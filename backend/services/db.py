"""Per-user storage: profile, GitHub repo and token, and the cost of every generation.

A SQLite file: backend/data.db by default, or the path in SQLITE_PATH.
"""
import base64
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text,
                        create_engine, insert, select, update)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

RECENT_GENERATIONS = 20


def _database_path() -> Path:
    """SQLite file; SQLITE_PATH lets a host point it at a persistent disk."""
    custom = os.environ.get("SQLITE_PATH", "").strip()
    path = Path(custom) if custom else Path(__file__).resolve().parent.parent / "data.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# The timeout makes a writer wait for another worker's write instead of failing with "locked".
engine = create_engine(f"sqlite:///{_database_path()}", connect_args={"timeout": 15})
metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("name", String(200), nullable=False, default=""),
    Column("provider", String(20), nullable=False, default=""),
    Column("github_repo", String(200), nullable=False, default=""),
    Column("github_token_enc", Text, nullable=False, default=""),  # encrypted, never sent to the client
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_login_at", DateTime(timezone=True), nullable=False),
)

generations = Table(
    "generations", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("repo", String(200), nullable=False, default=""),
    Column("folder", String(200), nullable=False, default=""),
    Column("model", String(80), nullable=False, default=""),
    Column("input_tokens", Integer, nullable=False, default=0),
    Column("output_tokens", Integer, nullable=False, default=0),
    Column("cost_usd", Float, nullable=False, default=0.0),
    Column("github_url", Text, nullable=False, default=""),
    Column("pages_url", Text, nullable=False, default=""),
    Column("error", Text, nullable=False, default=""),
)

try:
    metadata.create_all(engine)
except SQLAlchemyError:
    # Two gunicorn workers can race to create the tables on the first boot; the loser retries.
    metadata.create_all(engine)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fernet() -> Fernet:
    secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("Server has no SECRET_KEY configured")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def ensure_user(email: str, name: str = "", provider: str = "", login: bool = False) -> None:
    """Create the user's row if it is missing; on a sign-in also refresh name and login time."""
    with engine.begin() as conn:
        exists = conn.execute(select(users.c.id).where(users.c.email == email)).first()
        if exists and not login:
            return
        if exists:
            values = {"last_login_at": _now(), "provider": provider}
            if name:
                values["name"] = name
            conn.execute(update(users).where(users.c.email == email).values(**values))
            return
        try:
            with conn.begin_nested():
                conn.execute(insert(users).values(
                    email=email, name=name, provider=provider, created_at=_now(), last_login_at=_now()))
        except IntegrityError:
            pass  # a concurrent request created it first


def save_github(email: str, repo: str | None = None, token: str | None = None) -> None:
    """Update the stored repo and/or token. `None` leaves a field alone; "" clears it."""
    values = {}
    if repo is not None:
        values["github_repo"] = repo
    if token is not None:
        values["github_token_enc"] = _fernet().encrypt(token.encode()).decode() if token else ""
    if values:
        with engine.begin() as conn:
            conn.execute(update(users).where(users.c.email == email).values(**values))


def github_settings(email: str) -> tuple[str, str]:
    """The user's stored (repo, token); each is "" when not set or no longer decryptable."""
    with engine.connect() as conn:
        row = conn.execute(
            select(users.c.github_repo, users.c.github_token_enc).where(users.c.email == email)).first()
    if not row:
        return "", ""
    token = ""
    if row.github_token_enc:
        try:
            token = _fernet().decrypt(row.github_token_enc.encode()).decode()
        except InvalidToken:  # SECRET_KEY changed since it was saved: the user has to enter it again
            token = ""
    return row.github_repo, token


def record_generation(email: str, prompt: str, repo: str, result: dict | None, usage: dict | None,
                      error: str = "") -> None:
    result, usage = result or {}, usage or {}
    with engine.begin() as conn:
        user_id = conn.execute(select(users.c.id).where(users.c.email == email)).scalar_one()
        conn.execute(insert(generations).values(
            user_id=user_id, created_at=_now(), prompt=prompt, repo=repo,
            folder=result.get("folder", ""), model=usage.get("model", ""),
            input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
            cost_usd=usage.get("cost_usd", 0.0),
            github_url=result.get("github_url", ""), pages_url=result.get("pages_url", ""),
            error=error or result.get("github_error", ""),
        ))


def _generation(g) -> dict:
    return {
        "created_at": g.created_at.isoformat(),
        "prompt": g.prompt,
        "repo": g.repo,
        "model": g.model,
        "input_tokens": g.input_tokens,
        "output_tokens": g.output_tokens,
        "cost_usd": g.cost_usd,
        "github_url": g.github_url,
        "pages_url": g.pages_url,
        "error": g.error,
    }


def _user(user, gens: list) -> dict:
    """A user as sent to the client. The GitHub token itself is never included."""
    return {
        "email": user.email,
        "name": user.name,
        "provider": user.provider,
        "github_repo": user.github_repo,
        "has_github_token": bool(user.github_token_enc),
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat(),
        "total_cost_usd": round(sum(g.cost_usd for g in gens), 6),
        "generation_count": len(gens),
        "generations": [_generation(g) for g in gens[:RECENT_GENERATIONS]],
    }


def profile(email: str) -> dict:
    """What the profile menu shows: the user, their running cost and latest generations."""
    with engine.connect() as conn:
        user = conn.execute(select(users).where(users.c.email == email)).first()
        gens = conn.execute(
            select(generations).where(generations.c.user_id == user.id)
            .order_by(generations.c.id.desc())).all()
    return _user(user, gens)


def all_users() -> list[dict]:
    """Every registered user with their latest generations, newest sign-in first (admin view)."""
    with engine.connect() as conn:
        rows = conn.execute(select(users).order_by(users.c.last_login_at.desc())).all()
        gens = conn.execute(select(generations).order_by(generations.c.id.desc())).all()
    by_user: dict[int, list] = {}
    for g in gens:
        by_user.setdefault(g.user_id, []).append(g)
    return [_user(u, by_user.get(u.id, [])) for u in rows]
