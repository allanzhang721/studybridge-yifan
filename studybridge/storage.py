"""Private local accounts and versioned workspaces. No raw uploads on disk."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from .engine import new_workspace, now

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "studybridge.sqlite"


class ConflictError(ValueError):
    pass


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("STUDYBRIDGE_DB_PATH", str(DEFAULT_DB)))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, salt TEXT NOT NULL, password TEXT NOT NULL,
                    failures INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS workspaces (
                    username TEXT PRIMARY KEY REFERENCES users(username), payload TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                    created TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending');
                CREATE TABLE IF NOT EXISTS replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, feedback_id INTEGER NOT NULL,
                    created TEXT NOT NULL, role TEXT NOT NULL, body TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def password_hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()

    def register(self, username: str, password: str) -> str:
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
            raise ValueError("Use 3–24 letters, numbers, or underscores for your username.")
        if not 10 <= len(password) <= 128:
            raise ValueError("Choose a password with 10–128 characters.")
        salt = secrets.token_hex(16)
        hashed = self.password_hash(password, salt)
        try:
            with self.connect() as db:
                db.execute("INSERT INTO users(username,salt,password) VALUES (?,?,?)", (username, salt, hashed))
                db.execute("INSERT INTO workspaces(username,payload) VALUES (?,?)", (username, json.dumps(new_workspace())))
        except sqlite3.IntegrityError:
            raise ValueError("This username is unavailable.") from None
        return username

    def authenticate(self, username: str, password: str) -> str:
        username = username.strip().lower()
        if len(password) > 128:
            raise ValueError("Unable to sign in. Check your details or try again later.")
        with self.connect() as db:
            row = db.execute("SELECT salt,password,failures,locked_until FROM users WHERE username=?", (username,)).fetchone()
            if not row:
                self.password_hash(password, "0"*32)
                raise ValueError("Unable to sign in. Check your details or try again later.")
            salt, hashed, failures, locked_until = row
            if locked_until > time.time():
                raise ValueError("Too many attempts. Try again in 15 minutes.")
            if not hmac.compare_digest(hashed, self.password_hash(password, salt)):
                failures = failures + 1 if locked_until == 0 else 1
                db.execute("UPDATE users SET failures=?,locked_until=? WHERE username=?", (failures, time.time()+900 if failures >= 5 else 0, username))
                db.commit()
                raise ValueError("Unable to sign in. Check your details or try again later.")
            db.execute("UPDATE users SET failures=0,locked_until=0 WHERE username=?", (username,))
        return username

    def load(self, username: str) -> tuple[dict, int]:
        with self.connect() as db:
            row = db.execute("SELECT payload,revision FROM workspaces WHERE username=?", (username,)).fetchone()
        if not row:
            raise ValueError("Workspace not found.")
        return json.loads(row[0]), row[1]

    def save(self, username: str, state: dict, revision: int) -> int:
        payload = json.dumps(state, ensure_ascii=False)
        if len(payload.encode()) > 60_000_000:
            raise ValueError("Workspace is full. Export your records, then remove older courses.")
        with self.connect() as db:
            changed = db.execute("UPDATE workspaces SET payload=?,revision=revision+1 WHERE username=? AND revision=?", (payload, username, revision))
            if changed.rowcount != 1:
                raise ConflictError("Another tab updated this workspace. Sign out and back in before making more changes.")
        return revision + 1

    def delete_account(self, username: str):
        with self.connect() as db:
            db.execute("DELETE FROM replies WHERE feedback_id IN (SELECT id FROM feedback WHERE username=?)", (username,))
            db.execute("DELETE FROM feedback WHERE username=?", (username,))
            db.execute("DELETE FROM workspaces WHERE username=?", (username,))
            db.execute("DELETE FROM users WHERE username=?", (username,))

    def submit_feedback(self, username: str, body: str) -> int:
        body = body.strip()
        if not 10 <= len(body) <= 1500:
            raise ValueError("Write a question of 10–1,500 characters.")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                raise ValueError("Sign in before submitting feedback.")
            count = db.execute("SELECT COUNT(*) FROM feedback WHERE username=? AND created>=?", (username, now()[:10])).fetchone()[0]
            if count >= 5:
                raise ValueError("You have reached today's five-question limit.")
            cursor = db.execute("INSERT INTO feedback(username,created,body) VALUES (?,?,?)", (username, now(), body))
            return cursor.lastrowid

    def feedback(self, username: str | None = None):
        with self.connect() as db:
            rows = db.execute("SELECT id,username,created,body,status FROM feedback WHERE status='published' OR username=? ORDER BY id DESC LIMIT 50", (username or "",)).fetchall()
            result = []
            for row in rows:
                replies = db.execute("SELECT created,role,body FROM replies WHERE feedback_id=? ORDER BY id", (row[0],)).fetchall()
                result.append({"id": row[0], "own": row[1] == username, "created": row[2], "body": row[3], "status": row[4], "replies": replies})
            return result

    def moderate(self, feedback_id: int, reply: str):
        if not reply.strip():
            raise ValueError("A public reply cannot be empty.")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM feedback WHERE id=?", (feedback_id,)).fetchone():
                raise ValueError("Question not found.")
            db.execute("UPDATE feedback SET status='published' WHERE id=?", (feedback_id,))
            db.execute("INSERT INTO replies(feedback_id,created,role,body) VALUES (?,?,?,?)", (feedback_id, now(), "Platform team", reply.strip()))

