"""
Combined load and chaos tests - the ultimate resilience test.

These tests run load (Locust) while injecting failures (Chaos Mesh).
"""

import os
import sys
import time
import random
import threading
import pytest
from pathlib import Path

from src.tests.chaos.helpers.chaos_helper import ChaosHelper


def run_locust_load(base_url: str, duration: int = 60):
    """
    Run Locust load in background.
    
    Args:
        base_url: API base URL
        duration: Load duration in seconds
    """
    from locust.main import main as locust_main
    
    repo_root = Path(__file__).resolve().parents[4]
    locustfile = repo_root / "src" / "tests" / "load" / "locustfile.py"
    
    # Prepare Locust arguments
    locust_args = [
        "--locustfile", str(locustfile),
        "--host", base_url,
        "--users", "5",
        "--spawn-rate", "1",
        "--run-time", f"{duration}s",
        "--headless",
        "--only-summary",  # Less verbose output
    ]
    
    # Save and modify sys.argv
    original_argv = sys.argv.copy()
    sys.argv = ["locust"] + locust_args
    
    try:
        locust_main()
    finally:
        sys.argv = original_argv


@pytest.mark.chaos
@pytest.mark.slow
def test_load_with_pod_failures(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    base_url,
    api_client,
    verify_chaos_mesh
):
    """
    Test system behavior under load while killing pods.
    
    This is a comprehensive resilience test:
    1. Start load testing with Locust
    2. Randomly kill pods during load
    3. Verify system remains available
    4. Check that services recover
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["catalog", "orders", "inventory", "pricing"])
    
    print(f"\n🔥💥 Ultimate test: Load + Pod failures for service: {service}")
    
    chaos_name = None
    locust_thread = None
    
    try:
        # Start Locust in background thread
        print(f"✓ Starting load test (60s)...")
        locust_thread = threading.Thread(
            target=run_locust_load,
            args=(base_url, 60),
            daemon=True
        )
        locust_thread.start()
        
        # Wait a bit for load to ramp up
        time.sleep(10)
        
        # Create chaos experiment
        print(f"✓ Injecting pod failures for {service}...")
        chaos_obj = chaos.create_pod_chaos(
            action="pod-kill",
            selector={"app": service},
            duration="30s",
            mode="one"
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Chaos experiment created: {chaos_name}")
        
        # Monitor service health during chaos
        path = f"/api/{service}/actuator/health"
        
        print(f"✓ Monitoring {service} during load + chaos...")
        
        checks = 0
        successes = 0
        
        for i in range(8):  # Monitor for 40s
            try:
                response = api_client.get(path, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        successes += 1
                        print(f"  ✓ Check {i+1}: healthy")
                    else:
                        print(f"  ✗ Check {i+1}: unhealthy - {data.get('status')}")
                else:
                    print(f"  ✗ Check {i+1}: HTTP {response.status_code}")
            except Exception as e:
                print(f"  ✗ Check {i+1}: {type(e).__name__}")
            
            checks += 1
            time.sleep(5)
        
        # Calculate success rate
        success_rate = successes / checks if checks > 0 else 0
        print(f"✓ Success rate during chaos: {success_rate:.0%} ({successes}/{checks})")
        
        # System should maintain at least 40% availability under combined stress
        # (Some failures expected during pod restart)
        assert success_rate >= 0.4, (
            f"Service {service} availability too low under load + chaos: {success_rate:.0%}"
        )
        
        # Wait for Locust to finish
        if locust_thread and locust_thread.is_alive():
            print(f"✓ Waiting for load test to complete...")
            locust_thread.join(timeout=30)
        
        # Final health check
        time.sleep(5)
        response = api_client.get(path, timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "UP"
        
        print(f"✅ System maintained {success_rate:.0%} availability under load + pod failures")
        print(f"✅ Service {service} fully recovered after chaos")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("PodChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")


@pytest.mark.chaos
@pytest.mark.slow
def test_load_with_network_latency(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    base_url,
    api_client,
    verify_chaos_mesh
):
    """
    Test system behavior under load with increased network latency.
    
    Verifies that the system degrades gracefully under network stress.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["catalog", "orders", "pricing"])
    latency = "300ms"
    
    print(f"\n🔥💥 Ultimate test: Load + Network latency ({latency}) for service: {service}")
    
    chaos_name = None
    locust_thread = None
    
    try:
        # Start Locust
        print(f"✓ Starting load test (60s)...")
        locust_thread = threading.Thread(
            target=run_locust_load,
            args=(base_url, 60),
            daemon=True
        )
        locust_thread.start()
        
        time.sleep(10)
        
        # Inject network latency
        print(f"✓ Injecting {latency} network latency to {service}...")
        chaos_obj = chaos.create_network_chaos(
            action="delay",
            selector={"app": service},
            duration="40s",
            mode="all",
            delay={
                "latency": latency,
                "correlation": "0",
                "jitter": "50ms"
            },
            direction="to"
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Chaos experiment created: {chaos_name}")
        
        # Monitor during latency
        path = f"/api/{service}/actuator/health"
        
        print(f"✓ Monitoring {service} during load + latency...")
        
        checks = 0
        successes = 0
        
        for i in range(6):  # 30s monitoring
            try:
                start = time.time()
                response = api_client.get(path, timeout=15)
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        successes += 1
                        print(f"  ✓ Check {i+1}: healthy ({elapsed:.2f}s)")
                    else:
                        print(f"  ✗ Check {i+1}: unhealthy")
                else:
                    print(f"  ✗ Check {i+1}: HTTP {response.status_code}")
            except Exception as e:
                print(f"  ✗ Check {i+1}: timeout or error")
            
            checks += 1
            time.sleep(5)
        
        success_rate = successes / checks if checks > 0 else 0
        print(f"✓ Success rate during latency: {success_rate:.0%} ({successes}/{checks})")
        
        # Should maintain at least 60% availability (slower but functional)
        assert success_rate >= 0.6, (
            f"Service {service} availability too low under load + latency: {success_rate:.0%}"
        )
        
        # Wait for load test
        if locust_thread and locust_thread.is_alive():
            locust_thread.join(timeout=30)
        
        print(f"✅ System maintained {success_rate:.0%} availability under load + network latency")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("NetworkChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")

