import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

le = LabelEncoder()
df = pd.read_parquet("project/data/interpolated_trips.parquet")

#function from earlier
def add_cumulative_distance(group):
    coords = group[['stop_lat', 'stop_lon']].values
    dist = np.sqrt((coords[1:,0] - coords[:-1,0])**2 + (coords[1:,1] - coords[:-1,1])**2)
    dist = np.insert(dist, 0, 0)
    return np.cumsum(dist)


#created time from start column needed for model
df['arrival_seconds'] = pd.to_timedelta(df['interpolated_arrival_time']).dt.total_seconds()
df['start_time'] = df.groupby('trip_id')['arrival_seconds'].transform('min')
df['time_from_start'] = df['arrival_seconds'] - df['start_time']

df = df.dropna(subset=['arrival_seconds', 'time_from_start'])
#more preprocessing
df['hour_of_day'] = (df['arrival_seconds'] // 3600).astype(int)
df['cumulative_distance'] = (
    df.groupby('trip_id', group_keys=False)
      .apply(lambda group: pd.Series(add_cumulative_distance(group), index=group.index))
)
df["route_encoded"] = le.fit_transform(df["route_short_name"])

#variables
features = ['stop_sequence', 'route_encoded', 'hour_of_day', 'cumulative_distance']
target = 'time_from_start'

#unique train test split
unique_trips = df['trip_id'].unique()
train_ids, test_ids = train_test_split(unique_trips, test_size=0.2, random_state=42)

train_df = df[df['trip_id'].isin(train_ids)]
test_df = df[df['trip_id'].isin(test_ids)]
features = ['stop_sequence', 'route_encoded', 'hour_of_day', 'cumulative_distance']
target = 'time_from_start'

X_train = train_df[features]
y_train = train_df[target]

X_test = test_df[features]
y_test = test_df[target]

#random forest model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

#save model
joblib.dump(model, 'project/model/eta_model.pkl')

#metric eval
pred = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, pred))
print("R²:", r2_score(y_test, pred))
