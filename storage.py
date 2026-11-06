"""Storage layer for Next Chapter.

Everything is keyed by the user's **email** — that is how a person is tied to their
activity/history across the app.

This ships with `InSessionStorage`, which keeps everything in `st.session_state`
(nothing is written to disk). That is intentional for the skeleton:
  - zero latency,
  - no personal data persisted (important for this sensitive population),
  - and a clean seam for the team to swap in a real backend later.

To add real persistence, implement the `Storage` interface with a new class
(e.g. `SupabaseStorage` or `SQLiteStorage`) and change only `get_storage()` below.
No caller needs to change.

NOTE for the team: on Streamlit Community Cloud the filesystem is ephemeral, so a
local SQLite file resets on redeploy. Use a hosted DB (e.g. Supabase) for durable data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import streamlit as st


class Storage(ABC):
    """Interface every storage backend implements. Keyed by email."""

    # --- users -----------------------------------------------------------
    @abstractmethod
    def get_user(self, email: str) -> dict | None:
        """Return the user record for `email`, or None if not found."""

    @abstractmethod
    def create_user(self, user: dict) -> None:
        """Persist a new user record. `user` must contain at least 'email'."""

    # --- per-user activity / history ------------------------------------
    @abstractmethod
    def save_profile(self, email: str, profile: dict) -> None: ...

    @abstractmethod
    def get_profile(self, email: str) -> dict | None: ...

    @abstractmethod
    def save_matches(self, email: str, matches: list[dict]) -> None: ...

    @abstractmethod
    def get_matches(self, email: str) -> list[dict]: ...

    @abstractmethod
    def save_letter(self, email: str, job_soc: str, letter: dict) -> None: ...

    @abstractmethod
    def get_letters(self, email: str) -> dict[str, dict]: ...

    @abstractmethod
    def get_history(self, email: str) -> dict[str, Any]:
        """Return everything stored for a user (profile, matches, letters)."""


class InSessionStorage(Storage):
    """In-memory storage backed by st.session_state. Nothing hits disk.

    Data lives only for the browser session, so refreshing keeps it but it is
    never persisted server-side. Swap this out to add real persistence.
    """

    _USERS_KEY = "_store_users"       # email -> user record
    _DATA_KEY = "_store_data"         # email -> {profile, matches, letters}

    def __init__(self) -> None:
        st.session_state.setdefault(self._USERS_KEY, {})
        st.session_state.setdefault(self._DATA_KEY, {})

    @property
    def _users(self) -> dict[str, dict]:
        return st.session_state[self._USERS_KEY]

    @property
    def _data(self) -> dict[str, dict]:
        return st.session_state[self._DATA_KEY]

    def _bucket(self, email: str) -> dict:
        return self._data.setdefault(
            email, {"profile": None, "matches": [], "letters": {}}
        )

    # --- users -----------------------------------------------------------
    def get_user(self, email: str) -> dict | None:
        return self._users.get(email.lower().strip())

    def create_user(self, user: dict) -> None:
        email = user["email"].lower().strip()
        user["email"] = email
        self._users[email] = user

    # --- per-user activity ----------------------------------------------
    def save_profile(self, email: str, profile: dict) -> None:
        self._bucket(email)["profile"] = profile

    def get_profile(self, email: str) -> dict | None:
        return self._bucket(email)["profile"]

    def save_matches(self, email: str, matches: list[dict]) -> None:
        self._bucket(email)["matches"] = matches

    def get_matches(self, email: str) -> list[dict]:
        return self._bucket(email)["matches"]

    def save_letter(self, email: str, job_soc: str, letter: dict) -> None:
        self._bucket(email)["letters"][job_soc] = letter

    def get_letters(self, email: str) -> dict[str, dict]:
        return self._bucket(email)["letters"]

    def get_history(self, email: str) -> dict[str, Any]:
        return self._bucket(email)


class SQLiteStorage(Storage):
    """Durable backend (db.py). Users go in the users table; activity in kv, keyed by email."""

    def get_user(self, email: str) -> dict | None:
        import db
        return db.get_user(email.lower().strip())

    def create_user(self, user: dict) -> None:
        import db
        user["email"] = user["email"].lower().strip()
        db.upsert_user(user)

    def _get(self, email: str, field: str, default):
        import db
        return db.kv_get(f"{email}:{field}", default)

    def _set(self, email: str, field: str, value) -> None:
        import db
        db.kv_set(f"{email}:{field}", value)

    def save_profile(self, email: str, profile: dict) -> None:
        self._set(email, "profile", profile)

    def get_profile(self, email: str) -> dict | None:
        return self._get(email, "profile", None)

    def save_matches(self, email: str, matches: list[dict]) -> None:
        self._set(email, "matches", matches)

    def get_matches(self, email: str) -> list[dict]:
        return self._get(email, "matches", [])

    def save_letter(self, email: str, job_soc: str, letter: dict) -> None:
        letters = self.get_letters(email)
        letters[job_soc] = letter
        self._set(email, "letters", letters)

    def get_letters(self, email: str) -> dict[str, dict]:
        return self._get(email, "letters", {})

    def get_history(self, email: str) -> dict[str, Any]:
        return {"profile": self.get_profile(email), "matches": self.get_matches(email),
                "letters": self.get_letters(email)}


def get_storage() -> Storage:
    """Return the active storage backend.

    Swap the implementation here to change backends app-wide. Constructed per call
    (cheap) so the in-session backend initializes this session's state every rerun.
    """
    return SQLiteStorage()
