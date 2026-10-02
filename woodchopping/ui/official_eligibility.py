"""Resolve persisted competition authority before official output or results."""

from woodchopping.ui.prediction_context import AuthorityReference


def require_official_eligibility(root_state, *, authority_store=None):
    from woodchopping.strathmark_v3_local import LOCAL_V3_PREVIEW_CONTRACTS

    if "prediction_authority_ref" not in root_state:
        return  # Existing legacy workflows retain their migration policy.
    if authority_store is None:
        from woodchopping.ui.multi_event_ui import _configured_authority_store

        authority_store = _configured_authority_store(None)
    if authority_store is None:
        raise ValueError("cannot verify saved prediction authority for official results or schedule")
    receipt = authority_store.resolve(AuthorityReference.from_json(root_state["prediction_authority_ref"]))
    if receipt.engine == "v3" and receipt.contract_identity in LOCAL_V3_PREVIEW_CONTRACTS:
        raise ValueError("V3 numeric previews cannot be exported or recorded as official schedules or results")
