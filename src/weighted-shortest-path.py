import os
import sys
import json
import glob
import folium
import pandas as pd
import geopandas as gpd
import networkx as nx
from datetime import datetime
import matplotlib.pyplot as plt
from osdatahub import FeaturesAPI, Extent
from folium.plugins import FloatImage

key = ""

extent = Extent.from_bbox((600000, 310200, 600900, 310900), "EPSG:27700")

product = "Highways_RoadLink"
features = FeaturesAPI(key, product, extent)
data = features.query(limit=2000)

gdf = gpd.GeoDataFrame.from_features(data, crs=data['crs'])

gdf.head(5)

gdf['Length'] = pd.to_numeric(gdf['Length'])
gdf['ElevationGainInDir'] = pd.to_numeric(gdf['ElevationGainInDir'])
gdf['ElevationGainInOppDir'] = pd.to_numeric(gdf['ElevationGainInOppDir'])

gdf['StartNodeGraded'] = gdf['StartNode'] + "_" + gdf['StartGradeSeparation'].apply(str)
gdf['EndNodeGraded'] = gdf['EndNode'] + "_" + gdf['EndGradeSeparation'].apply(str)

gdf.describe()

gdf.head(5)

ax = gdf.plot(color='#ff1f5b', figsize=(15, 15))
ax.axis('off')

roadWeight = {
    'Restricted Local Access Road': 0, 
    'Minor Road': 10, 
    'Local Road': 20,
    'A Road': 100, 
    'A Road Primary': 150,
    'B Road': 180, 
    'Restricted Secondary Access Road': 0,
    'Local Access Road': 0, 
    'Secondary Access Road': 0
}

def cyclingWeight(row):
    
    weight = 0
    weight += roadWeight[row['RouteHierarchy']]
    weight += row['Length'] / 1000
    weight += row['ElevationGainInDir'] / 10
    weight += row['ElevationGainInOppDir'] / 100
    
    return weight

gdf['weight'] = gdf.apply(cyclingWeight, axis=1)

gdf[['ID', 'StartNodeGraded', 'EndNodeGraded', 'Length', 'ElevationGainInDir', 'ElevationGainInOppDir', 'weight']].head()


G = nx.from_pandas_edgelist(gdf, 'StartNodeGraded', 'EndNodeGraded', ['weight', 'Length'])

# Display Graph info
print(nx.info(G))

# Work out shortest path from nodes chosen at random
startNode = list(G.nodes())[0] # the start node's TOID
endNode = list(G.nodes())[201] # the end node's TOID

# First, the shortest path based on the length of each connecting link
dijkstraLengthNodes = nx.dijkstra_path(G, startNode, endNode, 'Length')

# Then, the shortest path based on the weight dimension 
dijkstraWeightNodes = nx.dijkstra_path(G, startNode, endNode, 'weight')

# Create a mask to easily select shortest path route segments

gdf['dijkstraLengthMask'] = gdf['StartNodeGraded'].isin(dijkstraLengthNodes) & gdf['EndNodeGraded'].isin(dijkstraLengthNodes)
gdf['dijkstraWeightMask'] = gdf['StartNodeGraded'].isin(dijkstraWeightNodes) & gdf['EndNodeGraded'].isin(dijkstraWeightNodes)

# Set options and ZXY endpoints for OS Maps API: 
layer = 'Light_3857'
zxy_path = 'https://api.os.uk/maps/raster/v1/zxy/{}/{{z}}/{{x}}/{{y}}.png?key={}'.format(layer, key)

# Create a new Folium map
# Ordnance Survey basemap using the OS Data Hub OS Maps API centred on the boundary centroid location
# Zoom levels 7 - 16 correspond to the open data zoom scales only
m = folium.Map(location=[50.916438, -1.397284],
               min_zoom=7,
               max_zoom=16,
               tiles=zxy_path,
               attr='Contains OS data © Crown copyright and database right {}'.format(datetime.year))
