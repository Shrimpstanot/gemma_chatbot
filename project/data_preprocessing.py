import os
import pandas as pd
import numpy as np

# Base path to your data folder
DATA_DIR = os.path.join("project", "data")

# Now reuse this for all files
stops = pd.read_csv(os.path.join(DATA_DIR, "stops.csv"))
routes = pd.read_csv(os.path.join(DATA_DIR, "routes.csv"))
trips = pd.read_csv(os.path.join(DATA_DIR, "trips.csv"))
stop_times = pd.read_csv(os.path.join(DATA_DIR, "stop_times.csv"))

trip_stops = pd.merge(stop_times, trips, on="trip_id")
trip_stops["stop_id"] = trip_stops["stop_id"].astype(str)
stops["stop_id"] = stops["stop_id"].astype(str)

trip_stops_full = pd.merge(trip_stops, stops, on="stop_id")

# Optional: sort to see clean stop order
trip_stops_full = trip_stops_full.sort_values(["route_id", "trip_id", "stop_sequence"])
trip_stops_full['arrival_seconds'] = pd.to_timedelta(trip_stops_full['arrival_time']).dt.total_seconds()

def interpolate_group(df):
    df = df.sort_values('stop_sequence').copy()
    coords = df[['stop_lat','stop_lon']].values
    # Euclidean distances between consecutive stops
    dist = np.sqrt((coords[1:,0] - coords[:-1,0])**2 + (coords[1:,1] - coords[:-1,1])**2)
    dist = np.insert(dist, 0, 0)  # first stop has zero distance
    cumdist = np.cumsum(dist)
    first_sec = df['arrival_seconds'].iloc[0]
    last_sec = df['arrival_seconds'].iloc[-1]
    total_time = last_sec - first_sec
    total_dist = cumdist[-1]  # Changed from cumdist.iloc[-1] to cumdist[-1]
    # avoid division by zero
    if total_dist > 0:
        interp_sec = first_sec + (cumdist / total_dist) * total_time
    else:
        interp_sec = np.full_like(cumdist, first_sec)
    df['interpolated_seconds'] = interp_sec
    return df

interpolated = trip_stops_full.groupby('trip_id').apply(interpolate_group).reset_index(drop=True)
interpolated['interpolated_arrival_time'] = pd.to_timedelta(interpolated['interpolated_seconds'], unit='s').astype(str)
print(interpolated[['route_id','trip_id','stop_sequence','stop_name','interpolated_arrival_time']].head(20))