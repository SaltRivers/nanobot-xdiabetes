# Channel Plugin Guide

Build a custom channel integration in three steps: subclass, package, install.

## How It Works

The runtime discovers channel plugins through Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/). When `x-diabetes gateway` starts, it scans:

1. Built-in channels in `x-diabetes/channels/`
2. External packages registered under the `xdiabetes.channels` entry point group

If a matching config section has `"enabled": true`, the channel is instantiated and started.

## Quick Start

We'll build a minimal webhook channel that receives messages via HTTP POST and sends replies back.

### Project Structure

```text
x-diabetes-channel-webhook/
├── x_diabetes_channel_webhook/
│   ├── __init__.py
│   └── channel.py
└── pyproject.toml
```

### 1. Create Your Channel

```python
# x_diabetes_channel_webhook/__init__.py
from x_diabetes_channel_webhook.channel import WebhookChannel

__all__ = ["WebhookChannel"]
```

```python
# x_diabetes_channel_webhook/channel.py
import asyncio
from typing import Any

from aiohttp import web
from loguru import logger

from xdiabetes.channels.base import BaseChannel
from xdiabetes.bus.events import OutboundMessage


class WebhookChannel(BaseChannel):
    name = "webhook"
    display_name = "Webhook"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"enabled": False, "port": 9000, "allowFrom": []}

    async def start(self) -> None:
        self._running = True
        port = self.config.get("port", 9000)

        app = web.Application()
        app.router.add_post("/message", self._on_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info("Webhook listening on :{}", port)

        while self._running:
            await asyncio.sleep(1)

        await runner.cleanup()

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        logger.info("[webhook] -> {}: {}", msg.chat_id, msg.content[:80])

    async def _on_request(self, request: web.Request) -> web.Response:
        body = await request.json()
        sender = body.get("sender", "unknown")
        chat_id = body.get("chat_id", sender)
        text = body.get("text", "")
        media = body.get("media", [])

        await self._handle_message(
            sender_id=sender,
            chat_id=chat_id,
            content=text,
            media=media,
        )

        return web.json_response({"ok": True})
```

### 2. Register the Entry Point

```toml
# pyproject.toml
[project]
name = "x-diabetes-channel-webhook"
version = "0.1.0"
dependencies = ["x-diabetes-ai", "aiohttp"]

[project.entry-points."xdiabetes.channels"]
webhook = "x_diabetes_channel_webhook:WebhookChannel"
```

### 3. Install & Configure

```bash
pip install -e .
x-diabetes onboard
```

Edit `~/.x-diabetes/config.json`:

```json
{
  "channels": {
    "webhook": {
      "enabled": true,
      "port": 9000,
      "allowFrom": ["*"]
    }
  }
}
```

### 4. Run & Test

```bash
x-diabetes gateway
```

In another terminal:

```bash
curl -X POST http://localhost:9000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "user1", "chat_id": "user1", "text": "Hello!"}'
```

## Naming Convention

| What | Format | Example |
|------|--------|---------|
| Package name | `x-diabetes-channel-{name}` | `x-diabetes-channel-webhook` |
| Entry point key | `{name}` | `webhook` |
| Config section | `channels.{name}` | `channels.webhook` |
| Python package | `x_diabetes_channel_{name}` | `x_diabetes_channel_webhook` |
