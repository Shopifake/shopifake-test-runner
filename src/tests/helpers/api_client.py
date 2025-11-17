"""
API Client wrapper for making HTTP requests with retry logic, timeout, and error handling.
"""

import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class APIClient:
    """HTTP client with retry logic and consistent error handling."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 60,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API (e.g., http://localhost:8080)
            timeout: Default timeout in seconds for requests
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Backoff factor for retry delays
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Configure session with retry strategy
        self.session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}/{path}"

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Perform GET request.

        Args:
            path: API path (e.g., /api/catalog/products)
            params: Query parameters
            headers: Request headers
            timeout: Override default timeout

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        url = self._build_url(path)
        timeout = timeout or self.timeout

        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Perform POST request.

        Args:
            path: API path
            json: JSON payload
            data: Form data payload
            headers: Request headers
            timeout: Override default timeout

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        url = self._build_url(path)
        timeout = timeout or self.timeout

        response = self.session.post(
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Perform PUT request.

        Args:
            path: API path
            json: JSON payload
            data: Form data payload
            headers: Request headers
            timeout: Override default timeout

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        url = self._build_url(path)
        timeout = timeout or self.timeout

        response = self.session.put(
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Perform DELETE request.

        Args:
            path: API path
            headers: Request headers
            timeout: Override default timeout

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        url = self._build_url(path)
        timeout = timeout or self.timeout

        response = self.session.delete(
            url,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def health_check(self, path: str = "/actuator/health") -> Dict[str, Any]:
        """
        Perform health check.

        Args:
            path: Health check path

        Returns:
            Health check response as dict

        Raises:
            requests.RequestException: If health check fails
        """
        response = self.get(path, timeout=10)
        return response.json() if response.text else {}

