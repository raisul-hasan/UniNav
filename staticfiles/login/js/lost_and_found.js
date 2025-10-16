// static/login/js/lost_and_found.js
// Initialize Leaflet map with simple coordinate system for image-based floor plans
let map = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -1,
    maxZoom: 2
}).setView([0, 0], 0);

// Image bounds (matches campusmap.js; assumes 1000x1000px images)
const imageBounds = [[-50, -50], [2500, 2500]]; // [southWest, northEast]
let currentOverlay = null;
let currentMarkers = L.layerGroup(); // For lost/found item pins
let tempMarkers = L.layerGroup(); // For temporary user pins
let currentFloor = 1;
let pickingLocation = false;

// Load floor plan and markers
function loadFloor(floorNum, itemId = null) {
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
    } else {
        console.error('Floor plan image not found for floor:', floorNum);
        alert('Failed to load floor plan. Please try another floor.');
        return;
    }

    // Fetch lost/found items for this floor
    const urlParams = new URLSearchParams(window.location.search);
    const itemType = urlParams.get('item_type') || '';
    const category = urlParams.get('category') || '';
    fetch(`/lost-and-found/?format=json&floor=${floorNum}&item_type=${itemType}&category=${category}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch items');
            return response.json();
        })
        .then(data => {
            const floorMarkers = data.map(item => ({
                lat: item.location.latitude,
                lng: item.location.longitude,
                title: `${item.item_type.charAt(0).toUpperCase() + item.item_type.slice(1)} - ${item.description.substring(0, 50)}`,
                desc: `Category: ${item.category_display}<br>Reported by: ${item.user_name || item.teacher_name}<br>Status: ${item.status}`
            }));
            floorMarkers.forEach((markerData, index) => {
                const isHighlighted = itemId && item.id === parseInt(itemId);
                const marker = L.marker([markerData.lat, markerData.lng], {
                    icon: L.divIcon({
                        className: isHighlighted ? 'lost-found-pin highlighted' : 'lost-found-pin',
                        html: `<i class="fas fa-map-pin" style="color: ${isHighlighted ? '#ff0000' : '#ff4444'}; font-size: 26px;"></i>`,
                        iconSize: [26, 26],
                        iconAnchor: [13, 26]
                    })
                }).bindPopup(`${markerData.title}<br>${markerData.desc}`);
                if (isHighlighted) {
                    marker.openPopup();
                    map.panTo([markerData.lat, markerData.lng]);
                }
                marker.addTo(currentMarkers);
            });
            currentMarkers.addTo(map);
        })
        .catch(error => {
            console.error('Error fetching items:', error);
            alert('Failed to load lost and found items.');
        });
}

// Handle map clicks for pinning location
map.on('click', function(e) {
    if (pickingLocation) {
        tempMarkers.clearLayers();
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        // Validate coordinates within bounds
        if (lat < -50 || lat > 50 || lng < -50 || lng > 50) {
            alert('Selected location is outside map bounds. Please try again.');
            return;
        }
        const marker = L.marker([lat, lng], {
            icon: L.divIcon({
                className: 'temp-pin',
                html: '<i class="fas fa-check-circle" style="color: #00ff00; font-size: 24px;"></i>',
                iconSize: [24, 24],
                iconAnchor: [12, 24]
            })
        }).addTo(tempMarkers);
        tempMarkers.addTo(map);
        document.getElementById('latitude').value = lat.toFixed(4);
        document.getElementById('longitude').value = lng.toFixed(4);
        document.getElementById('pin-coordinates').textContent = `Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}`;
        document.getElementById('submit-btn').disabled = false;
    }
});

// Handle manual coordinate input
function updateCoordinates() {
    const lat = parseFloat(document.getElementById('latitude-manual').value);
    const lng = parseFloat(document.getElementById('longitude-manual').value);
    if (isNaN(lat) || isNaN(lng)) {
        document.getElementById('submit-btn').disabled = true;
        document.getElementById('pin-coordinates').textContent = 'Invalid coordinates';
        return;
    }
    if (lat < -50 || lat > 50 || lng < -50 || lng > 50) {
        alert('Coordinates must be between -50 and 50.');
        document.getElementById('submit-btn').disabled = true;
        return;
    }
    tempMarkers.clearLayers();
    const marker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'temp-pin',
            html: '<i class="fas fa-check-circle" style="color: #00ff00; font-size: 24px;"></i>',
            iconSize: [24, 24],
            iconAnchor: [12, 24]
        })
    }).addTo(tempMarkers);
    tempMarkers.addTo(map);
    document.getElementById('latitude').value = lat.toFixed(4);
    document.getElementById('longitude').value = lng.toFixed(4);
    document.getElementById('pin-coordinates').textContent = `Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}`;
    document.getElementById('submit-btn').disabled = false;
    map.panTo([lat, lng]);
}

// Geolocation: Map real-world coords to image coords
document.getElementById('my-location').addEventListener('click', function() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const realLat = position.coords.latitude;
            const realLng = position.coords.longitude;
            // Adjust these offsets based on your campus's real-world coordinates
            const mappedLat = (realLat - 40.0) * 100; // Example offset for Boulder, CO
            const mappedLng = (realLng + 105.3) * 100;
            if (mappedLat < -50 || mappedLat > 50 || mappedLng < -50 || mappedLng > 50) {
                alert('Your location is outside the map bounds. Please pin manually.');
                return;
            }
            tempMarkers.clearLayers();
            const marker = L.marker([mappedLat, mappedLng], {
                icon: L.divIcon({
                    className: 'my-location-pin',
                    html: '<i class="fas fa-user-circle" style="color: #00cc00; font-size: 24px;"></i>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 24]
                })
            })
            .bindPopup(`You are here!<br>Coordinates: ${mappedLat.toFixed(4)}, ${mappedLng.toFixed(4)}`)
            .addTo(tempMarkers)
            .openPopup();
            tempMarkers.addTo(map);
            if (pickingLocation) {
                document.getElementById('latitude').value = mappedLat.toFixed(4);
                document.getElementById('longitude').value = mappedLng.toFixed(4);
                document.getElementById('pin-coordinates').textContent = `Lat: ${mappedLat.toFixed(4)}, Lng: ${mappedLng.toFixed(4)}`;
                document.getElementById('submit-btn').disabled = false;
            }
            map.panTo([mappedLat, mappedLng]);
        }, function(error) {
            alert('Geolocation failed: ' + error.message + '. Please pin the location manually or enter coordinates.');
        });
    } else {
        alert('Geolocation is not supported by your browser. Please pin the location manually or enter coordinates.');
    }
});

// Floor button clicks
document.querySelectorAll('.floor-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFloor = parseInt(btn.dataset.floor);
        loadFloor(currentFloor);
    });
});

// Pin picking
document.getElementById('pick-location').addEventListener('click', function() {
    pickingLocation = true;
    tempMarkers.clearLayers();
    document.getElementById('latitude').value = '';
    document.getElementById('longitude').value = '';
    document.getElementById('latitude-manual').value = '';
    document.getElementById('longitude-manual').value = '';
    document.getElementById('pin-coordinates').textContent = 'Click map or enter coordinates manually';
    document.getElementById('submit-btn').disabled = true;
});

// Modal close
document.getElementById('lostFoundModal').addEventListener('hidden.bs.modal', function() {
    pickingLocation = false;
    tempMarkers.clearLayers();
});

// Zoom and reset controls
document.getElementById('zoom-in').addEventListener('click', function() {
    map.zoomIn();
});

document.getElementById('zoom-out').addEventListener('click', function() {
    map.zoomOut();
});

document.getElementById('reset').addEventListener('click', function() {
    map.fitBounds(imageBounds);
});

// Manual coordinate input
document.getElementById('latitude-manual').addEventListener('input', updateCoordinates);
document.getElementById('longitude-manual').addEventListener('input', updateCoordinates);

// Initial load
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