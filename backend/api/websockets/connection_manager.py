"""WebSocket connection manager for real-time updates."""

from fastapi import WebSocket
from typing import Dict, Set, Optional
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections for real-time updates.

    Supports broadcasting to specific organizations, users, or all connected clients.
    Tracks agent heartbeats for monitoring agent availability.
    """

    def __init__(self):
        """Initialize connection manager."""
        # Map of org_id -> set of WebSocket connections
        self.active_connections_by_org: Dict[str, Set[WebSocket]] = {}

        # Map of user_id -> set of WebSocket connections
        self.active_connections_by_user: Dict[str, Set[WebSocket]] = {}

        # Map of agent_id -> last heartbeat timestamp
        self.agent_heartbeats: Dict[str, datetime] = {}

    async def connect(
        self,
        websocket: WebSocket,
        org_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        Register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            org_id: Organization ID
            user_id: Optional user ID (for user connections)
            agent_id: Optional agent ID (for agent connections)
        """
        await websocket.accept()

        # Add to org connections
        if org_id not in self.active_connections_by_org:
            self.active_connections_by_org[org_id] = set()
        self.active_connections_by_org[org_id].add(websocket)

        # Add to user connections if user_id provided
        if user_id:
            if user_id not in self.active_connections_by_user:
                self.active_connections_by_user[user_id] = set()
            self.active_connections_by_user[user_id].add(websocket)

        # Record agent heartbeat if agent_id provided
        if agent_id:
            self.agent_heartbeats[agent_id] = datetime.now(timezone.utc)

        logger.info(
            f"WebSocket connected - org_id: {org_id}, user_id: {user_id}, agent_id: {agent_id}"
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        org_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection
            org_id: Organization ID
            user_id: Optional user ID
            agent_id: Optional agent ID
        """
        # Remove from org connections
        if org_id in self.active_connections_by_org:
            self.active_connections_by_org[org_id].discard(websocket)
            if not self.active_connections_by_org[org_id]:
                del self.active_connections_by_org[org_id]

        # Remove from user connections
        if user_id and user_id in self.active_connections_by_user:
            self.active_connections_by_user[user_id].discard(websocket)
            if not self.active_connections_by_user[user_id]:
                del self.active_connections_by_user[user_id]

        # Remove agent heartbeat
        if agent_id and agent_id in self.agent_heartbeats:
            del self.agent_heartbeats[agent_id]

        logger.info(
            f"WebSocket disconnected - org_id: {org_id}, user_id: {user_id}, agent_id: {agent_id}"
        )

    async def broadcast(self, message: dict) -> None:
        """
        Broadcast message to all connected clients.

        Args:
            message: Message to broadcast (will be JSON encoded)
        """
        message_str = json.dumps(message)
        disconnected = set()

        for connections in self.active_connections_by_org.values():
            for connection in connections:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {str(e)}")
                    disconnected.add(connection)

        # Clean up disconnected connections
        for org_id in list(self.active_connections_by_org.keys()):
            self.active_connections_by_org[org_id] -= disconnected

    async def send_to_org(self, org_id: str, message: dict) -> None:
        """
        Send message to all users in an organization.

        Args:
            org_id: Organization ID
            message: Message to send
        """
        if org_id not in self.active_connections_by_org:
            return

        message_str = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections_by_org[org_id]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to org {org_id}: {str(e)}")
                disconnected.add(connection)

        # Clean up disconnected connections
        self.active_connections_by_org[org_id] -= disconnected

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """
        Send message to a specific user across all their connections.

        Args:
            user_id: User ID
            message: Message to send
        """
        if user_id not in self.active_connections_by_user:
            return

        message_str = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections_by_user[user_id]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {str(e)}")
                disconnected.add(connection)

        # Clean up disconnected connections
        self.active_connections_by_user[user_id] -= disconnected

    def update_agent_heartbeat(self, agent_id: str) -> None:
        """
        Update the last heartbeat timestamp for an agent.

        Args:
            agent_id: Agent ID
        """
        self.agent_heartbeats[agent_id] = datetime.now(timezone.utc)
        logger.debug(f"Agent {agent_id} heartbeat updated")

    def get_agent_heartbeat(self, agent_id: str) -> Optional[datetime]:
        """
        Get the last heartbeat timestamp for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Last heartbeat timestamp or None if agent not connected
        """
        return self.agent_heartbeats.get(agent_id)

    def is_agent_connected(self, agent_id: str, timeout_seconds: int = 30) -> bool:
        """
        Check if an agent is currently connected and responsive.

        An agent is considered connected if its last heartbeat was within the timeout period.

        Args:
            agent_id: Agent ID
            timeout_seconds: Seconds without heartbeat to consider agent disconnected

        Returns:
            True if agent is connected, False otherwise
        """
        heartbeat = self.agent_heartbeats.get(agent_id)
        if not heartbeat:
            return False

        elapsed = (datetime.now(timezone.utc) - heartbeat).total_seconds()
        return elapsed < timeout_seconds

    def get_connected_agents(self) -> Dict[str, datetime]:
        """
        Get all connected agents and their last heartbeat times.

        Returns:
            Dictionary of agent_id -> last_heartbeat
        """
        return self.agent_heartbeats.copy()


# Global connection manager instance
manager = ConnectionManager()
