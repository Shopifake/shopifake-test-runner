"""
Pytest configuration and fixtures for chaos tests.
"""

import os
import pytest
from kubernetes import client, config


@pytest.fixture(scope="session")
def k8s_client():
    """Provide Kubernetes API client."""
    print("\n🔧 Initializing Kubernetes client...")
    try:
        # Try in-cluster config first (when running in K8s pod)
        config.load_incluster_config()
        print("✅ Using in-cluster Kubernetes config")
    except config.ConfigException as e:
        print(f"⚠️  In-cluster config failed: {e}")
        print("🔧 Trying kubeconfig...")
        try:
            # Fallback to kubeconfig (local or CI with KUBECONFIG env var)
            config.load_kube_config()
            print("✅ Using kubeconfig")
        except config.ConfigException as e2:
            print(f"❌ Failed to load Kubernetes config: {e2}")
            print("💡 Make sure KUBECONFIG is set or pod has ServiceAccount mounted")
            pytest.exit("Cannot access Kubernetes cluster - chaos tests cannot run", returncode=1)
    
    api = client.CoreV1Api()
    
    # Test connectivity
    try:
        version = api.get_api_resources()
        print(f"✅ Connected to Kubernetes API")
    except Exception as e:
        print(f"❌ Cannot connect to Kubernetes API: {e}")
        pytest.exit("Kubernetes API unreachable - chaos tests cannot run", returncode=1)
    
    return api


@pytest.fixture(scope="session")
def k8s_custom_client():
    """Provide Kubernetes custom objects API client for CRDs."""
    print("🔧 Initializing Kubernetes CustomObjects API client...")
    try:
        config.load_incluster_config()
        print("✅ Using in-cluster config for CRDs")
    except config.ConfigException:
        try:
            config.load_kube_config()
            print("✅ Using kubeconfig for CRDs")
        except config.ConfigException as e:
            print(f"❌ Failed to load Kubernetes config for CRDs: {e}")
            pytest.exit("Cannot access Kubernetes cluster - chaos tests cannot run", returncode=1)
    
    return client.CustomObjectsApi()


@pytest.fixture(scope="session")
def namespace(k8s_client):
    """Kubernetes namespace for chaos tests."""
    ns = os.getenv("K8S_NAMESPACE", "staging")
    print(f"🔧 Using Kubernetes namespace: {ns}")
    
    # Verify namespace exists
    try:
        k8s_client.read_namespace(ns)
        print(f"✅ Namespace '{ns}' exists and is accessible")
    except Exception as e:
        print(f"❌ Cannot access namespace '{ns}': {e}")
        pytest.exit(f"Namespace '{ns}' not accessible - check RBAC permissions", returncode=1)
    
    # List pods in namespace to verify we can read them
    try:
        pods = k8s_client.list_namespaced_pod(namespace=ns, limit=5)
        pod_count = len(pods.items)
        print(f"✅ Found {pod_count} pod(s) in namespace (showing first 5)")
        if pod_count == 0:
            print("⚠️  WARNING: No pods found in namespace - chaos tests may skip")
    except Exception as e:
        print(f"❌ Cannot list pods in namespace '{ns}': {e}")
        pytest.exit(f"Cannot list pods - check RBAC permissions", returncode=1)
    
    return ns


@pytest.fixture(scope="session")
def chaos_mesh_group():
    """Chaos Mesh API group."""
    return "chaos-mesh.org"


@pytest.fixture(scope="session")
def chaos_mesh_version():
    """Chaos Mesh API version."""
    return "v1alpha1"


@pytest.fixture(scope="session")
def verify_chaos_mesh(k8s_custom_client, namespace, chaos_mesh_group, chaos_mesh_version):
    """Verify Chaos Mesh is installed and accessible."""
    print("\n🔧 Verifying Chaos Mesh installation...")
    
    # Try to list PodChaos CRDs to verify Chaos Mesh is installed
    try:
        k8s_custom_client.list_namespaced_custom_object(
            group=chaos_mesh_group,
            version=chaos_mesh_version,
            namespace=namespace,
            plural="podchaos",
            limit=1
        )
        print("✅ Chaos Mesh is installed and accessible")
        print(f"✅ Can access PodChaos CRDs in namespace '{namespace}'")
        return True
    except Exception as e:
        print(f"❌ Cannot access Chaos Mesh CRDs: {e}")
        print("💡 Chaos Mesh may not be installed or RBAC permissions are missing")
        print("💡 Install with: kubectl apply -f https://mirrors.chaos-mesh.org/latest/crd.yaml")
        pytest.exit("Chaos Mesh not accessible - chaos tests cannot run", returncode=1)

