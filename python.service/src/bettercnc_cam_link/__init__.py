"""CAM reception and machining feedback over TCP, with optional LAN UDP discovery.

The receiver owns its inbox, never machine program directories or commands.
Local controller communication is restricted to the machine.status wire method.
"""

from ._discovery import DiscoveryOptions
from ._server import main, serve

__all__ = ["DiscoveryOptions", "main", "serve"]
