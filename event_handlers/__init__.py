"""
This package contains event handlers for different Discord events.
"""

# Import the event handlers so they are registered when the package is imported
from .message import on_message
from .on_ready import on_ready
from .reaction import on_raw_reaction_add

# Export these functions when someone imports from the event_handlers package
__all__: list[str] = ["on_ready", "on_message", "on_raw_reaction_add"]
