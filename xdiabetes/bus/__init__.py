"""Message bus module for decoupled channel-agent communication."""

from xdiabetes.bus.events import InboundMessage, OutboundMessage
from xdiabetes.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
