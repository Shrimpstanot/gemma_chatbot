import os
import pandas as pd
import numpy as np


DATA_DIR = os.path.join("project", "data")

stops = pd.read_csv(os.path.join(DATA_DIR, "stops.csv"))
routes = pd.read_csv(os.path.join(DATA_DIR, "routes.csv"))
trips = pd.read_csv(os.path.join(DATA_DIR, "trips.csv"))
stop_times = pd.read_csv(os.path.join(DATA_DIR, "stop_times.csv"))

#merging stop times and trips based on trip-id
trip_stops = pd.merge(stop_times, trips, on="trip_id")
#converting stop id to a str
trip_stops["stop_id"] = trip_stops["stop_id"].astype(str)
stops["stop_id"] = stops["stop_id"].astype(str)

#merging trip_stops and stops on stop_id
trip_stops_full = pd.merge(trip_stops, stops, on="stop_id")
trip_stops_full["route_id"] = trip_stops_full["route_id"].astype(str)
routes["route_id"] = routes["route_id"].astype(str)
trip_stops_full = pd.merge(trip_stops_full, routes[['route_id', 'route_short_name']], on="route_id", how="left")

def interpolate_group(df):
    # creating a copy of df and sorting according to "stop_sequence"
    df = df.sort_values('stop_sequence').copy()
    # taking the stop latitude and longitude
    coords = df[['stop_lat','stop_lon']].values
    # Euclidean distances between consecutive stops
    dist = np.sqrt((coords[1:,0] - coords[:-1,0])**2 + (coords[1:,1] - coords[:-1,1])**2)
    dist = np.insert(dist, 0, 0)  # first stop has zero distance
    # getting the cumulative sum and assinging it to cumdist
    cumdist = np.cumsum(dist)
    first_sec = df['arrival_seconds'].iloc[0]
    last_sec = df['arrival_seconds'].iloc[-1]
    total_time = last_sec - first_sec
    total_dist = cumdist[-1]
    # avoid division by zero
    if total_dist > 0:
        interp_sec = first_sec + (cumdist / total_dist) * total_time
    else:
        interp_sec = np.full_like(cumdist, first_sec)
    df['interpolated_seconds'] = interp_sec
    return df

# runs interpolation logic to all trip-ids and saves it to interpolated
interpolated = trip_stops_full.groupby('trip_id').apply(interpolate_group).reset_index(drop=True)
# converts interpolated time to HH:MM:SS format
interpolated['interpolated_arrival_time'] = pd.to_timedelta(interpolated['interpolated_seconds'], unit='s').astype(str)

# saving interpolated trips
interpolated.to_csv(os.path.join(DATA_DIR, "interpolated_trips.csv"), index=False, encoding="utf-8")
interpolated.to_parquet(os.path.join(DATA_DIR, "interpolated_trips.parquet"), index=False)
print(interpolated[['route_id','route_short_name','trip_id','stop_sequence','stop_name','interpolated_arrival_time']].head(20))