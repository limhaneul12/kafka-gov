"""i18n Translation System for Backend

Usage:
    from app.shared.i18n.translator import t, set_language

    # Use translation
    message = t("error.topic_not_found", name="prod.orders")

    # Change language
    set_language("en")
"""

import json
from pathlib import Path
from typing import Any


class Translator:
    """Translation manager for backend messages"""

    def __init__(self, lang: str = "ko") -> None:
        self.lang = lang
        self.translations: dict[str, Any] = self._load_translations()

    def _load_translations(self) -> dict[str, Any]:
        """Load translation file"""
        file_path = Path(__file__).parent / f"{self.lang}.json"

        if not file_path.exists():
            # Fallback to Korean if file doesn't exist
            file_path = Path(__file__).parent / "ko.json"

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def t(self, key: str, **kwargs: Any) -> str:  # 다양한 타입의 포맷 변수 지원
        """Get translated text with optional formatting

        Args:
            key: Translation key in dot notation (e.g., "error.not_found")
            **kwargs: Variables for string formatting (Any 사용 이유: str, int, float 등
                     다양한 타입의 포맷 변수를 지원하기 위함)

        Returns:
            Translated string, or the key itself if not found

        Examples:
            >>> t("error.topic_not_found")
            "Topic not found"

            >>> t("error.invalid_value", field="partition", value=0)
            "Invalid value for partition: 0"
        """
        keys = key.split(".")
        value: Any = self.translations  # 중첩 dict 탐색 시 타입 변화

        # Navigate through nested dict
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, key)
            else:
                return key

        # Format string if kwargs provided
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                # If formatting fails, return original string
                return value

        return value if isinstance(value, str) else key


# Global translator instance
_translator = Translator("ko")


def t(key: str, **kwargs: Any) -> str:  # 다양한 타입의 포맷 변수 지원
    """Get translated text (module-level function)

    Args:
        key: Translation key
        **kwargs: Variables for formatting (Any 사용 이유: 포맷 변수의 타입 다양성)

    Returns:
        Translated string
    """
    return _translator.t(key, **kwargs)


def set_language(lang: str) -> None:
    """Change translation language globally

    Args:
        lang: Language code ("ko" or "en")
    """
    global _translator
    _translator = Translator(lang)


def get_current_language() -> str:
    """Get current language code"""
    return _translator.lang
