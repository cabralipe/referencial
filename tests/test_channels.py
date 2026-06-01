import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from asgiref.sync import async_to_sync
from channels_redis.core import RedisChannelLayer
from django.conf import settings

from sockets.consumers import PresenceConsumer


@pytest.fixture(autouse=True)
def habilitar_flags():
    pass


def test_presence_consumer_broadcast():
    usuario = SimpleNamespace(id=123)
    consumer = PresenceConsumer()
    consumer.scope = {
        "url_route": {
            "args": (),
            "kwargs": {"doc_type": "texto_unico", "object_id": "1"},
        },
        "user": usuario,
    }
    consumer.channel_name = "test-channel"

    messages = []

    async def fake_base_send(message):
        messages.append(message)

    consumer.base_send = fake_base_send  # type: ignore
    consumer.close = AsyncMock()  # type: ignore

    consumer.channel_layer = SimpleNamespace(
        group_add=AsyncMock(),
        group_discard=AsyncMock(),
        group_send=AsyncMock(),
    )

    async def scenario():
        await consumer.connect()
        await consumer.receive_json({"action": "typing"})
        await consumer.disconnect(1000)

    async_to_sync(scenario)()

    consumer.channel_layer.group_add.assert_awaited_with(
        "presence.texto_unico.1", consumer.channel_name
    )
    assert consumer.channel_layer.group_send.await_args_list[0].args[1]["type"] == "presence.join"
    assert consumer.channel_layer.group_send.await_args_list[1].args[1]["type"] == "presence.event"
    assert consumer.channel_layer.group_send.await_args_list[1].args[1]["payload"]["action"] == "typing"

    async_to_sync(consumer.presence_join)({"payload": {"user_id": usuario.id}})
    async_to_sync(consumer.presence_event)({"payload": {"action": "typing"}})

    payloads = [json.loads(msg["text"]) for msg in messages if msg.get("type") == "websocket.send"]
    assert payloads[0]["event"] == "join"
    assert payloads[0]["user_id"] == usuario.id
    assert payloads[1]["event"] == "event"
    assert payloads[1]["action"] == "typing"


def test_channel_redis_socket_timeout_exceeds_blocking_read_timeout():
    host_config = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]

    assert host_config["socket_timeout"] > RedisChannelLayer.brpop_timeout
