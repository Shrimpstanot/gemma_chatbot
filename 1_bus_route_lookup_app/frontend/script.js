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
        resultDiv.innerText = "Possible routes: " + data.routes.join(", ");
      } else {
        resultDiv.innerText = "No routes found.";
      }
  
    } catch (error) {
      console.log("Error:", error);
      resultDiv.innerText = "Something went wrong.";
    }
  }