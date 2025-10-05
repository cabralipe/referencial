"""Consumers de WebSocket para presença e locks."""

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
