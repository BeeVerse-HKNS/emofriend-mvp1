"""ConnectorHub — n8n-style External Connector Hub.

Provides a registry for external service connectors following the
BaseConnector interface pattern, similar to n8n's node system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Abstract base class for all external service connectors.

    All connectors must implement connect, execute, and disconnect methods,
    plus expose their name and capabilities as properties.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external service.

        Returns:
            True if connection was successful.
        """
        ...

    @abstractmethod
    async def execute(self, action: str, params: dict) -> dict:
        """Execute an action on the external service.

        Args:
            action: The action identifier to execute.
            params: Parameters for the action.

        Returns:
            Result dictionary from the action execution.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the external service.

        Returns:
            True if disconnection was successful.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this connector."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """List of action capabilities this connector supports."""
        ...


class ConnectorHub:
    """ConnectorHub — n8n-style External Connector Hub.

    Manages registration, discovery, and execution of external service
    connectors. Connectors must implement the BaseConnector interface.

    Usage:
        hub = ConnectorHub()
        hub.register(my_connector)
        result = await hub.execute("github", "create_issue", {"title": "Bug"})
    """

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> bool:
        """Register a connector with the hub.

        Args:
            connector: A BaseConnector instance to register.

        Returns:
            True if registration was successful, False if a connector
            with the same name already exists.
        """
        if connector.name in self._connectors:
            return False
        self._connectors[connector.name] = connector
        return True

    def unregister(self, name: str) -> bool:
        """Unregister a connector from the hub.

        Args:
            name: The name of the connector to remove.

        Returns:
            True if the connector was found and removed.
        """
        if name not in self._connectors:
            return False
        del self._connectors[name]
        return True

    async def execute(self, connector_name: str, action: str, params: dict) -> dict:
        """Execute an action through a named connector.

        Args:
            connector_name: Name of the registered connector.
            action: The action to execute.
            params: Parameters for the action.

        Returns:
            Result dictionary from the connector execution.

        Raises:
            KeyError: If the connector is not registered.
        """
        if connector_name not in self._connectors:
            raise KeyError(f"Connector '{connector_name}' is not registered.")
        connector = self._connectors[connector_name]
        return await connector.execute(action, params)

    def list_connectors(self) -> list[dict]:
        """List all registered connectors and their metadata.

        Returns:
            List of dictionaries with keys: name, capabilities.
        """
        return [
            {"name": c.name, "capabilities": c.capabilities}
            for c in self._connectors.values()
        ]

    def get_connector(self, name: str) -> BaseConnector | None:
        """Retrieve a connector by name.

        Args:
            name: The connector name to look up.

        Returns:
            The BaseConnector instance, or None if not found.
        """
        return self._connectors.get(name)
