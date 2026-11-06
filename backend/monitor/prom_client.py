"""Prometheus Client for AEGIS Monitor."""

from __future__ import annotations
import os
import requests
import logging

logger = logging.getLogger(__name__)

class PromClient:
    def __init__(self):
        self.url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")

    def query(self, query: str) -> list[dict]:
        try:
            resp = requests.get(f"{self.url}/api/v1/query", params={"query": query}, timeout=2)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
        except Exception as e:
            logger.warning("Prometheus query failed: %s", e)
        return []

prom_client = PromClient()
