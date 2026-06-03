import logging

import requests

logger = logging.getLogger(__name__)


class RestClient:
    """
    StandardRestClient Class
    ----------------

    The `StandardRestClient` class is used to interact with REST APIs by sending HTTP requests.

    Methods:
        - __init__(base_url="")
        - base_url (property)
        - base_url (setter)
        - send_api_request(method: str, endpoint: str) -> dict

    Private Methods:
        - _send_request(method, endpoint, data=None, headers=None)
        - _construct_full_url(endpoint)

    Attributes:
        - _base_url (str): The base URL used for constructing full URLs for API requests.

    Initialization:
        The `StandardRestClient` class can be initialized with an optional `base_url` parameter that sets the base URL for all API
        requests. If no `base_url` is provided, the default value is an empty string.

    Examples:
        >>> client = StandardRestClient()
        >>> client.base_url
        ''
        >>> client.base_url = "https://api.example.com"
        >>> client.base_url
        'https://api.example.com'
        >>> response = client.send_api_request("GET", "users")
        >>> response
        {
            "users": [
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"}
            ]
        }
    """
    def __init__(self, base_url=""):
        self._base_url = base_url

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, value):
        self._base_url = value

    def send_api_request(self, method: str, endpoint: str,data=None, headers=None) -> dict:
        response = self._send_request(method, endpoint,data,headers)
        if response is not None:
            data=data or response
            headers=headers or {}
            return response.json()

    def _send_request(self, method, endpoint, data=None, headers=None):
        url = self._construct_full_url(endpoint)
        try:
            response = getattr(requests, method.lower())(url, json=data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending {method} request to {url}: {e}")
            return None
        return response

    def _construct_full_url(self, endpoint):
        return f"{self.base_url}/{endpoint}"
