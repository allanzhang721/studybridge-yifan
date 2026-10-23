import pytest
from studybridge.storage import Store, ConflictError
from studybridge.engine import new_workspace


def test_accounts_isolated_passwords_hashed_and_revisions_checked(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.register("alice", "correct-password")
    store.register("bruno", "another-password")
    assert store.authenticate("alice", "correct-password") == "alice"
    with pytest.raises(ValueError):
        store.authenticate("alice", "wrong")
    state, revision = store.load("alice")
    state["courses"] = [{"private": "Alice's private notes"}]
    store.save("alice", state, revision)
    assert store.load("bruno")[0]["courses"] == []
    with pytest.raises(ConflictError):
        store.save("alice", state, revision)
    with store.connect() as db:
        saved = db.execute("SELECT password FROM users WHERE username='alice'").fetchone()[0]
    assert saved != "correct-password"


def test_pending_feedback_not_visible_to_other_accounts(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.register("alice", "correct-password")
    store.register("bruno", "another-password")
    qid = store.submit_feedback("alice", "Where can I see this month's receipt?")
    assert len(store.feedback("alice")) == 1
    assert store.feedback("bruno") == [] and store.feedback() == []
    store.moderate(qid, "No donations have been made yet; this remains prelaunch.")
    post = store.feedback()[0]
    assert "username" not in post and post["status"] == "published"
    assert post["replies"][0][1] == "Platform team"
    store.delete_account("alice")
    assert store.feedback() == []
    with pytest.raises(ValueError):
        store.load("alice")


def test_login_lockout(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.register("alice", "correct-password")
    for _ in range(5):
        with pytest.raises(ValueError):
            store.authenticate("alice", "wrong")
    with pytest.raises(ValueError, match="15 minutes"):
        store.authenticate("alice", "correct-password")

