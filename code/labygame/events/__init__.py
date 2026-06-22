"""Event tiles. Importing the package registers all built-in event types so the
runtime can build event objects from saved ``.lvl`` data by name."""
from .base import EventTile, register, create, EVENT_REGISTRY  # noqa: F401
from . import hidden_loot  # noqa: F401  (side effect: registers "hidden_loot")
from . import carrot  # noqa: F401  (side effect: registers "carrot")
from . import bear_trap  # noqa: F401  (side effect: registers "bear_trap")
