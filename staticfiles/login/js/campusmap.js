document.addEventListener('DOMContentLoaded', function() {
    // Check if required elements exist
    const startSelect = document.getElementById('start-location');
    const endSelect = document.getElementById('end-location');
    const findPathBtn = document.getElementById('find-path');
    if (!startSelect || !endSelect || !findPathBtn) {
        console.error('Required elements (start-location, end-location, find-path) not found');
        return;
    }

    // Check if floorPlans is defined
    if (!window.floorPlans) {
        console.error('window.floorPlans is undefined');
        return;
    }

    // Initialize map
    const map = L.map('map', {
        crs: L.CRS.Simple,
        minZoom: -1,
        maxZoom: 2
    });

    // Map bounds (assuming 1000x1000px floor plans)
    const bounds = [[0, 0], [1000, 1000]];
    let currentFloor = 1;
    let currentOverlay;
    let markersLayer = L.layerGroup().addTo(map);
    let pathLayer = L.layerGroup().addTo(map);

    // Load floor
    function loadFloor(floor) {
        if (!window.floorPlans[floor]) {
            console.error(`Floor plan for floor ${floor} not found`);
            return;
        }
        if (currentOverlay) {
            map.removeLayer(currentOverlay);
        }
        currentOverlay = L.imageOverlay(window.floorPlans[floor], bounds).addTo(map);
        map.fitBounds(bounds);
        
        // Update markers
        markersLayer.clearLayers();
        if (window.markersData[floor]) {
            window.markersData[floor].forEach(marker => {
                const m = L.marker([marker.latitude, marker.longitude], {
                    title: marker.name,
                    data: marker
                }).bindPopup(`
                    <b>${marker.name}</b><br>
                    ${marker.description}<br>
                    ${marker.is_transition ? `Type: ${marker.transition_type}` : ''}
                    <br>
                    <button class="set-start" data-id="${marker.id}">Set as Start</button>
                    <button class="set-end" data-id="${marker.id}">Set as End</button>
                `);
                markersLayer.addLayer(m);
            });
        }

        // Update active floor button
        document.querySelectorAll('.floor-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.floor == floor);
        });
    }

    // A* Algorithm
    function findPath(startId, endId) {
        if (!startId || !endId) {
            console.error('Start or end ID missing');
            return null;
        }
        const openSet = [];
        const closedSet = new Set();
        const cameFrom = {};
        const gScore = {};
        const fScore = {};

        const allLocations = Object.values(window.markersData).flat();
        const start = allLocations.find(loc => loc.id == startId);
        const end = allLocations.find(loc => loc.id == endId);
        if (!start || !end) {
            console.error('Start or end location not found');
            return null;
        }

        gScore[startId] = 0;
        fScore[startId] = heuristic(start, end);
        openSet.push([fScore[startId], startId]);

        while (openSet.length > 0) {
            openSet.sort((a, b) => a[0] - b[0]);
            const [currentFScore, currentId] = openSet.shift();
            if (currentId == endId) {
                return reconstructPath(cameFrom, currentId);
            }

            closedSet.add(currentId);
            const current = allLocations.find(loc => loc.id == currentId);
            const connections = Object.values(window.connections_by_floor).flat()
                .filter(conn => conn.from_id == currentId);

            for (const conn of connections) {
                const neighborId = conn.to_id;
                if (closedSet.has(neighborId)) continue;

                const neighbor = allLocations.find(loc => loc.id == neighborId);
                const tentativeGScore = gScore[currentId] + conn.weight * (conn.transition_type === 'stairs' ? 2 : conn.transition_type === 'elevator' ? 1.5 : 1);

                if (!openSet.some(([_, id]) => id == neighborId) || tentativeGScore < gScore[neighborId]) {
                    cameFrom[neighborId] = { id: currentId, transition: conn.transition_type };
                    gScore[neighborId] = tentativeGScore;
                    fScore[neighborId] = gScore[neighborId] + heuristic(neighbor, end);
                    if (!openSet.some(([_, id]) => id == neighborId)) {
                        openSet.push([fScore[neighborId], neighborId]);
                    }
                }
            }
        }
        return null;
    }

    function heuristic(a, b) {
        const dx = Math.abs(a.latitude - b.latitude);
        const dy = Math.abs(a.longitude - b.longitude);
        const dz = Math.abs(a.floor - b.floor) * 10;
        return dx + dy + dz;
    }

    function reconstructPath(cameFrom, currentId) {
        const path = [{ id: currentId }];
        while (cameFrom[currentId]) {
            currentId = cameFrom[currentId].id;
            path.unshift({ id: currentId, transition: cameFrom[currentId].transition });
        }
        return path;
    }

    function drawPath(path) {
        pathLayer.clearLayers();
        if (!path) {
            alert('No path found!');
            return;
        }

        const allLocations = Object.values(window.markersData).flat();
        const coords = path.map(p => {
            const loc = allLocations.find(l => l.id == p.id);
            return [loc.latitude, loc.longitude];
        });

        L.polyline(coords, { color: 'blue', weight: 5 }).addTo(pathLayer);
        path.forEach((p, i) => {
            if (p.transition) {
                const loc = allLocations.find(l => l.id == p.id);
                L.marker([loc.latitude, loc.longitude], {
                    icon: L.divIcon({
                        className: 'transition-icon',
                        html: `<span>${p.transition.charAt(0).toUpperCase()}</span>`
                    })
                }).addTo(pathLayer);
            }
        });
    }

    // Floor switching
    document.querySelectorAll('.floor-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const floor = parseInt(btn.dataset.floor);
            if (!window.floorPlans[floor]) {
                console.error(`No floor plan for floor ${floor}`);
                return;
            }
            currentFloor = floor;
            loadFloor(currentFloor);
        });
    });

    // Map controls
    document.getElementById('zoom-in').addEventListener('click', () => map.zoomIn());
    document.getElementById('zoom-out').addEventListener('click', () => map.zoomOut());
    document.getElementById('reset').addEventListener('click', () => map.fitBounds(bounds));
    document.getElementById('my-location').addEventListener('click', () => {
        navigator.geolocation.getCurrentPosition(pos => {
            const lat = (pos.coords.latitude % 1000);
            const lng = (pos.coords.longitude % 1000);
            map.setView([lat, lng], 1);
            L.marker([lat, lng]).addTo(map).bindPopup('You are here').openPopup();
        }, err => {
            console.error('Geolocation error:', err);
            alert('Unable to get your location');
        });
    });

    // Pathfinding UI
    let startId = null, endId = null;
    document.addEventListener('click', e => {
        if (e.target.classList.contains('set-start')) {
            startId = e.target.dataset.id;
            if (startSelect) startSelect.value = startId;
            updatePath();
        } else if (e.target.classList.contains('set-end')) {
            endId = e.target.dataset.id;
            if (endSelect) endSelect.value = endId;
            updatePath();
        }
    });

    findPathBtn.addEventListener('click', () => {
        startId = startSelect.value;
        endId = endSelect.value;
        updatePath();
    });

    function updatePath() {
        if (startId && endId) {
            const path = findPath(startId, endId);
            drawPath(path);
        }
    }

    // Initial load
    loadFloor(currentFloor);
});