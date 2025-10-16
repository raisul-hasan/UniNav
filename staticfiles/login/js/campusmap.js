// Initialize map with simple coordinate system for image-based maps
let map = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -1,
    maxZoom: 2
}).setView([0, 0], 0);

// Image bounds (adjust to your PNG dimensions, e.g., 1000x1000px)
const imageBounds = [[-50, -50], [50, 50]]; // [southWest, northEast]
let currentOverlay = null;
let currentMarkers = L.layerGroup(); // Permanent or lost/found pins
let tempMarkers = L.layerGroup(); // Temporary/user pins
let currentFloor = 1;
let currentMode = 'default'; // default or lost_and_found
let pickingLocation = false;

// Load floor and pins
function loadFloor(floorNum, searchQuery = '', itemId = null) {
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

    // Add pins based on mode
    let floorMarkers = [];
    if (currentMode === 'default') {
        floorMarkers = window.markersData[floorNum] || [];
    } else if (currentMode === 'lost_and_found') {
        // Fetch lost/found items via AJAX
        fetch(`/lost-and-found/?format=json&floor=${floorNum}`)
            .then(response => response.json())
            .then(data => {
                floorMarkers = data.map(item => ({
                    lat: item.location.latitude,
                    lng: item.location.longitude,
                    title: `${item.item_type.capitalize()} - ${item.description.substring(0, 50)}`,
                    desc: `Category: ${item.category_display}<br>Reported by: ${item.user_name || item.teacher_name}`
                }));
                renderMarkers(floorMarkers, searchQuery, itemId);
            });
        return; // Async fetch, render later
    }
    renderMarkers(floorMarkers, searchQuery, itemId);
}

function renderMarkers(floorMarkers, searchQuery, itemId) {
    let firstMatch = null;
    floorMarkers.forEach((markerData, index) => {
        const matchesSearch = !searchQuery || markerData.title.toLowerCase().includes(searchQuery.toLowerCase());
        const isHighlighted = matchesSearch || (itemId && index === 0); // Highlight specific item
        const marker = L.marker([markerData.lat, markerData.lng], {
            icon: L.divIcon({
                className: currentMode === 'lost_and_found' ? 'lost-found-pin' : (isHighlighted ? 'custom-pin highlight-pin' : 'custom-pin'),
                html: `<i class="fas fa-map-pin" style="color: ${currentMode === 'lost_and_found' ? '#ff4444' : (isHighlighted ? '#ffcc00' : '#7a6ad8')}; font-size: ${isHighlighted ? '28px' : '26px'};"></i>`,
                iconSize: [isHighlighted ? 28 : 26, isHighlighted ? 28 : 26],
                iconAnchor: [isHighlighted ? 14 : 13, isHighlighted ? 28 : 26]
            })
        })
        .bindPopup(`
            <b>${markerData.title}</b><br>
            ${markerData.desc}<br>
            <a href="#" onclick="shareLocation(${markerData.lat}, ${markerData.lng}, '${markerData.title}')">Share in Chat</a>
        `)
        .addTo(currentMarkers);
        if (isHighlighted && !firstMatch) {
            firstMatch = marker;
        }
    });
    currentMarkers.addTo(map);
    currentFloor = parseInt(currentFloor);

    if (firstMatch && (searchQuery || itemId)) {
        map.panTo(firstMatch.getLatLng());
        firstMatch.openPopup();
    }
}

// Share location in chat
function shareLocation(lat, lng, title) {
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

// Click to add temporary pin or pick location for lost/found
map.on('click', function(e) {
    if (pickingLocation) {
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
            Selected Location<br>
            Coordinates: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}
        `)
        .addTo(tempMarkers)
        .openPopup();
        tempMarkers.addTo(map);
        document.getElementById('latitude').value = e.latlng.lat.toFixed(4);
        document.getElementById('longitude').value = e.latlng.lng.toFixed(4);
        document.getElementById('pin-coordinates').textContent = `Lat: ${e.latlng.lat.toFixed(4)}, Lng: ${e.latlng.lng.toFixed(4)}`;
        document.getElementById('floor').value = currentFloor;
    } else {
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
    }
});

// Floor buttons
document.querySelectorAll('.floor-btn').forEach(btn => {
    btn.onclick = function() {
        document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const searchQuery = document.getElementById('location-search').value;
        const urlParams = new URLSearchParams(window.location.search);
        const itemId = urlParams.get('item_id');
        loadFloor(parseInt(btn.dataset.floor), searchQuery, itemId);
    };
});

// Mode buttons
document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.onclick = function() {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
        const searchQuery = document.getElementById('location-search').value;
        const urlParams = new URLSearchParams(window.location.search);
        const itemId = urlParams.get('item_id');
        loadFloor(currentFloor, searchQuery, itemId);
    };
});

// Zoom controls
document.getElementById('zoom-in').onclick = () => map.zoomIn();
document.getElementById('zoom-out').onclick = () => map.zoomOut();
document.getElementById('reset').onclick = () => map.fitBounds(imageBounds);

// My Location
document.getElementById('my-location').onclick = function() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const realLat = position.coords.latitude;
            const realLng = position.coords.longitude;
            const mappedLat = (realLat - 40.0) * 100;
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

// Pin picker for lost/found
document.getElementById('pick-location').addEventListener('click', function() {
    pickingLocation = true;
    tempMarkers.clearLayers();
    document.getElementById('latitude').value = '';
    document.getElementById('longitude').value = '';
    document.getElementById('pin-coordinates').textContent = 'Click map to select location';
});
document.getElementById('lostFoundModal').addEventListener('hidden.bs.modal', function() {
    pickingLocation = false;
    tempMarkers.clearLayers();
});

// Load initial state from URL
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode') || 'default';
    const itemId = urlParams.get('item_id');
    currentMode = mode;
    document.querySelectorAll('.mode-btn').forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    const floor = parseInt(urlParams.get('floor')) || 1;
    document.querySelectorAll('.floor-btn').forEach(btn => {
        if (parseInt(btn.dataset.floor) === floor) {
            btn.classList.add('active');
        }
    });
    loadFloor(floor, '', itemId);
});