"""
Health checks scenario - simple load test on health endpoints.
"""

import random


class HealthCheckScenario:
    """Simple scenario that performs health checks on services."""
    
    # List of health check endpoints
    HEALTH_ENDPOINTS = [
        "/actuator/health",  # Gateway
        "/api/access/actuator/health",
        "/api/audit/actuator/health",
        "/api/catalog/actuator/health",
        "/api/customers/actuator/health",
        "/api/inventory/actuator/health",
        "/api/orders/actuator/health",
        "/api/pricing/actuator/health",
        "/api/sales-dashboard/actuator/health",
        "/api/sites/actuator/health",
        "/api/chatbot/health",
        "/api/recommender/health",
        "/api/auth-b2c/healthz",
        "/api/auth-b2e/healthz",
    ]
    
    def __init__(self, client):
        """Initialize scenario with HTTP client.
        
        Args:
            client: Locust HttpUser client for making requests
        """
        self.client = client
    
    def run(self):
        """Execute health check scenario."""
        # Randomly select a health endpoint to check
        endpoint = random.choice(self.HEALTH_ENDPOINTS)
        self.check_health(endpoint)
    
    def check_health(self, endpoint: str):
        """Check health of a specific endpoint.
        
        Args:
            endpoint: Health check endpoint path
        """
        with self.client.get(
            endpoint,
            catch_response=True,
            name=f"health {endpoint}",
        ) as response:
            if response.status_code == 200:
                # Try to parse JSON response if available
                try:
                    data = response.json()
                    # Check if status is UP or healthy (Python services use "healthy")
                    if isinstance(data, dict) and "status" in data:
                        if data["status"] in ["UP", "healthy"]:
                            response.success()
                        else:
                            response.failure(f"Status not UP/healthy: {data.get('status')}")
                    else:
                        response.success()
                except Exception:
                    # If not JSON or parsing fails, still consider 200 as success
                    response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

