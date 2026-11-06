"""Authentication for Next Chapter.

Two ways in (both requested):
  1. Email + password  -> fully working here (passwords hashed with PBKDF2).
  2. Google sign-in     -> STUBBED button for now. See `login_google()` for how to
     wire Streamlit's native OIDC (`st.login`) later.

The signed-in user lives in `st.session_state["user"]`. `email` is the key that ties
a person to their stored activity (see storage.py).

Security note: PBKDF2 via stdlib hashlib is fine for a skeleton/demo. For production,
prefer `bcrypt`/`argon2` and a real identity provider.
"""

from __future__ import annotations

import hashlib
import hmac
import os

import streamlit as st

from storage import get_storage

_USER_KEY = "user"
_NEW_USER_KEY = "is_new_user"
_PBKDF2_ROUNDS = 200_000


# --- password hashing ----------------------------------------------------
def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, _ = stored.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    return hmac.compare_digest(_hash_password(password, salt), stored)


# --- session helpers -----------------------------------------------------
def current_user() -> dict | None:
    """Return the signed-in user record, or None."""
    return st.session_state.get(_USER_KEY)


def is_new_user() -> bool:
    """True right after sign-up, so the router sends them into My Path."""
    return bool(st.session_state.get(_NEW_USER_KEY))


def clear_new_user_flag() -> None:
    st.session_state[_NEW_USER_KEY] = False


def logout() -> None:
    st.session_state.pop(_USER_KEY, None)
    st.session_state.pop(_NEW_USER_KEY, None)


def _set_session(user: dict, new: bool) -> None:
    # Never keep the password hash in the session user object.
    st.session_state[_USER_KEY] = {k: v for k, v in user.items() if k != "password_hash"}
    st.session_state[_NEW_USER_KEY] = new


# --- auth actions --------------------------------------------------------
def signup(email: str, password: str, name: str) -> tuple[bool, str]:
    """Create an account. Returns (ok, message)."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Please enter a valid email address."
    if len(password or "") < 6:
        return False, "Password must be at least 6 characters."
    store = get_storage()
    if store.get_user(email):
        return False, "An account with this email already exists. Try signing in."
    store.create_user(
        {
            "email": email,
            "name": (name or "").strip() or email.split("@")[0],
            "password_hash": _hash_password(password),
            "provider": "email",
        }
    )
    _set_session(store.get_user(email), new=True)
    return True, "Account created."


def login(email: str, password: str) -> tuple[bool, str]:
    """Sign in with email + password. Returns (ok, message)."""
    email = (email or "").strip().lower()
    store = get_storage()
    user = store.get_user(email)
    if not user or user.get("provider") != "email":
        return False, "No account found for that email."
    if not _verify_password(password, user.get("password_hash", "")):
        return False, "Incorrect password."
    _set_session(user, new=False)
    return True, "Signed in."


def login_google() -> tuple[bool, str]:
    """STUB: pretend a Google user signed in.

    TODO(team): replace with Streamlit native OIDC.
      1. Add [auth] config + Google OAuth client id/secret to .streamlit/secrets.toml.
      2. Use st.login("google") / st.user to get the verified email + name.
      3. Upsert the user via storage and call _set_session(user, new=<first time?>).
      Docs: https://docs.streamlit.io/develop/api-reference/user/st.login
    """
    demo_email = "google.user@example.com"
    store = get_storage()
    existing = store.get_user(demo_email)
    new = existing is None
    if new:
        store.create_user(
            {
                "email": demo_email,
                "name": "Google Demo User",
                "provider": "google",
            }
        )
    _set_session(store.get_user(demo_email), new=new)
    return True, "Signed in with Google (demo stub)."
