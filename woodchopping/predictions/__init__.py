"""Historical STRATHEX predictors retained for compatibility tools.

Live STRATHEX 7 calculations use :mod:`woodchopping.strathmark_adapter` and
STRATHMARK v2. Import legacy modules explicitly if an archived audit needs them;
this package no longer imports XGBoost or Ollama at application startup.
"""

__all__: list[str] = []
