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
    
    possible_routes = []
    for route in bus_routes:
        stops = route["stops"]
        if start in stops and destination in stops and stops.index(start) < stops.index(destination):
            possible_routes.append(route["route"])
    
    return JSONResponse(content={"routes": possible_routes})
            