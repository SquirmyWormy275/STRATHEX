"""Smoke tests for the retained public package surface."""

from __future__ import annotations

import importlib

import woodchopping.predictions as predictions


def test_prediction_package_intentionally_has_no_eager_public_exports():
    assert predictions.__all__ == []


def test_retained_public_packages_import_without_optional_services():
    for module_name in (
        "woodchopping",
        "woodchopping.predictions",
        "woodchopping.handicaps",
        "woodchopping.simulation",
        "woodchopping.strathmark_adapter",
    ):
        assert importlib.import_module(module_name) is not None
