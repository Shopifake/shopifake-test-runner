"""
Helper class for interacting with Chaos Mesh CRDs.
"""

import time
import uuid
from typing import Dict, List, Optional

from kubernetes import client


class ChaosHelper:
    """Wrapper for Chaos Mesh operations."""
    
    def __init__(
        self,
        custom_client: client.CustomObjectsApi,
        namespace: str,
        group: str = "chaos-mesh.org",
        version: str = "v1alpha1"
    ):
        """
        Initialize Chaos Helper.
        
        Args:
            custom_client: Kubernetes CustomObjectsApi client
            namespace: Kubernetes namespace
            group: Chaos Mesh API group
            version: Chaos Mesh API version
        """
        self.client = custom_client
        self.namespace = namespace
        self.group = group
        self.version = version
    
    def _generate_name(self, prefix: str) -> str:
        """Generate unique chaos experiment name."""
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}-{unique_id}"
    
    def create_pod_chaos(
        self,
        action: str,
        selector: Dict[str, any],
        duration: str = "30s",
        mode: str = "one",
        name: Optional[str] = None
    ) -> Dict:
        """
        Create PodChaos experiment.
        
        Args:
            action: Chaos action (pod-kill, pod-failure, container-kill)
            selector: Pod selector (labelSelectors dict)
            duration: Experiment duration (e.g., "30s", "2m")
            mode: Selection mode (one, all, fixed, fixed-percent, random-max-percent)
            name: Optional experiment name
        
        Returns:
            Created chaos object
        """
        name = name or self._generate_name("podchaos")
        
        body = {
            "apiVersion": f"{self.group}/{self.version}",
            "kind": "PodChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "action": action,
                "mode": mode,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": selector
                },
                "duration": duration
            }
        }
        
        return self.client.create_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural="podchaos",
            body=body
        )
    
    def create_network_chaos(
        self,
        action: str,
        selector: Dict[str, any],
        duration: str = "30s",
        mode: str = "all",
        delay: Optional[Dict] = None,
        loss: Optional[Dict] = None,
        direction: str = "to",
        name: Optional[str] = None
    ) -> Dict:
        """
        Create NetworkChaos experiment.
        
        Args:
            action: Chaos action (delay, loss, duplicate, corrupt, partition, bandwidth)
            selector: Pod selector
            duration: Experiment duration
            mode: Selection mode
            delay: Delay config (e.g., {"latency": "200ms", "correlation": "50", "jitter": "10ms"})
            loss: Loss config (e.g., {"loss": "30", "correlation": "50"})
            direction: Traffic direction (to, from, both)
            name: Optional experiment name
        
        Returns:
            Created chaos object
        """
        name = name or self._generate_name("networkchaos")
        
        spec = {
            "action": action,
            "mode": mode,
            "selector": {
                "namespaces": [self.namespace],
                "labelSelectors": selector
            },
            "duration": duration,
            "direction": direction
        }
        
        if delay:
            spec["delay"] = delay
        if loss:
            spec["loss"] = loss
        
        body = {
            "apiVersion": f"{self.group}/{self.version}",
            "kind": "NetworkChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": spec
        }
        
        return self.client.create_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural="networkchaos",
            body=body
        )
    
    def create_stress_chaos(
        self,
        selector: Dict[str, any],
        duration: str = "30s",
        mode: str = "one",
        stressors: Optional[Dict] = None,
        name: Optional[str] = None
    ) -> Dict:
        """
        Create StressChaos experiment.
        
        Args:
            selector: Pod selector
            duration: Experiment duration
            mode: Selection mode
            stressors: Stress config (e.g., {"cpu": {"workers": 2, "load": 80}, "memory": {"workers": 1, "size": "256MB"}})
            name: Optional experiment name
        
        Returns:
            Created chaos object
        """
        name = name or self._generate_name("stresschaos")
        
        body = {
            "apiVersion": f"{self.group}/{self.version}",
            "kind": "StressChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "mode": mode,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": selector
                },
                "duration": duration,
                "stressors": stressors or {}
            }
        }
        
        return self.client.create_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural="stresschaos",
            body=body
        )
    
    def delete_chaos(self, kind: str, name: str) -> None:
        """
        Delete chaos experiment.
        
        Args:
            kind: Chaos kind (PodChaos, NetworkChaos, StressChaos)
            name: Experiment name
        """
        plural = kind.lower() + "es" if kind.endswith("s") else kind.lower() + "s"
        
        self.client.delete_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=plural,
            name=name
        )
    
    def get_chaos_status(self, kind: str, name: str) -> Dict:
        """
        Get chaos experiment status.
        
        Args:
            kind: Chaos kind
            name: Experiment name
        
        Returns:
            Chaos object with status
        """
        plural = kind.lower() + "es" if kind.endswith("s") else kind.lower() + "s"
        
        return self.client.get_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=plural,
            name=name
        )
    
    def wait_for_chaos_completion(
        self,
        kind: str,
        name: str,
        timeout: int = 120
    ) -> bool:
        """
        Wait for chaos experiment to complete.
        
        Args:
            kind: Chaos kind
            name: Experiment name
            timeout: Max wait time in seconds
        
        Returns:
            True if completed successfully, False otherwise
        """
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                chaos = self.get_chaos_status(kind, name)
                status = chaos.get("status", {})
                
                # Check if experiment is finished
                conditions = status.get("conditions", [])
                for condition in conditions:
                    if condition.get("type") == "AllInjected":
                        if condition.get("status") == "True":
                            return True
                
                time.sleep(2)
            except Exception as e:
                print(f"Error checking chaos status: {e}")
                return False
        
        return False

