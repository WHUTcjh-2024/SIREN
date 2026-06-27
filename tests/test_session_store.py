from backend.services.session_store import SessionStore


def test_session_store_removes_heavy_fields_and_round_trips(tmp_path):
    store = SessionStore(tmp_path)
    store.write("valid-session", {"H0": 12.3, "grayImage": "large-payload"})
    assert store.read("valid-session") == {"H0": 12.3}


def test_session_store_rejects_unsafe_id(tmp_path):
    store = SessionStore(tmp_path)
    try:
        store.write("../../", {"x": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe session id must be rejected")
