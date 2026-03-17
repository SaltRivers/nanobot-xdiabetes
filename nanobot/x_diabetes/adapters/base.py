"""Base interface for X-Diabetes DTMH adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from nanobot.x_diabetes.schemas import DTMHRequest, DTMHResult


class DTMHAdapter(ABC):
    """Abstract adapter interface.

    All DTMH backends must implement the same synchronous contract so the tool
    layer does not need to know whether the real model is local, remote, or
    still unavailable.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend name."""

    @abstractmethod
    def analyze(self, request: DTMHRequest) -> DTMHResult:
        """Run DTMH analysis for a patient request."""
