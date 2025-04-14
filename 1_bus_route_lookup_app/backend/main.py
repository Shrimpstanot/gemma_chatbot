from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from data import bus_routes
import os

app = FastAPI()

static_path = os.path.join(os.path.dirname(__file__), "../static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def serve_homepage():
    return FileResponse(os.path.join(static_path, "index.html"))

class RouteRequest(BaseModel):
    start: str
    destination: str
    
@app.post("/get-route")
async def get_route(req: RouteRequest):
    start = req.start.capitalize()
    destination = req.destination.capitalize()
    
    results = []
    for route in bus_routes:
        stops = route["stops"]
        if start in stops and destination in stops and stops.index(start) < stops.index(destination):
            results.append({
                "type": "direct",
                "route": route["route"],
                "from": start,
                "to": destination
            })
            
    # inter-line connection
    for route1 in bus_routes:
        if start not in route1["stops"]:
            continue
        
        for route2 in bus_routes:
            if route1["route"] == route2["route"] or destination not in route2["stops"]:
                continue
            
            transfer_stops = set(route1["stops"]) & set(route2["stops"])
            for transfer in transfer_stops:
                if (route1["stops"].index(start) < route1["stops"].index(transfer) and
                        route2["stops"].index(transfer) < route2["stops"].index(destination)):
                    results.append({
                        "type": "transfer",
                        "route1": route1["route"],
                        "from": start,
                        "to": transfer,
                        "route2": route2["route"],
                        "from2": transfer,
                        "to2": destination
                    })
    
    return JSONResponse(content={"routes": results})
        
            