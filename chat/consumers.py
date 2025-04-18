import json
import os
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Message
from asgiref.sync import sync_to_async
from uuid import uuid4

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        user1 = self.scope['user'].username 
        user2 = self.room_name
        self.room_group_name = f"chat_{''.join(sorted([user1, user2]))}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        # Check if it's a text message or an audio message
        if 'message' in text_data_json:
            # Handle text message
            message = text_data_json['message']
            sender = self.scope['user']
            receiver = await self.get_receiver_user()

            await self.save_message(sender, receiver, message)

            # Send the message to WebSocket
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender': sender.username,
                    'receiver': receiver.username,
                    'message': message
                }
            )
        elif 'audio' in text_data_json:
            # Handle audio message
            audio_data = text_data_json['audio']
            audio_format = text_data_json.get('audio_format', 'webm')
            sender = self.scope['user']
            receiver = await self.get_receiver_user()

            # Decode base64 audio
            audio_file_path = await self.decode_audio(audio_data, audio_format)

            # Save the audio message
            audio_url = await self.save_audio_message(sender, receiver, audio_file_path, audio_format)

            # Send the audio message to WebSocket
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_audio_message',
                    'sender': sender.username,
                    'receiver': receiver.username,
                    'audio_url': audio_url
                }
            )

    async def chat_message(self, event):
        # Send text message to WebSocket
        await self.send(text_data=json.dumps({
            'sender': event['sender'],
            'receiver': event['receiver'],
            'message': event['message']
        }))

    async def chat_audio_message(self, event):
        # Send audio message to WebSocket
        await self.send(text_data=json.dumps({
            'sender': event['sender'],
            'receiver': event['receiver'],
            'audio_url': event['audio_url']
        }))

    @sync_to_async
    def save_message(self, sender, receiver, message):
        # Save the text message to the database
        Message.objects.create(sender=sender, receiver=receiver, content=message)

    @sync_to_async
    def get_receiver_user(self):
        # Retrieve the receiver user from the database
        return User.objects.get(username=self.room_name)

    async def decode_audio(self, audio_data, audio_format):
        # Define the directory where you want to store the audio files
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        
        # Create the directory if it does not exist
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)

        # Generate a unique filename for the audio file
        audio_file_name = f"{uuid4()}.{audio_format}"
        audio_file_path = os.path.join(audio_dir, audio_file_name)
        
        # Decode and write the audio data to the file
        with open(audio_file_path, 'wb') as audio_file:
            audio_file.write(base64.b64decode(audio_data))
        
        return audio_file_path

    @sync_to_async
    def save_audio_message(self, sender, receiver, audio_file_path, audio_format):
        # Save the audio file to the database and return the URL
        audio_file_name = os.path.basename(audio_file_path)

        # Create the relative URL for the audio file
        audio_url = settings.MEDIA_URL + 'audio/' + audio_file_name

        # Save the message with the audio URL in the database
        Message.objects.create(
            sender=sender,
            receiver=receiver,
            content='🎤 Voice message',  # Placeholder for the audio message
            audio_file=audio_url  # Assuming you have an `audio_file` field in your Message model
        )

        return audio_url


