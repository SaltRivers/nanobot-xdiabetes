"""Chat channels module with plugin architecture."""

from xdiabetes.channels.base import BaseChannel
from xdiabetes.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
