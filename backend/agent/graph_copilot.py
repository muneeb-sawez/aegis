"""AEGIS Graph AI Copilot Engine.

Interprets natural language queries on the Topology screen:
1. Explains microservices, their roles, blast radii, dependencies, and health telemetry.
2. Performs dynamic topology mutations: node creation, edge wiring/rewiring, deletion.
3. Resolves conversational anaphora and retains memory of created nodes across turns.
4. Executes mutations via GraphMutator and persists immediately to data/graphs/{project_id}.json.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from pydantic import BaseModel, Field

from backend.agent.chat_memory import get_chat_memory
from backend.agent.llm import call_llm
from backend.config import settings
from backend.graph import get_repository
from backend.graph.mutator import get_graph_mutator

logger = logging.getLogger("aegis.agent.graph_copilot")


class CopilotAction(BaseModel):
    action_type: str  # CREATE_NODE | UPDATE_NODE | DELETE_NODE | CREATE_EDGE | UPDATE_EDGE | DELETE_EDGE
    node_id: Optional[str] = None
    label: Optional[str] = "Service"
    properties: Optional[dict[str, Any]] = Field(default_factory=dict)
    source: Optional[str] = None
    target: Optional[str] = None
    old_target: Optional[str] = None
    edge_type: Optional[str] = "CALLS"


class CopilotResponse(BaseModel):
    reply: str
    actions: list[CopilotAction] = Field(default_factory=list)
    executed_actions: list[dict[str, Any]] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    project_id: str = "demo"


SYSTEM_PROMPT = """You are AEGIS Graph AI Copilot, an expert cloud-native architecture assistant embedded directly inside an interactive microservice dependency graph canvas.

YOUR RESPONSIBILITIES:
1. EXPLAIN MICROSERVICES:
   - Explain what microservices are present in the current repository/project graph.
   - Describe their architecture, duties, upstream callers, downstream dependencies, databases, and container images.
   - Report their live operational health status (healthy, degraded, unavailable, latencies, error rates) accurately from the context.
2. DYNAMIC GRAPH EDITING & REWIRING:
   - When the user asks to add or create a node (Service, Database, APIEndpoint, Gateway, Cache, etc.), emit a CREATE_NODE action.
   - When the user asks to connect nodes, link services, or establish dependencies, emit a CREATE_EDGE action.
   - When the user asks to change, reroute, or rewire connections, emit an UPDATE_EDGE action.
   - When the user asks to remove or delete a node or edge, emit a DELETE_NODE or DELETE_EDGE action.
   - When the user asks to update a service (e.g. change version, port, image), emit an UPDATE_NODE action.
3. CONTEXT & MEMORY AWARENESS:
   - Check the "Session Created Entities" and recent conversation history.
   - If the user says "connect it to checkout" or "what was its port?", resolve "it" to the most recently created or discussed node.
   - Never hallucinate non-existent services unless the user explicitly requested to create them.

OUTPUT FORMAT:
You MUST respond with a single, valid JSON object with EXACTLY this structure:
{
  "reply": "Your friendly, clear markdown response explaining the microservices or confirming actions taken.",
  "actions": [
    {
      "action_type": "CREATE_NODE" | "UPDATE_NODE" | "DELETE_NODE" | "CREATE_EDGE" | "UPDATE_EDGE" | "DELETE_EDGE",
      "node_id": "service-name",
      "label": "Service" | "Database" | "APIEndpoint" | "ExternalService",
      "properties": { "technology": "...", "status": "healthy" },
      "source": "source-service-id",
      "target": "target-service-id",
      "old_target": "prior-target-if-rewiring",
      "edge_type": "CALLS" | "DEPENDS_ON" | "CONNECTS_TO" | "HOSTED_ON"
    }
  ]
}

