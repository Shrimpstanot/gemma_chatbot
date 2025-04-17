from data import generate_synthetic_data
import torch
import torch.nn as nn
import torch.optim as optim
import random
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

data = generate_synthetic_data(1000) # generate n data

# create a tensor so we can run the nn
X = torch.tensor([
    [d["speed"], d["traffic_level"], d["weather"], d["road_type"], d["distance"], d["day_of_week"]] for d in data
], dtype=torch.float32)

y = torch.tensor([
    [d["time"]] for d in data
], dtype=torch.float32)


#use a scaler so model predicts better
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X.numpy())
joblib.dump(scaler, "scaler.pkl") #save the scaler so we use again in main

#create 80/20 train test split
X = torch.tensor(X_scaled, dtype=torch.float32)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

#define model architecture
model = nn.Sequential(
    nn.Linear(6, 64),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(64, 32),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(32, 1)
)

#loss and optimizter
criterion = nn.MSELoss()
optimizer = optim.AdamW(model.parameters())

#train the model for n epochs
for epoch in range(500):
    model.train()
    optimizer.zero_grad()
    pred = model(X_train)
    loss = criterion(pred, y_train)
    loss.backward()
    optimizer.step()
    
print(f"Final training loss: {loss.item():.4f}")
torch.save(model.state_dict(), "travel_time_model.pt") #save model weights


#model evaluation metrics
model.eval()
with torch.no_grad():
    test_pred = model(X_test)
    test_loss = criterion(test_pred, y_test)
    print(f"Test loss: {test_loss.item():.4f}")

test_pred_np = test_pred.numpy()
y_test_np = y_test.numpy()

mae = mean_absolute_error(y_test_np, test_pred_np)
r2 = r2_score(y_test_np, test_pred_np)

print(f"MAE: {mae:.4f}, R²: {r2:.4f}")

# Adjusted R²
n = X_test.shape[0]
p = X_test.shape[1]
adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)
print(f"Adjusted R²: {adj_r2:.4f}")
