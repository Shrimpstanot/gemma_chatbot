async function lookupRoute() {
    const start = document.getElementById("start").value;
    const destination = document.getElementById("destination").value;
    const resultDiv = document.getElementById("result");
  
    try {
      const response = await fetch("/get-route", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          start: start,
          destination: destination
        })
      });
  
      const data = await response.json();
  
      if (data.routes.length > 0) {
        resultDiv.innerHTML = "";

        const header = document.createElement("div");
        header.innerText = "Routes sorted from fastest to slowest:";
        header.style.marginBottom = "10px";
        resultDiv.appendChild(header);

        data.routes.forEach(route => {
          const routeDiv = document.createElement("div");
          if (route.type === "direct") {
            routeDiv.className = "direct";
            routeDiv.innerText = `Direct route: ${route.route} from ${route.from} to ${route.to}.`;
          } else if (route.type === "transfer") {
            routeDiv.className = "transfer";
            routeDiv.innerText = `Transfer route: ${route.route1} from ${route.from} to ${route.to},
             then ${route.route2} from ${route.from2} to ${route.to2}`;
          }
          resultDiv.appendChild(routeDiv);
        });
      } else {
        resultDiv.innerText = "No routes found.";
      }
          // pick the first route to plot
    const firstRoute = data.routes[0];
    let stopList = [];

    if (firstRoute.type === "direct") {
      const routeObj = [firstRoute.from, firstRoute.to];
      const routeCoords = Object.keys(stopCoordinates);
      const allStops = routeCoords.slice(routeCoords.indexOf(firstRoute.from), routeCoords.indexOf(firstRoute.to) + 1);
      stopList = allStops;
    } else if (firstRoute.type === "transfer") {
      const routeObj = [firstRoute.from, firstRoute.to2];
      const routeCoords = Object.keys(stopCoordinates);
      const firstLeg = routeCoords.slice(routeCoords.indexOf(firstRoute.from), routeCoords.indexOf(firstRoute.to) + 1);
      const secondLeg = routeCoords.slice(routeCoords.indexOf(firstRoute.from2), routeCoords.indexOf(firstRoute.to2) + 1);
      stopList = firstLeg.concat(secondLeg.slice(1)); // avoid duplicate transfer stop
    }

    plotRouteOnMap(stopList);
  
    } catch (error) {
      console.log("Error:", error);
      resultDiv.innerText = "Something went wrong.";
    }
  }

  const stopCoordinates = {
    A: [41.0082, 28.9784],
    B: [41.0095, 28.9790],
    C: [41.0110, 28.9800],
    D: [41.0125, 28.9820],
    E: [41.0140, 28.9840],
    F: [41.0155, 28.9860],
    G: [41.0170, 28.9875],
    H: [41.0180, 28.9890],
    L: [41.0190, 28.9900],
    M: [41.0200, 28.9910],
    N: [41.0210, 28.9920],
    O: [41.0220, 28.9930],
    P: [41.0230, 28.9940],
    Q: [41.0240, 28.9950],
    R: [41.0250, 28.9960],
    S: [41.0260, 28.9970],
    X: [41.0270, 28.9980],
    Y: [41.0280, 28.9990],
    Z: [41.0290, 29.0000]
  };
  
  const map = L.map('map').setView([41.0082, 28.9784], 14);
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  
  function plotRouteOnMap(stops) {
    const latlngs = stops.map(stop => stopCoordinates[stop]).filter(Boolean);
    map.eachLayer(layer => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline) {
        map.removeLayer(layer);
      }
    });
    if (!latlngs.length) return;
  
    latlngs.forEach((coord, index) => {
      const stop = stops[index];
      L.marker(coord).addTo(map).bindPopup(`Stop: ${stop}`);
    });
  
    L.polyline(latlngs, { color: 'blue' }).addTo(map);
  }