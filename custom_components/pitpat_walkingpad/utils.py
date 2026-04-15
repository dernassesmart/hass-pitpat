"""Utility helpers for the PitPat WalkingPad integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class TemporaryValue(Generic[T]):
    """Holds a value that expires at a given timestamp.

    Used to give the UI immediate optimistic feedback while waiting for
    the next real status notification from the device.
    """

    _value: T | None = field(default=None, init=False)
    _expiration: float = field(default=0.0, init=False)

    @property
    def has_value(self) -> bool:
        return self._value is not None

    def set(self, value: T, expiration_timestamp: float) -> None:
        self._value = value
        self._expiration = expiration_timestamp

    def get(self, current_timestamp: float, fallback: T) -> T:
        """Return the temporary value if still valid, else the fallback."""
        if self._value is not None and current_timestamp <= self._expiration:
            return self._value
        self._value = None
        return fallback

    def peek(self, fallback: T) -> T:
        """Return the temporary value without expiry check, else fallback."""
        return self._value if self._value is not None else fallback

    def is_expired(self, current_timestamp: float) -> bool:
        """Return True if the value has expired or was never set."""
        return self._value is None or current_timestamp > self._expiration

    def reset(self) -> None:
        self._value = None
        self._expiration = 0.0
