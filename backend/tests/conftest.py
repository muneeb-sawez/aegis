"""AEGIS Pytest Configuration & Fixtures.

Provides clean repository isolation (autouse fixture) so each test executes
against an isolated, freshly-seeded graph state without residual mutations.
"""

import pytest
from backend.graph import get_repository


@pytest.fixture(autouse=True)
def isolate_graph_repository():
    """Ensure the GraphRepository is reset to clean baseline before and after each test."""
    repo = get_repository()
    repo.reset()
    yield
    repo.reset()
