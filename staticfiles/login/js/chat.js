document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('map-modal');
    const locationBtn = document.getElementById('location-btn');
    const closeBtn = document.getElementById('close-modal');
    const confirmBtn = document.getElementById('confirm-location');
    const latInput = document.getElementById('lat-input');
    const lngInput = document.getElementById('lng-input');
    const floorInput = document.getElementById('floor-input');

    let map, currentLayer, currentMarker;
    let selectedFloor = 1;
    let selectedLat, selectedLng;

    const mapWidth = 800;
    const mapHeight = 600;
    const floorImages = {
        1: '/static/images/floor1.png',
        2: '/static/images/floor2.png',
        3: '/static/images/floor3.png',
        4: '/static/images/floor4.png',
        5: '/static/images/floor5.png'
    };

    locationBtn.addEventListener('click', () => {
        modal.style.display = 'block';
        initMap();
        confirmBtn.style.display = 'inline-block';
    });

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        clearMap();
    });

    confirmBtn.addEventListener('click', () => {
        if (selectedLat && selectedLng) {
            latInput.value = selectedLat;
            lngInput.value = selectedLng;
            floorInput.value = selectedFloor;
            modal.style.display = 'none';
            clearMap();
            document.getElementById('chat-form').submit(); // Auto-submit form
        } else {
            alert('Please pin a location first.');
        }
    });

    function initMap() {
        const mapContainer = document.getElementById('map-container');
        map = L.map(mapContainer, {
            crs: L.CRS.Simple,
            minZoom: -1,
            maxZoom: 2,
            zoom: 0,
            zoomControl: false
        });

        const bounds = [[0, 0], [mapHeight, mapWidth]];
        loadFloor(1);

        map.on('click', (e) => {
            if (currentMarker) map.removeLayer(currentMarker);
            currentMarker = L.marker(e.latlng).addTo(map).bindPopup('Selected Location');
            selectedLat = e.latlng.lat;
            selectedLng = e.latlng.lng;
        });

        document.querySelectorAll('.floor-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                selectedFloor = parseInt(btn.getAttribute('data-floor'));
                loadFloor(selectedFloor);
                document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        document.getElementById('zoom-in').addEventListener('click', () => {
            map.zoomIn();
        });

        document.getElementById('zoom-out').addEventListener('click', () => {
            map.zoomOut();
        });

        document.getElementById('reset-zoom').addEventListener('click', () => {
            map.setView([mapHeight / 2, mapWidth / 2], 0);
        });

        document.getElementById('pin-location').addEventListener('click', () => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        const minLat = 23.0, maxLat = 23.1, minLng = 90.0, maxLng = 90.1;
                        const x = (lng - minLng) * (mapWidth / (maxLng - minLng));
                        const y = (maxLat - lat) * (mapHeight / (maxLat - minLat));

                        if (currentMarker) map.removeLayer(currentMarker);
                        currentMarker = L.marker([y, x]).addTo(map).bindPopup('Your Location').openPopup();
                        selectedLat = y;
                        selectedLng = x;
                    },
                    (error) => {
                        alert('Unable to retrieve location: ' + error.message);
                    }
                );
            } else {
                alert('Geolocation not supported.');
            }
        });
    }

    function loadFloor(floor) {
        if (currentLayer) map.removeLayer(currentLayer);
        currentLayer = L.imageOverlay(floorImages[floor], [[0, 0], [mapHeight, mapWidth]]).addTo(map);
        map.setView([mapHeight / 2, mapWidth / 2], 0);
        map.setMaxBounds([[0, 0], [mapHeight, mapWidth]]);
    }

    function clearMap() {
        if (map) {
            map.remove();
            map = null;
            currentMarker = null;
            currentLayer = null;
        }
    }

    document.querySelectorAll('.view-location').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            selectedFloor = parseInt(e.target.dataset.floor);
            selectedLat = parseFloat(e.target.dataset.lat);
            selectedLng = parseFloat(e.target.dataset.lng);
            modal.style.display = 'block';
            initMap();
            loadFloor(selectedFloor);
            currentMarker = L.marker([selectedLat, selectedLng]).addTo(map).bindPopup('Shared Location').openPopup();
            confirmBtn.style.display = 'none';
        });
    });
});