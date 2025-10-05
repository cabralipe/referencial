"""Consumers de WebSocket para presença, streams e notificações."""

from __future__ import annotations

import json
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PresenceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.doc_type = self.scope["url_route"]["kwargs"].get("doc_type")
        self.doc_id = self.scope["url_route"]["kwargs"].get("object_id")
        self.group_name = f"presence.{self.doc_type}.{self.doc_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence.join",
                "payload": {
                    "user_id": self.scope.get("user").id if self.scope.get("user") else None,
                },
            },
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence.leave",
                "payload": {
                    "user_id": self.scope.get("user").id if self.scope.get("user") else None,
                },
            },
        )

    async def receive_json(self, content: Any, **kwargs):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence.event",
                "payload": content,
            },
        )

    async def presence_join(self, event):
        await self.send_json({"event": "join", **event["payload"]})

    async def presence_leave(self, event):
        await self.send_json({"event": "leave", **event["payload"]})

    async def presence_event(self, event):
        await self.send_json({"event": "event", **event["payload"]})


class StreamConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.alvo_tipo = self.scope["url_route"]["kwargs"].get("alvo_tipo")
        self.alvo_id = self.scope["url_route"]["kwargs"].get("alvo_id")
        self.group_name = f"stream.{self.alvo_tipo}.{self.alvo_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def broadcast(self, event):
        await self.send_json(event["payload"])


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.group_name = f"user.{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def deliver(self, event):
        await self.send_json(event["payload"])
