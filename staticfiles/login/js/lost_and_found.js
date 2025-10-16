let map = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -1,
    maxZoom: 2
}).setView([0, 0], 0);

const imageBounds = [[-50, -50], [50, 50]];
let currentOverlay = null;
let currentMarkers = L.layerGroup();
let tempMarkers = L.layerGroup();
let currentFloor = 1;
let pickingLocation = false;

function loadFloor(floorNum, itemId = null) {
    if (currentOverlay) map.removeLayer(currentOverlay);
    currentMarkers.clearLayers();
    tempMarkers.clearLayers();
    map.removeLayer(currentMarkers);
    map.removeLayer(tempMarkers);

    const imageUrl = window.floorPlans[floorNum];
    if (imageUrl) {
        currentOverlay = L.imageOverlay(imageUrl, imageBounds).addTo(map);
        map.fitBounds(imageBounds);
    }

    fetch(`/lost-and-found/?format=json&floor=${floorNum}`)
        .then(response => response.json())
        .then(data => {
            let firstMatch = null;
            data.forEach((item, index) => {
                const isHighlighted = itemId && item.id === parseInt(itemId);
                const marker = L.marker([item.location.latitude, item.location.longitude], {
                    icon: L.divIcon({
                        className: 'lost-found-pin',
                        html: `<i class="fas fa-map-pin" style="color: ${isHighlighted ? '#ffcc00' : '#ff4444'}; font-size: ${isHighlighted ? '28px' : '26px'};"></i>`,
                        iconSize: [isHighlighted ? 28 : 26, isHighlighted ? 28 : 26],
                        iconAnchor: [isHighlighted ? 14 : 13, isHighlighted ? 28 : 26]
                    })
                })
                .bindPopup(`
                    <b>${item.item_type.charAt(0).toUpperCase() + item.item_type.slice(1)} - ${item.description.substring(0, 50)}</b><br>
                    Category: ${item.category_display}<br>
                    Reported by: ${item.user_name || item.teacher_name}<br>
                    <a href="#" onclick="shareLocation(${item.location.latitude}, ${item.location.longitude}, '${item.item_type.charAt(0).toUpperCase() + item.item_type.slice(1)} - ${item.description.substring(0, 50)}')">Share in Chat</a>
                `)
                .addTo(currentMarkers);
                if (isHighlighted && !firstMatch) {
                    firstMatch = marker;
                }
            });
            currentMarkers.addTo(map);
            currentFloor = parseInt(floorNum);

            if (firstMatch) {
                map.panTo(firstMatch.getLatLng());
                firstMatch.openPopup();
            }
        });
}

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

function validateForm() {
    const latitude = document.getElementById('latitude').value;
    const longitude = document.getElementById('longitude').value;
    if (!latitude || !longitude) {
        alert('Please click the map to pin a location before submitting.');
        return false;
    }
    return true;
}

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
    }
});

document.querySelectorAll('.floor-btn').forEach(btn => {
    btn.onclick = function() {
        document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const urlParams = new URLSearchParams(window.location.search);
        const itemId = urlParams.get('item_id');
        loadFloor(parseInt(btn.dataset.floor), itemId);
    };
});

document.getElementById('zoom-in').onclick = () => map.zoomIn();
document.getElementById('zoom-out').onclick = () => map.zoomOut();
document.getElementById('reset').onclick = () => map.fitBounds(imageBounds);

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
    document.getElementById('latitude').value = '';
    document.getElementById('longitude').value = '';
    document.getElementById('pin-coordinates').textContent = 'No location selected';
});

document.querySelectorAll('.view-on-map').forEach(btn => {
    btn.onclick = function() {
        const floor = btn.dataset.floor;
        const itemId = btn.dataset.itemId;
        document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.floor-btn[data-floor="${floor}"]`).classList.add('active');
        loadFloor(parseInt(floor), itemId);
    };
});

document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const floor = parseInt(urlParams.get('floor')) || 1;
    const itemId = urlParams.get('item_id');
    document.querySelectorAll('.floor-btn').forEach(btn => {
        if (parseInt(btn.dataset.floor) === floor) {
            btn.classList.add('active');
        }
    });
    loadFloor(floor, itemId);
});