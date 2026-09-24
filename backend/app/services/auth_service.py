"""Password hashing, account persistence, and small signed login tokens."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
TOKEN_TTL_SECONDS = 8 * 60 * 60


class AuthenticationError(Exception):
    """Raised when credentials or a bearer token are invalid."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    normalized = normalize_email(email)
    local, separator, domain = normalized.partition("@")
    if separator != "@" or not local or not domain or "." not in domain:
        raise ValueError("Enter a valid email address.")
    return normalized


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    """Hash with scrypt and a unique random salt; never save the password."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=64,
    )
    return "$".join(
        [
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _encode(salt),
            _encode(digest),
        ]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, n, r, p, salt_text, expected_text = encoded_hash.split("$")
        if scheme != "scrypt":
            return False
        salt = _decode(salt_text)
        expected = _decode(expected_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def public_user(row: sqlite3.Row | dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
    }


class AuthService:
    def __init__(self) -> None:
        # Set AUTH_SECRET in a deployment. The random development fallback
        # keeps this sample safe by default and invalidates old tokens on restart.
        configured_secret = os.getenv("AUTH_SECRET")
        self.secret = (
            configured_secret.encode("utf-8")
            if configured_secret
            else secrets.token_bytes(32)
        )

    def register(
        self,
        db: sqlite3.Connection,
        *,
        name: str,
        email: str,
        password: str,
        role: str,
    ) -> dict:
        clean_name = name.strip()
        if len(clean_name) < 2:
            raise ValueError("Name must contain at least 2 characters.")
        if role not in {"teacher", "student"}:
            raise ValueError("Role must be teacher or student.")
        clean_email = validate_email(email)

        try:
            cursor = db.execute(
                """
                INSERT INTO users (name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    clean_name,
                    clean_email,
                    hash_password(password),
                    role,
                    _now_iso(),
                ),
            )
            db.commit()
        except sqlite3.IntegrityError as exc:
            db.rollback()
            raise ValueError("An account with this email already exists.") from exc

        row = db.execute(
            "SELECT id, name, email, role FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        user = public_user(row)
        return {"access_token": self.create_token(user), "user": user}

    def login(
        self,
        db: sqlite3.Connection,
        *,
        email: str,
        password: str,
    ) -> dict:
        row = db.execute(
            """
            SELECT id, name, email, role, password_hash
            FROM users
            WHERE email = ?
            """,
            (normalize_email(email),),
        ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            raise AuthenticationError("Invalid email or password.")

        user = public_user(row)
        return {"access_token": self.create_token(user), "user": user}

    def get_user(self, db: sqlite3.Connection, user_id: int) -> dict | None:
        row = db.execute(
            "SELECT id, name, email, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return public_user(row) if row else None

    def create_token(self, user: dict) -> str:
        payload = {
            "sub": str(user["id"]),
            "role": user["role"],
            "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        }
        payload_text = _encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = hmac.new(
            self.secret,
            payload_text.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload_text}.{signature}"

    def decode_token(self, token: str) -> int:
        try:
            payload_text, supplied_signature = token.split(".", 1)
            expected_signature = hmac.new(
                self.secret,
                payload_text.encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise AuthenticationError("Invalid or expired login token.")

            payload = json.loads(_decode(payload_text))
            user_id = int(payload["sub"])
            if int(payload["exp"]) < int(time.time()):
                raise AuthenticationError("Invalid or expired login token.")
            return user_id
        except AuthenticationError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AuthenticationError("Invalid or expired login token.") from exc
