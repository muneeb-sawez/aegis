"""AEGIS Graph Chatbot Conversation & Entity Memory Store.

Retains turn-by-turn chat history, tracked entities, and graph mutations per (project_id, session_id).
Enables natural anaphoric references (e.g. "connect it to checkout", "what was its port?").
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("aegis.agent.chat_memory")


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = Field(default_factory=time.time)
    actions: Optional[list[dict[str, Any]]] = None


class SessionState(BaseModel):
    project_id: str
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_nodes: list[dict[str, Any]] = Field(default_factory=list)
    modified_edges: list[dict[str, Any]] = Field(default_factory=list)
    last_referenced_node: Optional[str] = None
    last_referenced_edge: Optional[dict[str, str]] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ChatMemoryStore:
    """In-memory multi-tenant chat session and entity registry."""

    def __init__(self, max_messages: int = 25):
        self._sessions: dict[str, SessionState] = {}
        self.max_messages = max_messages

    def _key(self, project_id: str, session_id: str) -> str:
        return f"{project_id.strip()}::{session_id.strip()}"

    def get_or_create_session(self, project_id: str, session_id: str) -> SessionState:
        key = self._key(project_id, session_id)
        if key not in self._sessions:
            self._sessions[key] = SessionState(
                project_id=project_id.strip(),
                session_id=session_id.strip(),
            )
        return self._sessions[key]

    def add_user_message(self, project_id: str, session_id: str, content: str) -> ChatMessage:
        session = self.get_or_create_session(project_id, session_id)
        msg = ChatMessage(role="user", content=content.strip())
        session.messages.append(msg)
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages:]
        session.updated_at = time.time()
        return msg

    def add_assistant_message(
        self,
        project_id: str,
        session_id: str,
        content: str,
        actions: Optional[list[dict[str, Any]]] = None,
    ) -> ChatMessage:
        session = self.get_or_create_session(project_id, session_id)
        msg = ChatMessage(role="assistant", content=content.strip(), actions=actions)
        session.messages.append(msg)
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages:]
        session.updated_at = time.time()
        return msg

    def record_node_creation(
        self,
        project_id: str,
        session_id: str,
        node_id: str,
        label: str = "Service",
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        session = self.get_or_create_session(project_id, session_id)
        session.last_referenced_node = node_id
        # Prevent duplicate entries in created_nodes list
        existing = [n for n in session.created_nodes if n.get("id") == node_id]
        if not existing:
            session.created_nodes.append({
                "id": node_id,
                "label": label,
                "properties": properties or {},
                "created_at": time.time(),
            })

    def record_edge_action(
        self,
        project_id: str,
        session_id: str,
        source: str,
        target: str,
        edge_type: str = "CALLS",
        action: str = "created",
    ) -> None:
        session = self.get_or_create_session(project_id, session_id)
        session.last_referenced_edge = {
            "source": source,
            "target": target,
            "type": edge_type,
        }
        session.modified_edges.append({
            "source": source,
            "target": target,
            "type": edge_type,
            "action": action,
            "timestamp": time.time(),
        })

    def get_history(self, project_id: str, session_id: str) -> list[ChatMessage]:
        session = self.get_or_create_session(project_id, session_id)
        return list(session.messages)

    def get_session_entities(self, project_id: str, session_id: str) -> dict[str, Any]:
        session = self.get_or_create_session(project_id, session_id)
        return {
            "created_nodes": session.created_nodes,
            "modified_edges": session.modified_edges,
            "last_referenced_node": session.last_referenced_node,
            "last_referenced_edge": session.last_referenced_edge,
            "total_messages": len(session.messages),
        }

    def clear(self, project_id: str, session_id: str) -> None:
        key = self._key(project_id, session_id)
        if key in self._sessions:
            del self._sessions[key]


_chat_memory_instance: Optional[ChatMemoryStore] = None


def get_chat_memory() -> ChatMemoryStore:
    global _chat_memory_instance
    if _chat_memory_instance is None:
        _chat_memory_instance = ChatMemoryStore()
    return _chat_memory_instance
