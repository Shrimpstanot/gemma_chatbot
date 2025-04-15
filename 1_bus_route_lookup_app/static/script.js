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

        data.routes.forEach(route => {
          const routeDiv = document.createElement("Div");
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
  
    } catch (error) {
      console.log("Error:", error);
      resultDiv.innerText = "Something went wrong.";
    }
  }