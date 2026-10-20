# Ingestion-lite reference (M3, Weeks 4 & 9) — IN SCOPE for Phase 1

Goal: prove the graph can be built from real files. Parse **Online Boutique** Kubernetes manifests (in the `aegis-testbed` fork) into `CALLS` edges and measure precision/recall. This must **not** disturb the 54-node demo graph.

## Rules
- Write edges with `source='static'`, `confidence=0.6`, and tag `graph='boutique'` (separate namespace).
- Edges are caller → callee (the Deployment whose env var points at another service is the **caller**).
- Idempotent writes (`MERGE`).

## Sketch (adapt and test; verify against the real manifests)
```python
import re, yaml

def edges_from_k8s_manifest(path, known_services):
    edges = set()
    for doc in yaml.safe_load_all(open(path)):
        if not doc or doc.get("kind") != "Deployment":
            continue
        caller = doc["metadata"]["name"]
        for c in doc["spec"]["template"]["spec"].get("containers", []):
            for env in c.get("env", []):
                value = str(env.get("value", ""))        # "svc:3550" or "svc.ns.svc.cluster.local"
                host = re.split(r"[:/]", value)[0].split(".")[0]
                if host in known_services and host != caller:
                    edges.add((caller, host))
    return edges   # e.g. {("checkoutservice", "productcatalogservice")}
```
`known_services` comes from the Kubernetes `Service` objects in the same manifests (Online Boutique env vars look like `PRODUCT_CATALOG_SERVICE_ADDR`).

## Ground truth + metrics
1. Hand-write the ground-truth edge list for Online Boutique (a few dozen lines) from its docs/manifests (`data/boutique_ground_truth.yaml`).
2. Script prints **precision** (extracted edges that are real) and **recall** (real edges found). Any honest number is acceptable.
3. Optional stretch (Week 9): show the Boutique graph as a second canvas view.

## Outside Phase 1
Library manifests, API specs, traces, Kubernetes live scanning and confidence merging belong to Phase 2 (`docs/phase2-parked/`).
