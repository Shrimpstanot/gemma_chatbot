from fastapi import FastAPI
from pydantic import BaseModel
import torch
import torch.nn as nn
import joblib
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException

app = FastAPI()

#paths
static_path = os.path.join(os.path.dirname(__file__), "../static")
model_path = os.path.join(os.path.dirname(__file__), "../model/travel_time_model.pt")
scaler_path = os.path.join(os.path.dirname(__file__), "../model/scaler.pkl")

app.mount(static_path, StaticFiles(directory=static_path), name="static")

#serve frontend
@app.get("/")
def serve_home():
    return FileResponse(os.path.join(static_path, "index.html"))


#load model and scaler
model = nn.Sequential(
    nn.Linear(6, 64),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(64, 32),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(32, 1)
)
model.load_state_dict(torch.load(model_path, weights_only=True))
model.eval()

scaler = joblib.load(filename=scaler_path)

class InputData(BaseModel):
    distance: float
    speed: float
    traffic_level: float
    weather: int
    road_type: int
    day_of_week: int


@app.post("/predict")
def predict(data: InputData):
    if not (0 <= data.traffic_level <= 1):
        raise HTTPException(status_code=400, detail="Traffic level must be between 0 and 1.")
    if data.speed <= 0:
        raise HTTPException(status_code=400, detail="Speed must be positive.")
    
    input_values = [
        data.speed,
        data.traffic_level,
        data.weather,
        data.road_type,
        data.distance,
        data.day_of_week
    ]

    # Scale input
    scaled = scaler.transform([input_values])
    input_tensor = torch.tensor(scaled, dtype=torch.float32)

    with torch.no_grad():
        prediction = model(input_tensor).item()
        
    print(f"Input: {input_values} → Prediction: {prediction:.2f}")
    return {"predicted_time": round(prediction, 2)}
