"""Supabase authentication + client for the Streamlit dashboard (staff login).

Reads SUPABASE_URL + SUPABASE_ANON_KEY from st.secrets or env. Uses the ANON key
only (never the service_role key) — RLS restricts authenticated staff to read-only.
Degrades to a demo login when Supabase isn't configured yet, so the dashboard still
runs before the project exists.
"""

from __future__ import annotations

import os

import streamlit as st

try:
    from supabase import create_client
except Exception:  # pragma: no cover - dashboard still runs without the package
    create_client = None


def _secret(name: str) -> str | None:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name)


def is_configured() -> bool:
    """True when a real Supabase project + anon key are available."""
    return bool(create_client and _secret("SUPABASE_URL") and _secret("SUPABASE_ANON_KEY"))


@st.cache_resource(show_spinner=False)
def _base_client():
    return create_client(_secret("SUPABASE_URL"), _secret("SUPABASE_ANON_KEY"))


def get_client():
    """Anon client with the signed-in user's session applied (reads run under RLS)."""
    if not is_configured():
        return None
    client = _base_client()
    tok = st.session_state.get("sb_access_token")
    ref = st.session_state.get("sb_refresh_token")
    if tok and ref:
        try:
            client.auth.set_session(tok, ref)
        except Exception:
            pass
    return client


def _store_session(session, user, fallback_email: str) -> None:
    st.session_state["sb_access_token"] = session.access_token
    st.session_state["sb_refresh_token"] = session.refresh_token
    st.session_state["sb_user_email"] = getattr(user, "email", fallback_email)
    st.session_state["authed"] = True


def sign_in(email: str, password: str) -> tuple[bool, str | None]:
    """Sign in with email/password. Returns (ok, error_message)."""
    if not is_configured():
        if email:
            st.session_state["authed"] = True  # demo mode (no Supabase yet)
            return True, None
        return False, "Enter your email."
    try:
        res = _base_client().auth.sign_in_with_password({"email": email, "password": password})
        if not res.session:
            return False, "Invalid email or password."
        _store_session(res.session, res.user, email)
        return True, None
    except Exception as e:
        return False, str(e)


def sign_up(email: str, password: str, display_name: str | None = None) -> tuple[bool, str | None]:
    """Create a staff account. Returns (ok, error_message)."""
    if not is_configured():
        if email:
            st.session_state["authed"] = True
            return True, None
        return False, "Enter your email."
    try:
        payload: dict = {"email": email, "password": password}
        if display_name:
            payload["options"] = {"data": {"display_name": display_name}}
        res = _base_client().auth.sign_up(payload)
        if res.session:  # auto-confirm on; otherwise user must confirm email
            _store_session(res.session, res.user, email)
        else:
            st.session_state["authed"] = True
        return True, None
    except Exception as e:
        return False, str(e)


def sign_out() -> None:
    if is_configured():
        try:
            _base_client().auth.sign_out()
        except Exception:
            pass
    for k in ("sb_access_token", "sb_refresh_token", "sb_user_email", "authed"):
        st.session_state.pop(k, None)
