"""
Test resource stress scenarios using Chaos Mesh StressChaos.
"""

import time
import random
import pytest

from src.tests.chaos.helpers.chaos_helper import ChaosHelper


@pytest.mark.chaos
def test_cpu_stress(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client
):
    """
    Test service resilience under CPU stress.
    
    Applies CPU stress to a service and verifies it remains responsive.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["catalog", "orders", "pricing", "inventory"])
    
    print(f"\n🔥 Testing CPU stress for service: {service}")
    
    chaos_name = None
    try:
        # Create StressChaos with CPU stress
        chaos_obj = chaos.create_stress_chaos(
            selector={"app": service},
            duration="45s",
            mode="one",  # Stress one pod
            stressors={
                "cpu": {
                    "workers": 2,
                    "load": 80  # 80% CPU load
                }
            }
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created StressChaos experiment: {chaos_name}")
        print(f"✓ Applying CPU stress (2 workers, 80% load)")
        
        # Wait for stress to be active
        time.sleep(5)
        
        # Verify service remains responsive
        path = f"/api/{service}/actuator/health"
        
        print(f"✓ Testing service response under CPU stress...")
        
        # Try multiple times to account for slower responses
        max_attempts = 3
        success = False
        
        for attempt in range(max_attempts):
            try:
                start = time.time()
                response = api_client.get(path, timeout=15)
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        success = True
                        print(f"✓ Service responded in {elapsed:.2f}s (attempt {attempt + 1})")
                        break
            except Exception as e:
                print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        
        assert success, f"Service {service} failed to respond under CPU stress"
        
        print(f"✅ Service {service} remains responsive under CPU stress")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("StressChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")


@pytest.mark.chaos
def test_memory_stress(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client
):
    """
    Test service resilience under memory stress.
    
    Applies memory stress to a service and verifies it doesn't crash.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["catalog", "orders", "customers"])
    
    print(f"\n🔥 Testing memory stress for service: {service}")
    
    chaos_name = None
    try:
        # Create StressChaos with memory stress
        chaos_obj = chaos.create_stress_chaos(
            selector={"app": service},
            duration="45s",
            mode="one",
            stressors={
                "memory": {
                    "workers": 1,
                    "size": "256MB"  # Allocate 256MB
                }
            }
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created StressChaos experiment: {chaos_name}")
        print(f"✓ Applying memory stress (256MB allocation)")
        
        time.sleep(5)
        
        # Verify service remains responsive
        path = f"/api/{service}/actuator/health"
        
        print(f"✓ Testing service response under memory stress...")
        
        max_attempts = 3
        success = False
        
        for attempt in range(max_attempts):
            try:
                response = api_client.get(path, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        success = True
                        print(f"✓ Service healthy (attempt {attempt + 1})")
                        break
            except Exception as e:
                print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        
        assert success, f"Service {service} failed under memory stress"
        
        print(f"✅ Service {service} remains stable under memory stress")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("StressChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")


@pytest.mark.chaos
def test_combined_cpu_memory_stress(
    k8s_custom_client,
    namespace,
    chaos_mesh_group,
    chaos_mesh_version,
    api_client
):
    """
    Test service under combined CPU and memory stress.
    
    This simulates a more realistic high-load scenario.
    """
    chaos = ChaosHelper(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version)
    
    service = random.choice(["orders", "pricing", "inventory"])
    
    print(f"\n🔥 Testing combined CPU+Memory stress for service: {service}")
    
    chaos_name = None
    try:
        # Create StressChaos with both CPU and memory stress
        chaos_obj = chaos.create_stress_chaos(
            selector={"app": service},
            duration="60s",
            mode="one",
            stressors={
                "cpu": {
                    "workers": 1,
                    "load": 50
                },
                "memory": {
                    "workers": 1,
                    "size": "128MB"
                }
            }
        )
        chaos_name = chaos_obj["metadata"]["name"]
        
        print(f"✓ Created StressChaos experiment: {chaos_name}")
        print(f"✓ Applying combined stress (CPU: 50%, Memory: 128MB)")
        
        time.sleep(8)
        
        # Monitor service health over time
        path = f"/api/{service}/actuator/health"
        
        print(f"✓ Monitoring service health over 30s...")
        
        checks = 0
        successes = 0
        max_checks = 6
        
        for i in range(max_checks):
            try:
                response = api_client.get(path, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        successes += 1
                        print(f"  ✓ Check {i+1}/{max_checks}: healthy")
                    else:
                        print(f"  ✗ Check {i+1}/{max_checks}: unhealthy")
                else:
                    print(f"  ✗ Check {i+1}/{max_checks}: status {response.status_code}")
            except Exception as e:
                print(f"  ✗ Check {i+1}/{max_checks}: {e}")
            
            checks += 1
            time.sleep(5)
        
        # Service should be healthy at least 50% of the time
        success_rate = successes / checks if checks > 0 else 0
        print(f"✓ Success rate: {success_rate:.0%} ({successes}/{checks})")
        
        assert success_rate >= 0.5, f"Service {service} success rate too low under stress: {success_rate:.0%}"
        
        print(f"✅ Service {service} maintains {success_rate:.0%} availability under combined stress")
        
    finally:
        if chaos_name:
            try:
                chaos.delete_chaos("StressChaos", chaos_name)
                print(f"✓ Cleaned up chaos experiment: {chaos_name}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup: {e}")

