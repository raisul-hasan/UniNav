from django.test import TestCase, Client
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Product, CartItem, EventPin
from daphne.testing import DaphneProcess 
import unittest
from decimal import Decimal
from typing import Optional

from django.test import TestCase, Client, override_settings
from django.urls import reverse, NoReverseMatch
from django.core.files.uploadedfile import SimpleUploadedFile

# Optional WS deps: skip WS tests if channels/daphne not installed
try:
    from channels.testing import WebsocketCommunicator
    from channels.routing import ProtocolTypeRouter, URLRouter
    HAVE_WS = True
except Exception:
    HAVE_WS = False

from .models import (
    Student, Teacher, Product, CartItem,
    Message, Reaction, Group,
)
from .routing import websocket_urlpatterns


def maybe_reverse(name: str, *args, **kwargs) -> Optional[str]:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except Exception:
        return None



class ModelBasicsTests(TestCase):
    def setUp(self):
        self.alice = Student.objects.create(
            name="Alice", email="alice@example.com",
            student_id="S001", phone_number="01700000000", password="pw"
        )
        self.bob = Student.objects.create(
            name="Bob", email="bob@example.com",
            student_id="S002", phone_number="01700000001", password="pw2"
        )
        self.t1 = Teacher.objects.create(
            name="Prof. X", email="x@example.com",
            teacher_id="T001", department="CSE",
            phone_number="01800000000", password="pw", is_approved=True
        )

    def test_message_str_and_reaction_toggle_via_view_logic(self):
        msg = Message.objects.create(sender=self.alice, recipient=self.bob, content="Hi")
        
        r1, created1 = Reaction.objects.get_or_create(message=msg, user=self.alice, emoji="👍")
        self.assertTrue(created1)
        
        r2, created2 = Reaction.objects.get_or_create(message=msg, user=self.alice, emoji="👍")
        self.assertFalse(created2)
        
        r2.delete()
        self.assertFalse(Reaction.objects.filter(message=msg, user=self.alice, emoji="👍").exists())



# Shop / Cart

class ShopCartViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.p1 = Product.objects.create(name="Breadboard", description="Mini", price=Decimal("120.50"))
        self.student = Student.objects.create(
            name="Carol", email="carol@example.com",
            student_id="S100", phone_number="01712345678", password="pw"
        )
        s = self.client.session
        s["user_id"] = self.student.id
        s["user_type"] = "student"
        s.save()

    def test_shop_page_loads(self):
        url = maybe_reverse("shop")
        if not url:
            self.skipTest("shop URL not found")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_cart_page_loads(self):
        url = maybe_reverse("cart")
        if not url:
            self.skipTest("cart URL not found")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_inc_dec(self):
        add_url = maybe_reverse("add_to_cart", kwargs={"product_id": self.p1.id})
        if not add_url:
            self.skipTest("add_to_cart URL not found")
        r = self.client.post(add_url)
        self.assertIn(r.status_code, (200, 302))
        item = CartItem.objects.get(product=self.p1)
        start = item.quantity

        inc = maybe_reverse("increment_cart_item", kwargs={"item_id": item.id})
        if inc:
            self.client.post(inc, follow=True)
            item.refresh_from_db()
            self.assertEqual(item.quantity, start + 1)

        dec = maybe_reverse("decrement_cart_item", kwargs={"item_id": item.id})
        if dec:
            self.client.post(dec, follow=True)
            item.refresh_from_db()
            self.assertEqual(item.quantity, start)


# send_message (HTTP helper)
class SendMessageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sender = Student.objects.create(
            name="Dave", email="dave@example.com",
            student_id="S777", phone_number="01777777777", password="pw"
        )
        self.recipient = Student.objects.create(
            name="Erin", email="erin@example.com",
            student_id="S778", phone_number="01777777778", password="pw"
        )
        s = self.client.session
        s["user_id"] = self.sender.id
        s["user_type"] = "student"
        s.save()

    def test_send_message_json(self):
        url = maybe_reverse("send_message")
        if not url:
            self.skipTest("send_message URL not found")
        r = self.client.post(
            url,
            {"content": "hello", "recipient_id": self.recipient.id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("file", data)
        self.assertIn("voice", data)

    def test_send_message_with_file(self):
        url = maybe_reverse("send_message")
        if not url:
            self.skipTest("send_message URL not found")
        fake = SimpleUploadedFile("readme.txt", b"Hello", content_type="text/plain")
        r = self.client.post(
            url,
            {"content": "with file", "recipient_id": self.recipient.id, "file": fake},
            format="multipart",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("file", r.json())



# WebSocket chat (optional)

@unittest.skipUnless(HAVE_WS, "channels/daphne not installed; skipping WebSocket tests")
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatWebSocketTests(TestCase):
    async_capable = True

    def setUp(self):
        self.stu = Student.objects.create(
            name="Eve", email="eve@example.com",
            student_id="S900", phone_number="01790000000", password="pw"
        )
        self.other = Student.objects.create(
            name="Frank", email="frank@example.com",
            student_id="S901", phone_number="01790000001", password="pw"
        )
        self.application = ProtocolTypeRouter({"websocket": URLRouter(websocket_urlpatterns)})

    async def test_dm_message_and_reaction_toggle(self):
        comm = WebsocketCommunicator(self.application, f"/ws/chat/dm/{self.other.id}/")
        ok, _ = await comm.connect()
        self.assertTrue(ok)

        await comm.send_json_to({
            "action": "message",
            "content": "Hello Frank",
            "sender_id": self.stu.id,
            "sender_type": "student",
            "file_url": None, "voice_url": None,
            "latitude": None, "longitude": None,
        })
        event = await comm.receive_json_from()
        self.assertEqual(event["action"], "message")
        msg_id = event["message_id"]

        await comm.send_json_to({
            "action": "reaction",
            "message_id": msg_id,
            "emoji": "👍",
            "sender_id": self.stu.id,
            "sender_type": "student",
        })
        evt = await comm.receive_json_from()
        self.assertEqual(evt["action"], "reaction")



# Campus Map

class CampusMapViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Student.objects.create(
            name="Mia", email="mia@example.com",
            student_id="S555", phone_number="01755555555", password="pw"
        )

    def test_redirects_or_login_page_without_session(self):
        url = maybe_reverse("campus_map")
        if not url:
            self.skipTest("campus_map URL not found")
        r = self.client.get(url)  
        
        self.assertIn(r.status_code, (200, 301, 302))
        if r.status_code == 200:
            html = r.content.decode("utf-8")
            self.assertTrue(("Login" in html) or ("Sign in" in html))

    def test_renders_map_when_logged_in(self):
        url = maybe_reverse("campus_map")
        if not url:
            self.skipTest("campus_map URL not found")
        s = self.client.session
        s["user_id"] = self.user.id
        s["user_type"] = "student"
        s.save()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8")
       
        self.assertIn('id="map"', html)
        self.assertIn('floor-btn', html)
