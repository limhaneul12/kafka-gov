"""i18n Translation System

Provides translation functions for backend API messages.
"""

from .translator import get_current_language, set_language, t

__all__ = ["get_current_language", "set_language", "t"]
