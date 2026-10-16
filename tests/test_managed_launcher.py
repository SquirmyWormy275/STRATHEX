"""New shared clients must leave retro startup and saved authority alone."""

import pytest

from woodchopping.managed_launcher import workspace_url


def test_workspace_deep_link_is_not_an_authorization_token():
    assert (
        workspace_url("http://127.0.0.1:8789", "synthetic:show:event")
        == "http://127.0.0.1:8789/events/synthetic%3Ashow%3Aevent"
    )
    for bad in (
        "http://example.com",
        "https://user:secret@example.com",
        "https://example.com/?token=secret",
        "file:///tmp/event",
        "https://example.com/#token",
    ):
        with pytest.raises(ValueError):
            workspace_url(bad, "event")
