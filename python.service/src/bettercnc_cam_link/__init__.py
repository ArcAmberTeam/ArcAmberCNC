"""CAM reception and machining feedback over TCP, with optional LAN UDP discovery.

The receiver owns its inbox, never machine program directories or commands.
Execution is explicitly enabled and delegated through the public local CAM job protocol.
"""

from ._discovery import DiscoveryOptions
from ._server import main, serve

__all__ = ["DiscoveryOptions", "main", "serve"]
