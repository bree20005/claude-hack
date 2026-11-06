"""SQLite persistence for Rebloom.

One file (data/rebloom.db, gitignored, created on first run). What's stored:
  users           accounts from the log-in dialog (phone / email / Google). Guests: nothing.
  user_state      each signed-in user's progress (chat, answers, tags, matches, letters,
                  member conversations), so she can sign out and pick up where she left off.
  stories         published community stories (PRD 5/6), visible to every user.
  kv              small key/value store used by storage.py.

Privacy: guest sessions are never written. Signed-in users can delete everything with
"Delete my data" (header menu). Published stories hold only the approved public fields.

Note: on Streamlit Community Cloud the filesystem resets on redeploy/reboot; for a
long-lived deployment swap this module for a hosted DB (e.g. Supabase Postgres).
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "rebloom.db"
_LOCK = threading.Lock()

_SCHEMA = """
create table if not exists users (
  id text primary key, name text, provider text, program_code text,
  created_at text, last_seen text
);
create table if not exists user_state (
  user_id text primary key references users(id) on delete cascade,
  state_json text not null, updated_at text
);
create table if not exists stories (
  id text primary key, author_id text unique, created_at text, updated_at text,
  display_name text not null, current_job text not null, journey text not null, advice text,
  industry_tags text not null, experience_tags text not null, synthetic integer not null default 0
);
create table if not exists kv (k text primary key, v text);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@st.cache_resource
def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma journal_mode=wal")
    conn.execute("pragma foreign_keys=on")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _exec(sql: str, args: tuple = ()) -> None:
    with _LOCK:
        c = _conn()
        c.execute(sql, args)
        c.commit()


def _all(sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    with _LOCK:
        return _conn().execute(sql, args).fetchall()


# --- users -----------------------------------------------------------------------
def get_user(uid: str) -> dict | None:
    rows = _all("select * from users where id = ?", (uid,))
    if not rows:
        return None
    r = dict(rows[0])
    return {"email": r["id"], "name": r["name"], "provider": r["provider"], "program_code": r["program_code"]}


def upsert_user(user: dict) -> None:
    _exec(
        "insert into users (id, name, provider, program_code, created_at, last_seen) values (?,?,?,?,?,?) "
        "on conflict(id) do update set last_seen = excluded.last_seen",
        (user["email"], user.get("name"), user.get("provider"), user.get("program_code", ""), _now(), _now()),
    )


def delete_user_data(uid: str) -> None:
    _exec("delete from stories where author_id = ?", (uid,))
    _exec("delete from user_state where user_id = ?", (uid,))
    _exec("delete from users where id = ?", (uid,))


# --- per-user progress -------------------------------------------------------------
def load_state(uid: str) -> dict:
    rows = _all("select state_json from user_state where user_id = ?", (uid,))
    return json.loads(rows[0]["state_json"]) if rows else {}


def save_state(uid: str, state: dict) -> None:
    _exec(
        "insert into user_state (user_id, state_json, updated_at) values (?,?,?) "
        "on conflict(user_id) do update set state_json = excluded.state_json, updated_at = excluded.updated_at",
        (uid, json.dumps(state, default=list), _now()),
    )


# --- stories (PRD 5/6) ----------------------------------------------------------------
def _story(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["industry_tags"] = json.loads(d["industry_tags"])
    d["experience_tags"] = json.loads(d["experience_tags"])
    d["synthetic"] = bool(d["synthetic"])
    return d


def list_stories() -> list[dict]:
    return [_story(r) for r in _all("select * from stories order by created_at desc")]


def story_by_author(uid: str) -> dict | None:
    rows = _all("select * from stories where author_id = ?", (uid,))
    return _story(rows[0]) if rows else None


def upsert_story(uid: str, s: dict) -> dict:
    existing = story_by_author(uid)
    sid = existing["id"] if existing else uuid.uuid4().hex[:10]
    created = existing["created_at"] if existing else _now()
    _exec(
        "insert into stories (id, author_id, created_at, updated_at, display_name, current_job, journey, advice, "
        "industry_tags, experience_tags, synthetic) values (?,?,?,?,?,?,?,?,?,?,0) "
        "on conflict(author_id) do update set updated_at=excluded.updated_at, display_name=excluded.display_name, "
        "current_job=excluded.current_job, journey=excluded.journey, advice=excluded.advice, "
        "industry_tags=excluded.industry_tags, experience_tags=excluded.experience_tags",
        (sid, uid, created, _now(), s["display_name"], s["current_job"], s["journey"], s.get("advice", ""),
         json.dumps(s["industry_tags"]), json.dumps(s["experience_tags"])),
    )
    return story_by_author(uid)


def delete_story(uid: str) -> None:
    _exec("delete from stories where author_id = ?", (uid,))


# --- kv ----------------------------------------------------------------------------------
def kv_get(k: str, default=None):
    rows = _all("select v from kv where k = ?", (k,))
    return json.loads(rows[0]["v"]) if rows else default


def kv_set(k: str, v) -> None:
    _exec("insert into kv (k, v) values (?, ?) on conflict(k) do update set v = excluded.v", (k, json.dumps(v)))


def stats() -> dict:
    return {
        "users": _all("select count(*) n from users")[0]["n"],
        "stories": _all("select count(*) n from stories")[0]["n"],
    }
