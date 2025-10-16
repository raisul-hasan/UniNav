// Initialize map with simple coordinate system for image-based maps
let map = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -1,
    maxZoom: 2
}).setView([0, 0], 0);

// Image bounds (adjust to your PNG dimensions, e.g., 1000x1000px)
const imageBounds = [[-50, -50], [2500, 2500]]; // [southWest, northEast]
let currentOverlay = null;
let currentMarkers = L.layerGroup(); // Permanent pins
let tempMarkers = L.layerGroup(); // Temporary/user pins

// Load floor and pins
function loadFloor(floorNum) {
    // Clear previous layers
    if (currentOverlay) map.removeLayer(currentOverlay);
    currentMarkers.clearLayers();
    tempMarkers.clearLayers();
    map.removeLayer(currentMarkers);
    map.removeLayer(tempMarkers);

    // Add floor image
    const imageUrl = window.floorPlans[floorNum];
    if (imageUrl) {
        currentOverlay = L.imageOverlay(imageUrl, imageBounds).addTo(map);
        map.fitBounds(imageBounds);
    }

    // Add permanent pins
    const floorMarkers = window.markersData[floorNum] || [];
    floorMarkers.forEach(markerData => {
        const marker = L.marker([markerData.lat, markerData.lng], {
            icon: L.divIcon({
                className: 'custom-pin',
                html: '<i class="fas fa-map-pin" style="color: #7a6ad8; font-size: 24px;"></i>',
                iconSize: [24, 24],
                iconAnchor: [12, 24]
            })
        })
        .bindPopup(`
            <b>${markerData.title}</b><br>
            ${markerData.desc}<br>
            <a href="#" onclick="shareLocation(${markerData.lat}, ${markerData.lng}, '${markerData.title}')">Share in Chat</a>
        `)
        .addTo(currentMarkers);
    });
    currentMarkers.addTo(map);
}

// Share location in chat (integrates with WebSocket)
function shareLocation(lat, lng, title) {
    // Requires active chat session (set in chat.html)
    if (!window.chatType || !window.chatId) {
        alert('Please select a chat to share the location.');
        return;
    }
    const socket = new WebSocket(`ws://${window.location.host}/ws/chat/${window.chatType}/${window.chatId}/`);
    socket.onopen = function() {
        socket.send(JSON.stringify({
            'action': 'message',
            'content': `Shared location: ${title || 'Custom Pin'}`,
            'sender_id': window.userId,
            'sender_type': window.userType,
            'latitude': lat,
            'longitude': lng
        }));
        socket.close();
    };
}

// Click to add temporary pin
map.on('click', function(e) {
    tempMarkers.clearLayers();
    const marker = L.marker([e.latlng.lat, e.latlng.lng], {
        icon: L.divIcon({
            className: 'temp-pin',
            html: '<i class="fas fa-map-marker-alt" style="color: #ff4444; font-size: 24px;"></i>',
            iconSize: [24, 24],
            iconAnchor: [12, 24]
        })
    })
    .bindPopup(`
        Custom Pin<br>
        Coordinates: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}<br>
        <a href="#" onclick="shareLocation(${e.latlng.lat}, ${e.latlng.lng}, 'Custom Pin')">Share in Chat</a>
    `)
    .addTo(tempMarkers)
    .openPopup();
    tempMarkers.addTo(map);
});

// Floor buttons
document.querySelectorAll('.floor-btn').forEach(btn => {
    btn.onclick = function() {
        document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadFloor(parseInt(btn.dataset.floor));
    };
});

// Zoom controls
document.getElementById('zoom-in').onclick = () => map.zoomIn();
document.getElementById('zoom-out').onclick = () => map.zoomOut();
document.getElementById('reset').onclick = () => map.fitBounds(imageBounds);

// My Location (browser geolocation)
document.getElementById('my-location').onclick = function() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            // Map real-world coords to image coords (placeholder; calibrate to your campus)
            const realLat = position.coords.latitude;
            const realLng = position.coords.longitude;
            // Example: Scale real-world coords (e.g., campus at 40.007,-105.267) to [-50,50]
            const mappedLat = (realLat - 40.0) * 100; // Adjust offset/scale
            const mappedLng = (realLng + 105.3) * 100;
            
            tempMarkers.clearLayers();
            const marker = L.marker([mappedLat, mappedLng], {
                icon: L.divIcon({
                    className: 'my-location-pin',
                    html: '<i class="fas fa-user-circle" style="color: #00cc00; font-size: 24px;"></i>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 24]
                })
            })
            .bindPopup(`
                You are here!<br>
                Coordinates: ${mappedLat.toFixed(4)}, ${mappedLng.toFixed(4)}<br>
                <a href="#" onclick="shareLocation(${mappedLat}, ${mappedLng}, 'My Location')">Share in Chat</a>
            `)
            .addTo(tempMarkers)
            .openPopup();
            tempMarkers.addTo(map);
            map.panTo([mappedLat, mappedLng]);
        }, function(error) {
            alert('Geolocation failed: ' + error.message);
        });
    } else {
        alert('Geolocation is not supported by your browser.');
    }
};

// Load default floor
loadFloor(1);