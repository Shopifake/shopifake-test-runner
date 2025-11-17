"""
Configuration management for test runner.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field


class TestConfig(BaseModel):
    """Test configuration based on execution mode."""

    mode: Literal["pr", "staging"]
    base_url: str
    timeout: int = Field(default=60, description="Default timeout in seconds")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    
    # GitHub integration
    github_token: str | None = Field(default=None, description="GitHub token for API access")
    github_repo: str = Field(default="Shopifake/shopifake-back", description="GitHub repository")
    
    # Post-test actions
    create_pr: bool = Field(default=False, description="Create promotion PR on success")
    send_email: bool = Field(default=False, description="Send email notification on failure")
    
    # Services to test
    services: list[str] = Field(
        default_factory=lambda: [
            "access",
            "audit",
            "catalog",
            "customers",
            "inventory",
            "orders",
            "pricing",
            "sales-dashboard",
            "sites",
            "chatbot",
            "recommender",
            "auth-b2c",
            "auth-b2e",
        ]
    )

    @classmethod
    def from_mode(cls, mode: str) -> "TestConfig":
        """Create configuration based on execution mode."""
        if mode == "pr":
            return cls(
                mode="pr",
                base_url=os.getenv("BASE_URL", "http://localhost:8080"),
                timeout=int(os.getenv("TIMEOUT", "60")),
                create_pr=False,
                send_email=False,
            )
        elif mode == "staging":
            return cls(
                mode="staging",
                base_url=os.getenv("BASE_URL", "https://staging-api.shopifake.com"),
                timeout=int(os.getenv("TIMEOUT", "300")),
                github_token=os.getenv("GITHUB_TOKEN"),
                create_pr=True,
                send_email=True,
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
