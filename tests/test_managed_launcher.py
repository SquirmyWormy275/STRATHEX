"""New shared clients must leave retro startup and saved authority alone."""

from urllib.parse import quote, urlsplit

import pytest
from strathmark.events.contracts import identifier

from woodchopping.managed_launcher import workspace_url


def test_workspace_deep_link_is_not_an_authorization_token():
    assert (
        workspace_url("https://127.0.0.1:8789", "synthetic:show:event")
        == "https://127.0.0.1:8789/events/synthetic%3Ashow%3Aevent"
    )
    for bad in (
        "http://example.com",
        "http://127.0.0.1:8789",
        "http://localhost:8789",
        "http://[::1]:8789",
        "https://user:secret@example.com",
        "https://example.com/?token=secret",
        "file:///tmp/event",
        "https://example.com/#token",
    ):
        with pytest.raises(ValueError):
            workspace_url(bad, "event")


@pytest.mark.parametrize("event_id", [".", "..", "", "a\x00b", "a\nb", "a b", "%2e%2e", "a\\b", None, 123])
def test_workspace_rejects_non_component_identities(event_id):
    with pytest.raises(ValueError):
        workspace_url("https://example.invalid", event_id)


@pytest.mark.parametrize("event_id", ["synthetic:show:event", "event-1.2_3", "a/../b", "a/", "x" * 224])
def test_workspace_preserves_component_identity_as_one_encoded_segment(event_id):
    assert identifier(event_id) == event_id
    path = urlsplit(workspace_url("https://example.invalid", event_id)).path
    assert path == "/events/" + quote(event_id, safe="")
    assert len(path.split("/")) == 3
    assert path.split("/")[-1] not in {".", ".."}
