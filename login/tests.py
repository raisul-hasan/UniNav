from django.test import TestCase, Client
from .models import Location, Student, LostAndFound

class MapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = Student.objects.create(
            name="Test Student", email="test@university.edu",
            student_id="S123", phone_number="1234567890",
            password="hashed_password"
        )
        self.client.session['user_id'] = self.student.id
        self.client.session['user_type'] = 'student'
        self.client.session.save()
        self.location = Location.objects.create(
            name="Library", floor=1, latitude=-20, longitude=-30,
            description="Study area"
        )
        self.lost_item = LostAndFound.objects.create(
            user=self.student,
            item_type='lost',
            category='electronics',
            description="Lost phone near library",
            location=self.location,
            status='Open'
        )

    def test_map_loads(self):
        response = self.client.get('/campus-map/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="map"')
        self.assertContains(response, 'Library')

    def test_location_model(self):
        loc = Location.objects.get(name="Library")
        self.assertEqual(loc.floor, 1)
        self.assertEqual(loc.latitude, -20)
        self.assertEqual(loc.description, "Study area")

    def test_lost_and_found_list(self):
        response = self.client.get('/lost-and-found/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lost phone near library')
        self.assertContains(response, 'Lost')

    def test_lost_and_found_map(self):
        response = self.client.get('/lost-and-found-map/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="map"')
        self.assertContains(response, 'Lost phone near library')
        self.assertContains(response, 'lost_and_found_map.js')

    def test_add_lost_and_found(self):
        response = self.client.post('/add-lost-and-found/', {
            'item_type': 'found',
            'category': 'books',
            'description': 'Found textbook in cafeteria',
            'floor': 1,
            'latitude': -15,
            'longitude': -10
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LostAndFound.objects.filter(description='Found textbook in cafeteria').exists())

    def test_add_lost_and_found_empty_coordinates(self):
        response = self.client.post('/add-lost-and-found/', {
            'item_type': 'found',
            'category': 'books',
            'description': 'Found textbook in cafeteria',
            'floor': 1,
            'latitude': '',
            'longitude': ''
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LostAndFound.objects.filter(description='Found textbook in cafeteria').exists())
        response = self.client.get('/lost-and-found-map/')
        self.assertContains(response, 'All fields are required')

def test_lost_and_found_map_click_coordinates(self):
    response = self.client.post('/add-lost-and-found/', {
        'item_type': 'found',
        'category': 'books',
        'description': 'Found book in library',
        'floor': 1,
        'latitude': -15.1234,
        'longitude': 10.5678
    })
    self.assertEqual(response.status_code, 302)
    item = LostAndFound.objects.get(description='Found book in library')
    self.assertEqual(item.location.latitude, -15.1234)
    self.assertEqual(item.location.longitude, 10.5678)
    self.assertEqual(item.location.floor, 1)