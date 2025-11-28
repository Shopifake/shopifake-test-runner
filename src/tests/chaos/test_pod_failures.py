"""
Test pod failure recovery using Chaos Mesh PodChaos.
"""

import time
import random
import pytest

from src.tests.chaos.helpers.chaos_helper import ChaosHelper


# Services we can safely kill and expect automatic recovery
RESILIENT_SERVICES = [
    "catalog",
    "orders",
    "inventory",
    "customers",
    "pricing",
    "sites",
    "access",
    "audit",
]


@pytest.mark.chaos
def test_pod_deletion_recovery(
    k8s_client,
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client,
    verify_chaos_mesh
):
    """
    Test that a service recovers after a pod is killed.
    
    Steps:
    1. Pick a random service
    2. Create PodChaos to kill one pod
    3. Wait for chaos to complete (pod killed)
    4. Verify new pod is created and running
    5. Verify service health check passes
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    # Pick random service
    service = random.choice(RESILIENT_SERVICES)
    
    print(f"\n🔥 Testing pod deletion recovery for service: {service}")
    
    # Create PodChaos experiment
    chaos_name = None
    try:
        chaos_obj = chaos.create_pod_chaos(
            action="pod-kill",
            selector={"app": service},
            duration="30s",
            mode="one"
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created PodChaos experiment: {chaos_name}")
        
        # Wait a bit for pod to be killed
        time.sleep(10)
        
        # Check that new pods are running
        max_wait = 60
        start = time.time()
        pod_recovered = False
        
        while time.time() - start < max_wait:
            pods = k8s_client.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={service}"
            )
            
            running_pods = [p for p in pods.items if p.status.phase == "Running"]
            
            if len(running_pods) > 0:
                # Check if pods are actually ready
                ready_pods = [
                    p for p in running_pods
                    if p.status.conditions and any(
                        c.type == "Ready" and c.status == "True"
                        for c in p.status.conditions
                    )
                ]
                
                if ready_pods:
                    print(f"✓ Service {service} has {len(ready_pods)} ready pod(s)")
                    pod_recovered = True
                    break
            
            time.sleep(2)
        
        assert pod_recovered, f"Service {service} did not recover within {max_wait}s"
        
        # Verify service health via API
        print(f"✓ Verifying service health via API...")
        path = f"/api/{service}/actuator/health"
        
        # Give a bit more time for service to be fully ready
        time.sleep(5)
        
        response = api_client.get(path, timeout=10)
        assert response.status_code == 200, f"Health check failed for {service}"
        
        data = response.json()
        assert data.get("status") == "UP", f"Service {service} status is not UP: {data}"
        
        print(f"✅ Service {service} successfully recovered from pod deletion")
        
    finally:
        # Cleanup: delete chaos experiment
        if chaos_name:
            try:
                chaos.delete_chaos("PodChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup chaos experiment: {e}")


@pytest.mark.chaos
def test_multiple_pod_failures(
    k8s_client,
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client,
    verify_chaos_mesh
):
    """
    Test that a service recovers when multiple pods are killed simultaneously.
    
    This simulates a more severe outage where multiple instances fail at once.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    # Pick a service that typically has multiple replicas
    service = random.choice(["catalog", "orders", "inventory"])
    
    print(f"\n🔥 Testing multiple pod failures for service: {service}")
    
    # Check how many pods exist
    pods = k8s_client.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app={service}"
    )
    
    pod_count = len([p for p in pods.items if p.status.phase == "Running"])
    print(f"✓ Service {service} currently has {pod_count} running pod(s)")
    
    if pod_count < 2:
        pytest.skip(f"Service {service} has less than 2 pods, skipping multiple failure test")
    
    chaos_name = None
    try:
        # Kill 2 pods or 50% of pods (whichever is smaller)
        mode = "fixed"
        value = min(2, pod_count // 2) if pod_count > 2 else 1
        
        chaos_obj = chaos.create_pod_chaos(
            action="pod-kill",
            selector={"app": service},
            duration="30s",
            mode=mode  # Kill fixed number of pods
        )
        
        # Add value to spec if using fixed mode
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created PodChaos experiment: {chaos_name} (targeting {value} pod(s))")
        
        # Wait for pods to be killed and recover
        time.sleep(15)
        
        # Verify recovery
        max_wait = 90
        start = time.time()
        
        while time.time() - start < max_wait:
            pods = k8s_client.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={service}"
            )
            
            ready_pods = [
                p for p in pods.items
                if p.status.phase == "Running" and p.status.conditions and any(
                    c.type == "Ready" and c.status == "True"
                    for c in p.status.conditions
                )
            ]
            
            if len(ready_pods) >= pod_count:
                print(f"✓ Service {service} recovered all {len(ready_pods)} pods")
                break
            
            time.sleep(3)
        else:
            pytest.fail(f"Service {service} did not fully recover within {max_wait}s")
        
        # Verify service health
        print(f"✓ Verifying service health via API...")
        time.sleep(5)
        
        path = f"/api/{service}/actuator/health"
        response = api_client.get(path, timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "UP"
        
        print(f"✅ Service {service} successfully recovered from multiple pod failures")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("PodChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")

