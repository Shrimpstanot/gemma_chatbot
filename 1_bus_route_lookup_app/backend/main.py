from flask import Flask, jsonify, request, send_from_directory
from data import bus_routes
import os

# Use full path to frontend folder
frontend_folder = os.path.join(os.path.dirname(__file__), "../frontend")
app = Flask(__name__, static_folder=frontend_folder)

@app.route("/")
def serve_homepage():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/script.js")
def serve_script():
    return send_from_directory(frontend_folder, "script.js")

@app.route("/get-route", methods=["POST"])
def get_route():
    data = request.json
    start = data.get("start")
    destination = data.get("destination")

    possible_routes = []
    for route in bus_routes:
        stops = route["stops"]
        if start in stops and destination in stops and stops.index(start) < stops.index(destination):
            possible_routes.append(route["route"])

    return jsonify({"routes": possible_routes})

if __name__ == "__main__":
    app.run(debug=True)