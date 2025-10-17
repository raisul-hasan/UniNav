import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message, Student, Teacher, Reaction, Group
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_type = self.scope['url_route']['kwargs']['chat_type']
        self.id = self.scope['url_route']['kwargs']['id']
        self.room_group_name = f"chat_{self.chat_type}_{self.id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')

        if action == 'message':
            content = text_data_json['content']
            sender_id = text_data_json['sender_id']
            sender_type = text_data_json['sender_type']
            file_url = text_data_json.get('file_url')
            voice_url = text_data_json.get('voice_url')
            latitude = text_data_json.get('latitude')
            longitude = text_data_json.get('longitude')

            message_obj = await self.save_message(sender_id, sender_type, content, file_url, voice_url, latitude, longitude)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'content': content,
                    'sender_id': sender_id,
                    'sender_type': sender_type,
                    'message_id': message_obj.id if message_obj else None,
                    'file_url': file_url,
                    'voice_url': voice_url,
                    'latitude': latitude,
                    'longitude': longitude,
                }
            )
        elif action == 'reaction':
            message_id = text_data_json['message_id']
            emoji = text_data_json['emoji']
            sender_id = text_data_json['sender_id']
            sender_type = text_data_json['sender_type']

            reaction_obj = await self.save_reaction(message_id, sender_id, sender_type, emoji)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_reaction',
                    'message_id': message_id,
                    'emoji': emoji,
                    'sender_id': sender_id,
                    'sender_type': sender_type,
                    'created': bool(reaction_obj),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'action': 'message',
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_type': event['sender_type'],
            'message_id': event['message_id'],
            'file_url': event['file_url'],
            'voice_url': event['voice_url'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
        }))

    async def chat_reaction(self, event):
        await self.send(text_data=json.dumps({
            'action': 'reaction',
            'message_id': event['message_id'],
            'emoji': event['emoji'],
            'sender_id': event['sender_id'],
            'sender_type': event['sender_type'],
            'created': event['created'],
        }))

    @sync_to_async
    def save_message(self, sender_id, sender_type, content, file_url, voice_url, latitude, longitude):
        try:
            if sender_type == "student":
                sender = Student.objects.get(id=sender_id)
                teacher_sender = None
            elif sender_type == "teacher":
                sender = None
                teacher_sender = Teacher.objects.get(id=sender_id)
            else:
                return None
            
            msg = Message(
                sender=sender,
                teacher_sender=teacher_sender,
                content=content,
                latitude=latitude if latitude else None,
                longitude=longitude if longitude else None,
            )
            
            if self.chat_type == 'group':
                group = Group.objects.get(id=self.id)
                msg.group = group
            else:
                recipient = Student.objects.get(id=self.id)
                msg.recipient = recipient
            
            msg.save()
            return msg
        except (Student.DoesNotExist, Teacher.DoesNotExist, Group.DoesNotExist):
            return None

    @sync_to_async
    def save_reaction(self, message_id, sender_id, sender_type, emoji):
        try:
            if sender_type == "student":
                user = Student.objects.get(id=sender_id)
                teacher = None
            elif sender_type == "teacher":
                user = None
                teacher = Teacher.objects.get(id=sender_id)
            else:
                return None
            
            message = Message.objects.get(id=message_id)
            reaction, created = Reaction.objects.get_or_create(
                message=message, user=user, teacher=teacher, emoji=emoji,
                defaults={'created_at': timezone.now()}
            )
            if not created:
                reaction.delete()
                return None
            return reaction
        except (Student.DoesNotExist, Teacher.DoesNotExist, Message.DoesNotExist):
            return None