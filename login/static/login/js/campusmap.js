document.addEventListener("DOMContentLoaded", () => {
  const floors = window.floorMeta;
  let currentFloor = 1;
  let map, imgLayer, bounds;

  let myMarker = null;
  let destMarker = null;
  let routeLine = null;
  let clickCount = 0;

  // Initialize map
  map = L.map("map", { crs: L.CRS.Simple, zoomControl: true, minZoom: -1 });
  loadFloor(1);

  // Fit map to full view
  function fit(floor) {
    const { w, h } = floors[floor];
    bounds = [[0, 0], [h, w]];
    map.setMaxBounds(bounds);
    map.fitBounds(bounds, { padding: [0, 0], maxZoom: 0 });
  }

  function loadFloor(floor) {
    currentFloor = floor;
    const meta = floors[floor];
    if (imgLayer) map.removeLayer(imgLayer);
    imgLayer = L.imageOverlay(meta.src, [[0, 0], [meta.h, meta.w]]).addTo(map);
    fit(floor);

    document.querySelectorAll(".floor-btn").forEach((b) => {
      b.classList.toggle("btn-primary", parseInt(b.dataset.floor) === floor);
      b.classList.toggle("btn-outline-primary", parseInt(b.dataset.floor) !== floor);
    });

    [myMarker, destMarker, routeLine].forEach((m) => {
      if (m && m.floor !== currentFloor) map.removeLayer(m);
      else if (m && m.floor === currentFloor) m.addTo(map);
    });
  }

  document.querySelectorAll(".floor-btn").forEach((b) => {
    b.addEventListener("click", () => loadFloor(parseInt(b.dataset.floor)));
  });

  // Handle map click
  map.on("click", (e) => {
    e.originalEvent.preventDefault();
    e.originalEvent.stopPropagation();

    const p = e.latlng;
    clickCount++;

    if (clickCount === 1) {
      if (myMarker) map.removeLayer(myMarker);
      myMarker = L.marker(p, { title: "My Location", draggable: true, icon: blueIcon() }).addTo(map);
      myMarker.floor = currentFloor;
      myMarker.bindPopup("Your location").openPopup();
    } else if (clickCount === 2) {
      if (destMarker) map.removeLayer(destMarker);
      destMarker = L.marker(p, { title: "Destination", draggable: true, icon: redIcon() }).addTo(map);
      destMarker.floor = currentFloor;
      destMarker.bindPopup("Destination").openPopup();
    } else {
      clickCount = 0;
      alert("You can only set one start and one destination. Click Clear to reset.");
    }
  });

  function blueIcon() {
    return L.divIcon({
      className: "custom-blue",
      html: "📍",
      iconSize: [24, 24],
      iconAnchor: [12, 24],
    });
  }

  function redIcon() {
    return L.divIcon({
      className: "custom-red",
      html: "🎯",
      iconSize: [24, 24],
      iconAnchor: [12, 24],
    });
  }

  // Clear markers
  document.getElementById("btnClear").addEventListener("click", () => {
    [myMarker, destMarker, routeLine].forEach((m) => m && map.removeLayer(m));
    myMarker = destMarker = routeLine = null;
    clickCount = 0;
    document.getElementById("steps").innerHTML = "";
  });

  // Route button
  document.getElementById("btnRoute").addEventListener("click", () => {
    if (!myMarker) return alert("Click on the map to set your location.");
    if (!destMarker) return alert("Click again to set your destination.");

    const startP = myMarker.getLatLng();
    const goalP = destMarker.getLatLng();
    const start = { x: startP.lng, y: startP.lat, floor: myMarker.floor };
    const goal = { x: goalP.lng, y: goalP.lat, floor: destMarker.floor };

    fetch("/api/route/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start, goal }),
    })
      .then((r) => r.json())
      .then((res) => {
        if (!res.ok) return alert(res.error || "No route found.");
        drawRoute(res.path);
      })
      .catch(() => alert("Routing failed."));
  });

  function drawRoute(path) {
    const stepsEl = document.getElementById("steps");
    stepsEl.innerHTML = "";
    const segmentsByFloor = {};

    path.forEach((p, i) => {
      if (!segmentsByFloor[p.floor]) segmentsByFloor[p.floor] = [];
      segmentsByFloor[p.floor].push([p.y, p.x]);
      if (i < path.length - 1) {
        const n = path[i + 1];
        if (n.floor !== p.floor) {
          const li = document.createElement("li");
          li.innerHTML = `<strong>Go from Floor ${p.floor} to Floor ${n.floor}</strong>`;
          stepsEl.appendChild(li);
        }
      }
    });

    for (const [f, segs] of Object.entries(segmentsByFloor)) {
      if (parseInt(f) === currentFloor) {
        if (routeLine) map.removeLayer(routeLine);
        routeLine = L.polyline(segs, { color: "red", weight: 6 }).addTo(map);
        routeLine.floor = parseInt(f);
        loadFloor(parseInt(f));
      }
    }

    const li = document.createElement("li");
    li.textContent = `Total nodes: ${path.length}`;
    stepsEl.appendChild(li);
  }
});
