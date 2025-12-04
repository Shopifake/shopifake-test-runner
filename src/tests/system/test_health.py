"""
Health check tests for all Shopifake microservices.
Tests services through the API Gateway.
"""

import pytest


# Spring Boot services (use /actuator/health)
SPRING_BOOT_SERVICES = [
    "access",
    "audit",
    "catalog",
    "customers",
    "inventory",
    "orders",
    "pricing",
    "sales-dashboard",
    "sites",
]

# Python/FastAPI services (use /health)
PYTHON_SERVICES = [
    "recommender",
]

# Auth services (use /healthz)
AUTH_SERVICES = [
    "auth-b2c",
    "auth-b2e",
]


def test_gateway_health(api_client):
    """Test that the API Gateway is healthy."""
    data = api_client.health_check("/actuator/health")
    assert data.get("status") == "UP", f"Gateway status is not UP: {data}"


@pytest.mark.parametrize("service", SPRING_BOOT_SERVICES)
def test_spring_boot_service_health(api_client, service):
    """Test health of Spring Boot microservices through gateway."""
    path = f"/api/{service}/actuator/health"
    data = api_client.health_check(path)
    
    assert data.get("status") == "UP", (
        f"{service} is not healthy\n"
        f"Status: {data.get('status')}\n"
        f"Details: {data}"
    )


@pytest.mark.parametrize("service", PYTHON_SERVICES)
def test_python_service_health(api_client, service):
    """Test health of Python/FastAPI microservices through gateway."""
    path = f"/api/{service}/health"
    response = api_client.get(path, timeout=10)
    
    assert response.status_code == 200, (
        f"{service} health check failed\n"
        f"URL: {api_client.base_url}{path}\n"
        f"Status: {response.status_code}\n"
        f"Response: {response.text}"
    )


@pytest.mark.parametrize("service", AUTH_SERVICES)
def test_auth_service_health(api_client, service):
    """Test health of authentication services through gateway.
    
    Auth services return status: 'UP' (same as Spring Boot services).
    """
    path = f"/api/{service}/healthz"
    data = api_client.health_check(path)
    
    assert data.get("status") == "UP", (
        f"{service} is not healthy\n"
        f"Status: {data.get('status')}\n"
        f"Details: {data}"
    )

