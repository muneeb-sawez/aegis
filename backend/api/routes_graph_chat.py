"""AEGIS Graph AI Chatbot API Endpoints.

Provides conversational Q&A for explaining repository microservices, dynamic node
creation/connection/rewiring, session memory tracking, and immediate persistence.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.agent.chat_memory import get_chat_memory
from backend.agent.graph_copilot import run_graph_copilot
from backend.api.schemas import TopologyResponse
from backend.graph import get_repository

router = APIRouter(prefix="/api/graph/chat", tags=["graph-chat"])


class GraphChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or natural language instruction")
    project_id: str = Field(default="demo", description="Active project tenant ID")
    session_id: str = Field(default="default", description="Session identifier for memory isolation")


class GraphChatResponse(BaseModel):
    reply: str
    actions: list[dict[str, Any]]
    executed_actions: list[dict[str, Any]]
    total_nodes: int
    total_edges: int
    project_id: str
    nodes: list[Any] = Field(default_factory=list)
    edges: list[Any] = Field(default_factory=list)


@router.post("", response_model=GraphChatResponse)
async def chat_with_graph_copilot(req: GraphChatRequest) -> GraphChatResponse:
    """Send a natural language instruction or query to the Graph AI Copilot.

    Explains microservices in the active repo, adds/modifies/deletes nodes and edges,
    and returns conversational explanations alongside fresh topology data.
    """
    clean_msg = req.message.strip()
    if not clean_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    pid = req.project_id.strip() or "demo"
    sid = req.session_id.strip() or "default"

    copilot_res = await run_graph_copilot(
        project_id=pid,
        session_id=sid,
        user_message=clean_msg,
    )

    # Fetch updated topology so frontend gets latest state in the same response
    repo = get_repository()
    topo = repo.get_topology(project_id=pid)

    return GraphChatResponse(
        reply=copilot_res.reply,
        actions=[a.model_dump() for a in copilot_res.actions],
        executed_actions=copilot_res.executed_actions,
        total_nodes=len(topo.nodes),
        total_edges=len(topo.edges),
        project_id=pid,
        nodes=topo.nodes,
        edges=topo.edges,
    )


@router.get("/history")
def get_chat_history(
    project_id: str = Query("demo", description="Active project ID"),
    session_id: str = Query("default", description="Session ID"),
) -> dict[str, Any]:
    """Retrieve turn-by-turn conversation history and tracked session entities."""
    chat_mem = get_chat_memory()
    history = chat_mem.get_history(project_id=project_id, session_id=session_id)
    entities = chat_mem.get_session_entities(project_id=project_id, session_id=session_id)
    return {
        "project_id": project_id,
        "session_id": session_id,
        "messages": [m.model_dump() for m in history],
        "entities": entities,
    }


@router.delete("/history")
def clear_chat_history(
    project_id: str = Query("demo", description="Active project ID"),
    session_id: str = Query("default", description="Session ID"),
) -> dict[str, str]:
    """Clear conversation history and entity memory for the given session."""
    chat_mem = get_chat_memory()
    chat_mem.clear(project_id=project_id, session_id=session_id)
    return {
        "status": "ok",
        "message": f"Cleared chat history for project '{project_id}', session '{session_id}'",
    }
