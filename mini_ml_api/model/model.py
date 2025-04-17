from data import base_data
import torch
import torch.nn as nn
import torch.optim as optim
import random
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

for entry in base_data:
    if entry["traffic_level"] > 0.7:
        speed = random.uniform(20, 40)  # urban, traffic-congested
    elif entry["traffic_level"] < 0.3:
        speed = random.uniform(60, 90)  # highway or free-flow
    else:
        speed = random.uniform(40, 70)  # normal flow
    entry["speed"] = speed
    eff_speed = entry["speed"] * (1- entry["traffic_level"])
    entry["time"] = entry["distance"] / (eff_speed + 1e-3)

# Manual encoding of categorical features
weather_map = {"clear": 0, "rainy": 1, "foggy": 2, "snowy": 3}
road_type_map = {"highway": 0, "urban": 1, "residential": 2, "rural": 3}
day_map = {"weekday": 0, "weekend": 1}

for entry in base_data:
    entry["weather"] = weather_map[entry["weather"]]
    entry["road_type"] = road_type_map[entry["road_type"]]
    entry["day_of_week"] = day_map[entry["day_of_week"]]

X = torch.tensor([
    [d["speed"], d["traffic_level"], d["weather"], d["road_type"], d["distance"], d["day_of_week"]] for d in base_data
], dtype=torch.float32)

y = torch.tensor([
    [d["time"]] for d in base_data
], dtype=torch.float32)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X.numpy())

X = torch.tensor(X_scaled, dtype=torch.float32)

model = nn.Sequential(
    nn.Linear(6, 16),
    nn.ReLU(),
    nn.Linear(16, 1)
)

criterion = nn.MSELoss()
optimizer = optim.AdamW(model.parameters())

for epoch in range(500):
    model.train()
    optimizer.zero_grad()
    pred = model(X_train)
    loss = criterion(pred, y_train)
    loss.backward()
    optimizer.step()
    
print(f"Final training loss: {loss.item():.4f}")

model.eval()
with torch.no_grad():
    test_pred = model(X_test)
    test_loss = criterion(test_pred, y_test)
    print(f"Test loss: {test_loss.item():.4f}")