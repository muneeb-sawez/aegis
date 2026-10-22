"""AEGIS GitHub Webhook Endpoints.

Mounts:
  POST /webhooks/github       (and alias POST /api/webhooks/github)
  GET  /webhooks/deliveries/{delivery_id}

Verifies X-Hub-Signature-256 with hmac.compare_digest.
Returns 200 quickly and enqueues work via FastAPI BackgroundTasks.
Guarantees idempotent writes and skips duplicate redeliveries.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.webhooks.processor import process_github_event
from backend.webhooks.store import get_delivery_store
from backend.webhooks.verify import verify_github_signature

router = APIRouter(tags=["webhooks"])


class WebhookResponse(BaseModel):
    status: str = Field(..., description="'accepted', 'duplicate', or 'error'")
    message: str
    delivery_id: str
    event: Optional[str] = None
    action: Optional[str] = None
    redelivery: bool = False


async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header("ping", alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
    project_id: Optional[str] = Query(None, alias="project_id"),
) -> WebhookResponse:
    """Core webhook ingestion logic shared across /webhooks/github and /api/webhooks/github."""
    raw_body = await request.body()

    # 1. Verify HMAC-SHA256 signature with hmac.compare_digest
    if not verify_github_signature(raw_body, x_hub_signature_256):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing X-Hub-Signature-256 webhook signature",
        )

    # 2. Extract or generate delivery GUID
    delivery_id = x_github_delivery or f"del-{uuid.uuid4().hex[:12]}"
    event_type = (x_github_event or "ping").strip().lower()
    target_pid = x_project_id or project_id or "demo"

    # 3. Idempotency Check: handle redelivery quickly without duplicate writes
    store = get_delivery_store()
    if store.is_processed(delivery_id):
        existing = store.get_delivery(delivery_id) or {}
        return WebhookResponse(
            status="duplicate",
            message=f"Webhook delivery '{delivery_id}' has already been processed (idempotent skip).",
            delivery_id=delivery_id,
            event=event_type,
            action=existing.get("action"),
            redelivery=True,
        )

    # 4. Parse payload
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed JSON payload: {e}")

    action = payload.get("action")

    # 5. Record delivery attempt in idempotency store
    store.record_delivery(
        delivery_id=delivery_id,
        event_type=event_type,
        action=action,
        status="queued",
        details={"project_id": target_pid},
    )

    # 6. Enqueue work asynchronously (scan only changed files, assess risk, idempotent writes)
    background_tasks.add_task(
        process_github_event,
        event_type=event_type,
        payload=payload,
        delivery_id=delivery_id,
        project_id=target_pid,
    )

    # 7. Return 200 quickly to GitHub
    return WebhookResponse(
        status="accepted",
        message=f"Webhook {event_type} delivery {delivery_id} verified and enqueued for scanning.",
        delivery_id=delivery_id,
        event=event_type,
        action=action,
        redelivery=False,
    )


@router.post("/webhooks/github", response_model=WebhookResponse)
async def github_webhook_root(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header("ping", alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
    project_id: Optional[str] = Query(None, alias="project_id"),
) -> WebhookResponse:
    """GitHub webhook receiver mounted at POST /webhooks/github."""
    return await handle_github_webhook(
        request=request,
        background_tasks=background_tasks,
        x_hub_signature_256=x_hub_signature_256,
        x_github_event=x_github_event,
        x_github_delivery=x_github_delivery,
        x_project_id=x_project_id,
        project_id=project_id,
    )


@router.post("/api/webhooks/github", response_model=WebhookResponse)
async def github_webhook_api(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header("ping", alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
    project_id: Optional[str] = Query(None, alias="project_id"),
) -> WebhookResponse:
    """Alias GitHub webhook receiver mounted at POST /api/webhooks/github."""
    return await handle_github_webhook(
        request=request,
        background_tasks=background_tasks,
        x_hub_signature_256=x_hub_signature_256,
        x_github_event=x_github_event,
        x_github_delivery=x_github_delivery,
        x_project_id=x_project_id,
        project_id=project_id,
    )


@router.get("/webhooks/deliveries/{delivery_id}")
def get_webhook_delivery_status(delivery_id: str) -> dict[str, Any]:
    """Query execution results and risk report for a webhook delivery."""
    store = get_delivery_store()
    rec = store.get_delivery(delivery_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Delivery '{delivery_id}' not found")
    return rec
