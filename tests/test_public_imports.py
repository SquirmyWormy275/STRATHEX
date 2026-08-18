"""Smoke tests for the retained public package surface."""

from __future__ import annotations

import importlib

import woodchopping.predictions as predictions


def test_prediction_package_exports_are_importable():
    for name in predictions.__all__:
        assert getattr(predictions, name) is not None


def test_retained_public_packages_import_without_optional_services():
    for module_name in (
        "woodchopping",
        "woodchopping.predictions",
        "woodchopping.handicaps",
        "woodchopping.simulation",
        "woodchopping.strathmark_adapter",
    ):
        assert importlib.import_module(module_name) is not None
