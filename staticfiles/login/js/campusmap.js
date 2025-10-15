document.addEventListener("DOMContentLoaded", () => {
    var map = L.map('map', {
        crs: L.CRS.Simple,
        minZoom: -1,
        maxZoom: 3,
        zoom: 0
    });

    var currentLayer = null;
    var bounds = [[0, 0], [1500, 3000]]; // Adjust based on your SVG viewBox

    // ✅ Get the floorPlans object from window (defined in HTML)
    const floorPlans = window.floorPlans;

    function loadFloor(floor) {
        if (currentLayer) {
            map.removeLayer(currentLayer);
        }
        currentLayer = L.imageOverlay(floorPlans[floor], bounds, {
            interactive: true
        }).addTo(map);
        map.fitBounds(bounds);
    }

    document.querySelectorAll('.floor-btn').forEach(button => {
        button.addEventListener('click', function() {
            var floor = this.getAttribute('data-floor');
            loadFloor(floor);
        });
    });

    document.getElementById('zoom-in').addEventListener('click', function() {
        map.zoomIn();
    });

    document.getElementById('zoom-out').addEventListener('click', function() {
        map.zoomOut();
    });

    document.getElementById('reset').addEventListener('click', function() {
        map.fitBounds(bounds);
    });

    // Load first floor by default
    loadFloor(1);
});
