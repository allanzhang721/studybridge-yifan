from pathlib import Path
import sqlite3

from streamlit.testing.v1 import AppTest

from studybridge.storage import Store

APP = Path(__file__).resolve().parents[1] / "app.py"


def button(app, label):
    return next(b for b in app.button if b.label == label)


def signed_in(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "save.sqlite"))
    store = Store()
    store.register("student", "safe-test-password")
    app = AppTest.from_file(str(APP)).run()
    app.session_state["username"] = "student"
    app.session_state["workspace"], app.session_state["revision"] = store.load("student")
    app.run()
    return app, store


def test_conflict_keeps_unsaved_changes_until_explicit_reload(tmp_path, monkeypatch):
    app, store = signed_in(tmp_path, monkeypatch)
    other, revision = store.load("student")
    other["ai_calls"] = 3
    store.save("student", other, revision)
    button(app, "Load sample course").click().run()
    assert not app.exception
    assert app.session_state["save_pending"]
    assert len(app.session_state["workspace"]["courses"]) == 1
    assert store.load("student")[0]["courses"] == []
    assert button(app, "Load saved version").disabled
    next(c for c in app.checkbox if "exported my unsaved" in c.label).check()
    button(app, "Load saved version").click().run()
    assert not app.exception
    assert not app.session_state["save_pending"]
    assert app.session_state["workspace"]["ai_calls"] == 3


def test_failed_save_can_retry_without_losing_course(tmp_path, monkeypatch):
    app, store = signed_in(tmp_path, monkeypatch)
    original = Store.save

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError("private internal database detail")

    monkeypatch.setattr(Store, "save", unavailable)
    button(app, "Load sample course").click().run()
    assert not app.exception
    assert app.session_state["save_pending"]
    assert len(app.session_state["workspace"]["courses"]) == 1
    assert all("private internal" not in e.value for e in app.error)
    monkeypatch.setattr(Store, "save", original)
    button(app, "Retry saving").click().run()
    assert not app.exception
    assert not app.session_state["save_pending"]
    assert len(store.load("student")[0]["courses"]) == 1
    assert any("Saved ·" in c.value for c in app.caption)