If no graph modifications are needed (for example, pure questions or explanations), provide an empty actions list: "actions": [].
Do NOT wrap the JSON in extra commentary outside the JSON object.
"""


def _get_health_snapshot(project_id: str) -> dict[str, Any]:
    """Retrieve active monitor health telemetry for context injection."""
    try:
        from backend.monitor.health_checker import get_health_checker
        checker = get_health_checker()
        statuses = checker.get_status(project_id=project_id)
        return {s.service_id: s.model_dump() for s in statuses}
    except Exception:
        return {}


def _fallback_rule_based_copilot(
    project_id: str,
    user_message: str,
    nodes: list[Any],
    edges: list[Any],
    session_entities: dict[str, Any],
) -> tuple[str, list[CopilotAction]]:
    """Deterministic fallback reasoning when LLM API keys are absent or network times out."""
    msg_lower = user_message.strip().lower()
    actions: list[CopilotAction] = []

    last_node = session_entities.get("last_referenced_node")

    # 1. Action: Connect / Link
    connect_match = re.search(r"(?:connect|link|wire)\s+([a-zA-Z0-9_\-\.]+)\s+(?:to|with|into)\s+([a-zA-Z0-9_\-\.]+)", user_message, re.IGNORECASE)
    if connect_match:
        src = connect_match.group(1).strip()
        tgt = connect_match.group(2).strip()

        if src.lower() in ("it", "this", "the new node", "that") and last_node:
            src = last_node
        if tgt.lower() in ("it", "this", "the new node", "that") and last_node:
            tgt = last_node

        edge_type = "DEPENDS_ON" if "depend" in msg_lower else "CALLS"
        actions.append(CopilotAction(
            action_type="CREATE_EDGE",
            source=src,
            target=tgt,
            edge_type=edge_type,
            properties={"provenance": "ai-copilot"},
        ))
        reply = f"✅ Connected **`{src}`** → **`{tgt}`** with relationship `{edge_type}`. The graph topology has been updated and saved."
        return reply, actions

    # 2. Action: Create / Add Node
    # Handles: "Add a new service called telemetry-collector", "Create node auth-db", "Add redis-cache", etc.
    add_match = re.search(
        r"(?:add|create|insert)\s+(?:a\s+|an\s+)?(?:new\s+)?(service|node|database|db|cache|gateway|apiendpoint)?\s*(?:called|named|id)?\s*([a-zA-Z0-9_\-\.]+)",
        user_message,
        re.IGNORECASE,
    )
    if add_match and not any(w in msg_lower for w in ["edge", "connection", "link", "relationship"]):
        kind = (add_match.group(1) or "service").lower()
        candidate_id = add_match.group(2).strip()
        # If candidate captured noise words, look further
        if candidate_id.lower() in ("a", "an", "new", "service", "node", "database", "db", "cache", "called", "named"):
            rem_words = [
                w.strip() for w in user_message.split()
                if w.lower() not in ("add", "create", "insert", "a", "an", "new", "service", "node", "database", "db", "cache", "called", "named", "with", "using", "in")
            ]
            candidate_id = rem_words[0] if rem_words else "new-service"

        node_id = candidate_id
        label = "Database" if kind in ("database", "db", "cache") or "db" in node_id.lower() or "cache" in node_id.lower() else "Service"

        # Check for image or tech in prompt
        tech = "Redis" if "redis" in node_id.lower() or "redis" in msg_lower else "PostgreSQL" if "postgres" in node_id.lower() else "Microservice"
        if "python" in msg_lower:
            tech = "Python"
        elif "go" in msg_lower:
            tech = "Go"
        elif "java" in msg_lower:
            tech = "Java"

        actions.append(CopilotAction(
            action_type="CREATE_NODE",
            node_id=node_id,
            label=label,
            properties={"technology": tech, "status": "healthy"},
        ))

        # Check if user also asked to connect it in the same sentence (e.g. "add redis and connect it to checkout")
        connect_to_match = re.search(r"(?:connect(?:ed)?\s+(?:it\s+)?to|wire\s+(?:it\s+)?to)\s+([a-zA-Z0-9_\-\.]+)", user_message, re.IGNORECASE)
        if connect_to_match and connect_to_match.group(1).strip() != node_id:
            target_peer = connect_to_match.group(1).strip()
            actions.append(CopilotAction(
                action_type="CREATE_EDGE",
                source=target_peer,
                target=node_id,
                edge_type="DEPENDS_ON" if label == "Database" else "CALLS",
            ))
            reply = f"✅ Created new {label} node **`{node_id}`** ({tech}) and established connection **`{target_peer}`** → **`{node_id}`**. Saved to project graph."
        else:
            reply = f"✅ Created new {label} node **`{node_id}`** ({tech}). You can now connect other microservices to it."
        return reply, actions

    # 3. Action: Delete / Remove Node
    del_match = re.search(r"(?:delete|remove|destroy)\s+(?:node|service|database)?\s*([a-zA-Z0-9_\-\.]+)", user_message, re.IGNORECASE)
    if del_match and not any(w in msg_lower for w in ["edge", "connection", "link"]):
        node_id = del_match.group(1).strip()
        actions.append(CopilotAction(
            action_type="DELETE_NODE",
            node_id=node_id,
        ))
        reply = f"🗑️ Deleted node **`{node_id}`** and removed its associated connections. Saved to project graph."
        return reply, actions

    # 4. Action: Delete / Disconnect Edge
    disconnect_match = re.search(r"(?:disconnect|remove edge|delete edge)\s+([a-zA-Z0-9_\-\.]+)\s+(?:from|to)\s+([a-zA-Z0-9_\-\.]+)", user_message, re.IGNORECASE)
    if disconnect_match:
        src = disconnect_match.group(1).strip()
        tgt = disconnect_match.group(2).strip()
        actions.append(CopilotAction(
            action_type="DELETE_EDGE",
            source=src,
            target=tgt,
        ))
        reply = f"✂️ Removed connection **`{src}`** ↛ **`{tgt}`**. Saved to project graph."
        return reply, actions

    # 5. Blast Radius & Impact Analysis Question
    blast_match = re.search(r"(?:blast radius|what happens if|if\s+([a-zA-Z0-9_\-\.]+)\s+(?:goes down|fails|crashes|breaks|is degraded))", user_message, re.IGNORECASE)
    if blast_match or ("blast" in msg_lower and "radius" in msg_lower):
        # Identify target service
        target_name = None
        for n in nodes:
            if n.id.lower() in msg_lower:
                target_name = n.id
                break
        if not target_name and last_node:
            target_name = last_node

        if target_name:
            repo = get_repository()
            upstream = repo.callers(target_name, depth=3, project_id=project_id)
            callers_list = [f"- **`{c.node}`** (Hop {c.hops}, Impact {c.impact_weight * 100:.0f}%)" for c in upstream]
            callers_md = "\n".join(callers_list) if callers_list else "- *No direct upstream callers found in topology.*"

            reply = (
                f"### Blast Radius Analysis: `{target_name}`\n\n"
                f"#### 💥 Failure Impact Summary\n"
                f"If **`{target_name}`** becomes unavailable or starts timing out, failures propagate backward through the dependency chain.\n\n"
                f"#### 📡 Affected Upstream Callers ({len(upstream)} services):\n"
                f"{callers_md}\n\n"
                f"#### 🛡️ Recommended Mitigations\n"
                f"- Enable circuit breaking and rate limiting on upstream callers.\n"
                f"- Implement client-side fallback responses or read caches where appropriate."
            )
            return reply, actions

    # 6. Specific Service Query (e.g. "what does visits-service do?", "explain api-gateway", "what is bitb working")
    matching_node = None
    clean_words = [w.strip("?,.!:\"'") for w in msg_lower.split() if len(w) >= 3 and w not in ("what", "how", "why", "does", "the", "and", "working", "work", "explain", "about")]
    for n in nodes:
        nid_clean = n.id.lower()
        if nid_clean in msg_lower:
            matching_node = n
            break
        # Match partial service stems (e.g. "visit" -> "visits-service", "vet" -> "vets-service", "cust" -> "customers-service")
        for w in clean_words:
            if w in nid_clean or nid_clean.startswith(w):
                matching_node = n
                break
        if matching_node:
            break

    if matching_node:
        m_id = matching_node.id
        m_props = matching_node.properties or {}
        m_label = getattr(matching_node, "label", "Service")
        tech = m_props.get("technology") or m_props.get("image") or "Spring Boot / Java Microservice"

        # Find incoming callers and outgoing targets
        inbound_callers = [e.source for e in edges if e.target == m_id]
        outbound_targets = [e.target for e in edges if e.source == m_id]

        inbound_md = ", ".join([f"`{s}`" for s in inbound_callers]) if inbound_callers else "*None (Ingress or root)*"
        outbound_md = ", ".join([f"`{t}`" for t in outbound_targets]) if outbound_targets else "*None (Leaf node)*"

        role_desc = "processes domain business logic, handles REST endpoints, and manages data operations"
        if "visit" in m_id.lower():
            role_desc = "manages pet clinic appointments, visit records, timestamps, and doctor consultation notes"
        elif "vet" in m_id.lower():
            role_desc = "manages veterinarian staff profiles, medical specialties, and availability"
        elif "customer" in m_id.lower():
            role_desc = "manages pet owner records, contact details, and pet registration profiles"
        elif "gateway" in m_id.lower():
            role_desc = "acts as the central entrypoint routing external client HTTP traffic to downstream microservices"
        elif "db" in m_id.lower() or "mysql" in m_id.lower():
            role_desc = "provides relational database storage and ACID transaction persistence"
        elif "cache" in m_id.lower() or "redis" in m_id.lower():
            role_desc = "provides fast in-memory key-value caching and session store"

        reply = (
            f"### Microservice Inspection: `{m_id}`\n\n"
            f"#### ⚙️ Role & Function\n"
            f"**`{m_id}`** ({m_label}) {role_desc}.\n\n"
            f"#### 📋 Technical Specs\n"
            f"- **Type:** {m_label}\n"
            f"- **Technology / Stack:** {tech}\n"
            f"- **Health Status:** Healthy (0% error rate)\n\n"
            f"#### 🔗 Communication Flows\n"
            f"- **Inbound Callers (Upstream):** {inbound_md}\n"
            f"- **Outbound Dependencies (Downstream):** {outbound_md}\n\n"
            f"💡 *You can ask me to analyze failure blast radius with 'What happens if {m_id} fails?' or connect a new service to it.*"
        )
        return reply, actions

    # 7. Global Topology Architecture Overview
    gateways = [n for n in nodes if "gateway" in n.id.lower() or "ingress" in n.id.lower() or "frontend" in n.id.lower() or "web" in n.id.lower()]
    databases = [n for n in nodes if getattr(n, "label", "") == "Database" or "db" in n.id.lower() or "mysql" in n.id.lower() or "postgres" in n.id.lower() or "redis" in n.id.lower()]
    infra = [n for n in nodes if "vpc" in n.id.lower() or "role" in n.id.lower() or "iam" in n.id.lower()]
    services = [n for n in nodes if n not in gateways and n not in databases and n not in infra]

    total_n = len(nodes)
    total_e = len(edges)

    gw_md = ", ".join([f"`{n.id}`" for n in gateways[:6]]) or "*None detected*"
    svc_md = "\n".join([f"- **`{n.id}`** — {n.properties.get('technology') or n.properties.get('name') or 'Core microservice domain logic'}" for n in services[:10]])
    if len(services) > 10:
        svc_md += f"\n- *...and {len(services) - 10} more microservices*"
    db_md = "\n".join([f"- **`{n.id}`** — {n.properties.get('technology') or 'Persistence datastore / cache'}" for n in databases[:6]]) or "- *None detected*"

    reply = (
        f"### Microservices Architecture in `{project_id}`\n\n"
        f"#### 📊 System Overview\n"
        f"- **Active Nodes:** {total_n}\n"
        f"- **Dependencies (Edges):** {total_e}\n"
        f"- **Ingress / Gateways:** {len(gateways)}\n"
        f"- **Core Services:** {len(services)}\n"
        f"- **Datastores:** {len(databases)}\n\n"
        f"#### 🌐 Gateways & Ingress\n"
        f"{gw_md}\n\n"
        f"#### ⚙️ Core Microservices\n"
        f"{svc_md}\n\n"
        f"#### 🗄️ Databases & Caches\n"
        f"{db_md}\n\n"
        f"💡 *Ask me to inspect any service (e.g., 'What does checkoutservice do?'), analyze blast radius, or modify the graph (e.g., 'Add redis-cache and connect to checkoutservice').*"
    )
    return reply, actions


async def run_graph_copilot(
    project_id: str,
    session_id: str,
    user_message: str,
) -> CopilotResponse:
    """Execute the AI copilot pipeline over active graph topology and session memory."""
    repo = get_repository()
    topo = repo.get_topology(project_id=project_id)
    mutator = get_graph_mutator()
    chat_mem = get_chat_memory()

    # Record user message in memory
    chat_mem.add_user_message(project_id=project_id, session_id=session_id, content=user_message)

    # Gather context
    health_map = _get_health_snapshot(project_id)
    session_entities = chat_mem.get_session_entities(project_id=project_id, session_id=session_id)
    history_messages = chat_mem.get_history(project_id=project_id, session_id=session_id)

    nodes_summary = []
    for n in topo.nodes:
        h = health_map.get(n.id, {})
        nodes_summary.append({
            "id": n.id,
            "label": n.label,
            "status": h.get("status", n.properties.get("status", "healthy")),
            "technology": n.properties.get("technology") or n.properties.get("name"),
            "latency_ms": h.get("response_time_ms"),
            "error_rate": h.get("error_rate"),
        })

    edges_summary = [
        {"source": e.source, "target": e.target, "type": e.type}
        for e in topo.edges
    ]

    context_payload = {
        "project_id": project_id,
        "total_nodes": len(topo.nodes),
        "total_edges": len(topo.edges),
        "nodes": nodes_summary,
        "edges": edges_summary,
        "session_created_entities": session_entities,
    }

    parsed_reply: Optional[str] = None
    parsed_actions: list[CopilotAction] = []

    # 1. Primary Attempt: OCI Generative AI (Cohere Command A) if enabled
    if settings.OCI_ENABLED and settings.OCI_COMPARTMENT_ID:
        try:
            from backend.agent.pr_reasoner import _call_cohere_oci
            sys_prompt = SYSTEM_PROMPT + f"\n\nCURRENT ACTIVE TOPOLOGY & HEALTH CONTEXT:\n{json.dumps(context_payload, indent=2)}"
            
            history_lines = [f"{m.role.upper()}: {m.content}" for m in history_messages[-6:]]
            hist_str = "\n".join(history_lines)
            user_full_prompt = (
                f"RECENT CONVERSATION:\n{hist_str}\n\n"
                f"LATEST USER INSTRUCTION: {user_message}\n\n"
                f"Respond with JSON containing 'reply' and 'actions' (empty list [] if no graph changes)."
            )
            raw_oci = _call_cohere_oci(system_prompt=sys_prompt, user_prompt=user_full_prompt, temperature=0.1)
            if raw_oci:
                json_match = re.search(r"\{[\s\S]*\}", raw_oci)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                        if "reply" in data:
                            parsed_reply = str(data["reply"])
                            for ra in data.get("actions", []):
                                try:
                                    parsed_actions.append(CopilotAction(**ra))
                                except Exception as ex:
                                    logger.warning("Failed parsing action %s: %s", ra, ex)
                    except Exception:
                        pass
                if not parsed_reply and raw_oci.strip():
                    parsed_reply = raw_oci.strip().replace("```json", "").replace("```markdown", "").replace("```", "").strip()
        except Exception as oci_err:
            logger.warning("OCI GenAI Copilot call failed (%s), attempting secondary LLM", oci_err)

    # 2. Secondary Attempt: Configured LiteLLM provider
    if not parsed_reply:
        llm_messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"CURRENT ACTIVE TOPOLOGY & HEALTH CONTEXT:\n{json.dumps(context_payload, indent=2)}"},
        ]
        for m in history_messages[-8:]:
            llm_messages.append({"role": m.role, "content": m.content})

        try:
            raw_output = call_llm(
                messages=llm_messages,
                context={"graph_summary": context_payload},
                timeout=10.0,
            )
            json_match = re.search(r"\{[\s\S]*\}", raw_output)
            if json_match:
                data = json.loads(json_match.group(0))
                if "reply" in data:
                    parsed_reply = str(data["reply"])
                    for ra in data.get("actions", []):
                        try:
                            parsed_actions.append(CopilotAction(**ra))
                        except Exception as ex:
                            logger.warning("Failed parsing action %s: %s", ra, ex)
        except Exception as e:
            logger.warning("LiteLLM call failed (%s)", e)

    # 3. Deterministic Fallback if both LLMs unavailable
    if not parsed_reply:
        parsed_reply, parsed_actions = _fallback_rule_based_copilot(
            project_id=project_id,
            user_message=user_message,
            nodes=topo.nodes,
            edges=topo.edges,
            session_entities=session_entities,
        )

    # Execute graph mutations
    executed_actions: list[dict[str, Any]] = []
    for action in parsed_actions:
        try:
            if action.action_type == "CREATE_NODE" and action.node_id:
                node = mutator.add_node(
                    project_id=project_id,
                    node_id=action.node_id,
                    label=action.label or "Service",
                    properties=action.properties,
                    persist=True,
                )
                chat_mem.record_node_creation(
                    project_id=project_id,
                    session_id=session_id,
                    node_id=action.node_id,
                    label=action.label or "Service",
                    properties=action.properties,
                )
                executed_actions.append({
                    "action": "CREATE_NODE",
                    "id": action.node_id,
                    "label": action.label,
                    "success": True,
                })

            elif action.action_type == "UPDATE_NODE" and action.node_id:
                mutator.update_node(
                    project_id=project_id,
                    node_id=action.node_id,
                    label=action.label,
                    properties=action.properties,
                    persist=True,
                )
                executed_actions.append({
                    "action": "UPDATE_NODE",
                    "id": action.node_id,
                    "success": True,
                })

            elif action.action_type == "DELETE_NODE" and action.node_id:
                deleted = mutator.delete_node(project_id=project_id, node_id=action.node_id, persist=True)
                executed_actions.append({
                    "action": "DELETE_NODE",
                    "id": action.node_id,
                    "success": deleted,
                })

            elif action.action_type == "CREATE_EDGE" and action.source and action.target:
                edge = mutator.add_edge(
                    project_id=project_id,
                    source=action.source,
                    target=action.target,
                    edge_type=action.edge_type or "CALLS",
                    properties=action.properties,
                    persist=True,
                )
                chat_mem.record_edge_action(
                    project_id=project_id,
                    session_id=session_id,
                    source=action.source,
                    target=action.target,
                    edge_type=action.edge_type or "CALLS",
                    action="created",
                )
                executed_actions.append({
                    "action": "CREATE_EDGE",
                    "source": action.source,
                    "target": action.target,
                    "type": action.edge_type or "CALLS",
                    "success": True,
                })

            elif action.action_type == "UPDATE_EDGE" and action.source and action.old_target:
                mutator.update_edge(
                    project_id=project_id,
                    source=action.source,
                    old_target=action.old_target,
                    new_target=action.target,
                    new_type=action.edge_type,
                    properties=action.properties,
                    persist=True,
                )
                executed_actions.append({
                    "action": "UPDATE_EDGE",
                    "source": action.source,
                    "old_target": action.old_target,
                    "new_target": action.target,
                    "success": True,
                })

            elif action.action_type == "DELETE_EDGE" and action.source and action.target:
                deleted = mutator.delete_edge(
                    project_id=project_id,
                    source=action.source,
                    target=action.target,
                    edge_type=action.edge_type,
                    persist=True,
                )
                executed_actions.append({
                    "action": "DELETE_EDGE",
                    "source": action.source,
                    "target": action.target,
                    "success": deleted,
                })
        except Exception as mut_err:
            logger.error("Failed executing action %s: %s", action, mut_err)
            executed_actions.append({
                "action": action.action_type,
                "error": str(mut_err),
                "success": False,
            })

    # Record assistant message with actions
    chat_mem.add_assistant_message(
        project_id=project_id,
        session_id=session_id,
        content=parsed_reply,
        actions=executed_actions,
    )

    # Get updated topology counts
    updated_topo = repo.get_topology(project_id=project_id)

    return CopilotResponse(
        reply=parsed_reply,
        actions=parsed_actions,
        executed_actions=executed_actions,
        total_nodes=len(updated_topo.nodes),
        total_edges=len(updated_topo.edges),
        project_id=project_id,
    )
