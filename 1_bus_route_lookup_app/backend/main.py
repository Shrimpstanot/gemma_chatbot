from flask import Flask, jsonify, request
from data import bus_routes

app = Flask(__name__)

@app.route("/get-route", methods = ["POST"])
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