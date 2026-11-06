"""Kubernetes Client for AEGIS Actuator."""

from __future__ import annotations
import logging
from typing import Any

from kubernetes import client, config

logger = logging.getLogger(__name__)

class K8sClient:
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except config.ConfigException:
                logger.warning("Could not configure kubernetes python client. Using mock.")
                self.core_v1 = None
                self.apps_v1 = None
                return

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def restart_deployment(self, namespace: str, deployment_name: str) -> dict[str, Any]:
        """Restart a deployment by patching its annotations."""
        if not self.apps_v1:
            return {"status": "skipped", "reason": "No k8s client"}

        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now
                        }
                    }
                }
            }
        }
        try:
            self.apps_v1.patch_namespaced_deployment(deployment_name, namespace, body)
            return {"status": "applied", "action": "restart", "target": deployment_name}
        except Exception as e:
            logger.error("Failed to restart deployment %s in %s: %s", deployment_name, namespace, e)
            return {"status": "failed", "error": str(e)}

    def scale_deployment(self, namespace: str, deployment_name: str, replicas: int) -> dict[str, Any]:
        """Scale a deployment."""
        if not self.apps_v1:
            return {"status": "skipped", "reason": "No k8s client"}

        body = {"spec": {"replicas": replicas}}
        try:
            self.apps_v1.patch_namespaced_deployment(deployment_name, namespace, body)
            return {"status": "applied", "action": "scale", "target": deployment_name, "replicas": replicas}
        except Exception as e:
            logger.error("Failed to scale deployment %s in %s to %d: %s", deployment_name, namespace, replicas, e)
            return {"status": "failed", "error": str(e)}

k8s_client = K8sClient()
