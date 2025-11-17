"""
Pytest configuration and fixtures for chaos tests.
"""

import os
import pytest
from kubernetes import client, config


@pytest.fixture(scope="session")
def k8s_client():
    """Provide Kubernetes API client."""
    try:
        # Try in-cluster config first (when running in K8s pod)
        config.load_incluster_config()
    except config.ConfigException:
        # Fallback to kubeconfig (local or CI with KUBECONFIG env var)
        config.load_kube_config()
    
    return client.CoreV1Api()


@pytest.fixture(scope="session")
def k8s_custom_client():
    """Provide Kubernetes custom objects API client for CRDs."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    
    return client.CustomObjectsApi()


@pytest.fixture(scope="session")
def namespace():
    """Kubernetes namespace for chaos tests."""
    return os.getenv("K8S_NAMESPACE", "staging")


@pytest.fixture(scope="session")
def chaos_mesh_group():
    """Chaos Mesh API group."""
    return "chaos-mesh.org"


@pytest.fixture(scope="session")
def chaos_mesh_version():
    """Chaos Mesh API version."""
    return "v1alpha1"

