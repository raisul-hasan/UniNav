from django.test import TestCase, Client

class StaticFilesTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_static_files_load(self):
        response = self.client.get('/login/')
        self.assertContains(response, 'css/bootstrap.css')
        self.assertContains(response, 'js/script.js')