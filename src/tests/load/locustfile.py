"""
Locust configuration and test scenarios for load testing.

To add a new scenario:
1. Create a new file in src/tests/load/scenarios/your_scenario.py
2. Implement a class with a run() method that takes self.client
3. Import and add it as a task below
"""

import os
from locust import HttpUser, task, between

from src.tests.load.scenarios.health import HealthCheckScenario


class ShopifakeUser(HttpUser):
    """Main Locust user class that combines all scenarios.
    
    To add a new scenario, create it in scenarios/ and add a task method here.
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        # Base URL is automatically set by Locust from --host parameter
        pass
    
    @task(1)
    def health_checks(self):
        """Health checks scenario (weight: 1).
        
        Simple load test on health endpoints.
        """
        scenario = HealthCheckScenario(self.client)
        scenario.run()
    
    # To add more scenarios:
    # @task(2)
    # def your_new_scenario(self):
    #     """Your new scenario description."""
    #     scenario = YourNewScenario(self.client)
    #     scenario.run()


# Locust configuration via environment variables
host = os.getenv("LOCUST_HOST", "http://localhost:8080")
users = int(os.getenv("LOCUST_USERS", "10"))
spawn_rate = int(os.getenv("LOCUST_SPAWN_RATE", "2"))
run_time = os.getenv("LOCUST_RUN_TIME", "60s")

