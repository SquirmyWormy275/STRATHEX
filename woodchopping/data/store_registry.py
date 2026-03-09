"""
STRATHMARK ResultStore Registry
================================

Module-level singleton so UI functions can access the ResultStore without
threading it through every call signature.

Usage:
    # In MainProgramV5_2.py startup:
    from woodchopping.data.store_registry import set_store
    from strathmark import ResultStore
    set_store(ResultStore())

    # In excel_io.py / anywhere else:
    from woodchopping.data.store_registry import get_store
    store = get_store()   # Returns None if not initialized
    if store:
        store.record_result(...)
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from strathmark import ResultStore

_store: Optional[object] = None


def get_store():
    """Return the active ResultStore instance, or None if not initialized."""
    return _store


def set_store(store) -> None:
    """Set the active ResultStore instance (called once on application startup)."""
    global _store
    _store = store
