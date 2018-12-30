import pandas as pd
import numpy as np
road_adjacency = pd.read_csv("road.csv", header=0, index_col=0, dtype=np.int8)
road_adjacency = road_adjacency.apply(lambda x: np.bool_(x))
print(road_adjacency.head())
tile_adjacency = pd.read_csv("tile.csv", header=0, index_col=0, dtype=np.int8)
print(tile_adjacency.head())
roads = np.zeros(72, dtype=np.int8)
settlements = np.zeros(54, dtype=np.int8)
cities = np.zeros(54, dtype=np.int8)

location=1
next_roads = road_adjacency.iloc[:, location]
print("thing1", next_roads)
print(road_adjacency.loc[next_roads, :])
blocking_locations = road_adjacency.iloc[[bool(x) for x in next_roads], :]

print(blocking_locations)
