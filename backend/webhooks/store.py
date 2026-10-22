"""AEGIS Webhook Delivery Store & Idempotency Ledger.

Tracks processed X-GitHub-Delivery IDs to prevent duplicate work
and guarantee idempotent writes across webhook redeliveries.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DELIVERIES_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "webhook_deliveries.json"


class WebhookDeliveryStore:
    """In-memory and file-backed idempotency ledger for GitHub webhook deliveries."""

    def __init__(self, storage_path: Path = DELIVERIES_FILE_PATH) -> None:
        self.storage_path = storage_path
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._memory_cache = json.load(f)
            except Exception:
                self._memory_cache = {}

    def _save(self) -> None:
        try:
            temp_path = self.storage_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._memory_cache, f, indent=2)
            temp_path.replace(self.storage_path)
        except Exception:
            pass

    def is_processed(self, delivery_id: str) -> bool:
        """Check if delivery_id has already been processed or is currently in flight."""
        return delivery_id in self._memory_cache

    def get_delivery(self, delivery_id: str) -> Optional[dict[str, Any]]:
        """Retrieve execution record for delivery_id."""
        return self._memory_cache.get(delivery_id)

    def record_delivery(
        self,
        delivery_id: str,
        event_type: str,
        action: Optional[str] = None,
        status: str = "accepted",
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Record delivery attempt with metadata."""
        rec = {
            "delivery_id": delivery_id,
            "event_type": event_type,
            "action": action,
            "status": status,
            "details": details or {},
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        self._memory_cache[delivery_id] = rec
        self._save()
        return rec

    def update_delivery_result(self, delivery_id: str, status: str, details: dict[str, Any]) -> None:
        """Update asynchronous execution results."""
        if delivery_id in self._memory_cache:
            self._memory_cache[delivery_id]["status"] = status
            self._memory_cache[delivery_id]["details"].update(details)
            self._memory_cache[delivery_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def clear(self) -> None:
        """Clear ledger (useful for isolated tests)."""
        self._memory_cache.clear()
        if self.storage_path.exists():
            try:
                self.storage_path.unlink()
            except Exception:
                pass


_store_instance: Optional[WebhookDeliveryStore] = None


def get_delivery_store() -> WebhookDeliveryStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = WebhookDeliveryStore()
    return _store_instance
