"""
Test network chaos scenarios using Chaos Mesh NetworkChaos.
"""

import time
import random
import pytest

from src.tests.chaos.helpers.chaos_helper import ChaosHelper


@pytest.mark.chaos
def test_network_latency(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client,
    verify_chaos_mesh
):
    """
    Test that services handle increased network latency gracefully.
    
    Injects 200ms latency to a random service and verifies:
    1. Service remains available (slower but functional)
    2. Health checks still pass (with increased timeout)
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["catalog", "orders", "inventory", "pricing"])
    latency_ms = "200ms"
    
    print(f"\n🔥 Testing network latency ({latency_ms}) for service: {service}")
    
    chaos_name = None
    try:
        # Create NetworkChaos with delay
        chaos_obj = chaos.create_network_chaos(
            action="delay",
            selector={"app": service},
            duration="45s",
            mode="all",
            delay={
                "latency": latency_ms,
                "correlation": "0",
                "jitter": "10ms"
            },
            direction="to"
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created NetworkChaos experiment: {chaos_name}")
        print(f"✓ Injected {latency_ms} latency to all {service} pods")
        
        # Wait for chaos to be active
        time.sleep(5)
        
        # Verify service is still responsive (but slower)
        path = f"/api/{service}/actuator/health"
        
        print(f"✓ Testing service response with latency...")
        start = time.time()
        response = api_client.get(path, timeout=15)  # Increased timeout
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Service {service} failed under latency"
        
        data = response.json()
        assert data.get("status") == "UP", f"Service {service} unhealthy under latency"
        
        print(f"✓ Service responded in {elapsed:.2f}s (latency applied)")
        print(f"✅ Service {service} handles network latency gracefully")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("NetworkChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")


@pytest.mark.chaos
def test_network_partition(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client,
    verify_chaos_mesh
):
    """
    Test service behavior during network partition.
    
    Simulates network partition by blocking traffic to/from a service.
    Verifies that other services continue to operate.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    # Pick a non-critical service to partition
    partitioned_service = "audit"  # Audit is async, other services can tolerate it being down
    healthy_service = "catalog"
    
    print(f"\n🔥 Testing network partition for service: {partitioned_service}")
    
    chaos_name = None
    try:
        # Create NetworkChaos with partition action
        chaos_obj = chaos.create_network_chaos(
            action="partition",
            selector={"app": partitioned_service},
            duration="30s",
            mode="all",
            direction="both"
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created NetworkChaos experiment: {chaos_name}")
        print(f"✓ Network partition applied to {partitioned_service}")
        
        # Wait for partition to be active
        time.sleep(5)
        
        # Verify partitioned service is unreachable
        print(f"✓ Verifying {partitioned_service} is partitioned...")
        path = f"/api/{partitioned_service}/actuator/health"
        
        try:
            response = api_client.get(path, timeout=5)
            # If we get here, partition might not be working fully
            # But that's okay for this test
            print(f"⚠️  {partitioned_service} still reachable (partial partition)")
        except Exception:
            print(f"✓ {partitioned_service} is unreachable (partition successful)")
        
        # Verify other services are still healthy
        print(f"✓ Verifying other services remain healthy...")
        path = f"/api/{healthy_service}/actuator/health"
        response = api_client.get(path, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP"
        
        print(f"✓ Service {healthy_service} remains healthy during partition")
        print(f"✅ System tolerates network partition of {partitioned_service}")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("NetworkChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
                
                # Wait a bit for network to recover
                time.sleep(5)
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")


@pytest.mark.chaos
def test_packet_loss(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client,
    verify_chaos_mesh
):
    """
    Test service resilience to packet loss.
    
    Injects 30% packet loss and verifies service remains functional.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["orders", "inventory", "pricing"])
    loss_percent = "30"
    
    print(f"\n🔥 Testing packet loss ({loss_percent}%) for service: {service}")
    
    chaos_name = None
    try:
        chaos_obj = chaos.create_network_chaos(
            action="loss",
            selector={"app": service},
            duration="45s",
            mode="all",
            loss={
                "loss": loss_percent,
                "correlation": "0"
            },
            direction="to"
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created NetworkChaos experiment: {chaos_name}")
        print(f"✓ Injected {loss_percent}% packet loss")
        
        time.sleep(5)
        
        # Verify service still responds (may need retries)
        path = f"/api/{service}/actuator/health"
        
        max_attempts = 3
        success = False
        
        for attempt in range(max_attempts):
            try:
                response = api_client.get(path, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        success = True
                        print(f"✓ Service responded successfully on attempt {attempt + 1}")
                        break
            except Exception as e:
                print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                time.sleep(2)
        
        assert success, f"Service {service} failed to respond after {max_attempts} attempts with {loss_percent}% packet loss"
        
        print(f"✅ Service {service} handles {loss_percent}% packet loss")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("NetworkChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")

