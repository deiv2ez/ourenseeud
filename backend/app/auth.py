"""
auth.py — Autenticación con usuario+contrasinal por persoa e rol admin.

Deseño:
  - Usuarios gardados en data/users.json con contrasinal HASHEADO (bcrypt), nunca
    en texto plano.
  - Login devolve un token JWT que o frontend garda e envía en cada petición.
  - Rol "admin" (o usuario "david") pode acceder a endpoints de xestión (rumores,
    fichaxes, axuste de datos). Rol "user" só le.
  - A clave de asinado do JWT vén de variable de entorno JWT_SECRET.

IMPORTANTE: este módulo dá a MECÁNICA. Os usuarios reais créanse co script
create_user (nunca se hardcodean contrasinais no código).
"""

from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from jose import jwt, JWTError

USERS_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-CAMBIAR-en-producion")
JWT_ALGO = "HS256"
TOKEN_HOURS = 72


def _hash_password(password: str) -> str:
    # bcrypt limita a 72 bytes; truncamos de forma segura antes de hashear.
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, hashed: str) -> bool:
    pw = password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------- almacenamento ----
def _load_users() -> dict:
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_users(users: dict) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


# ----------------------------------------------------------- xestión --------
def create_user(username: str, password: str, role: str = "user") -> None:
    """Crea (ou actualiza) un usuario co contrasinal hasheado."""
    users = _load_users()
    users[username.lower()] = {
        "username": username.lower(),
        "hash": _hash_password(password),
        "role": role,  # "admin" | "user"
    }
    _save_users(users)


def verify_login(username: str, password: str) -> dict | None:
    """Comproba credenciais. Devolve o usuario (sen hash) se son válidas."""
    users = _load_users()
    u = users.get(username.lower())
    if not u or not _check_password(password, u["hash"]):
        return None
    return {"username": u["username"], "role": u["role"]}


# --------------------------------------------------------------- tokens -----
def make_token(user: dict) -> str:
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"username": payload["sub"], "role": payload.get("role", "user")}
    except JWTError:
        return None


if __name__ == "__main__":
    # Utilidade rápida: crear usuarios desde liña de comandos.
    #   python -m app.auth create david <contrasinal> admin
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "create":
        role = sys.argv[4] if len(sys.argv) > 4 else "user"
        create_user(sys.argv[2], sys.argv[3], role)
        print(f"Usuario '{sys.argv[2]}' creado con rol {role}.")
    else:
        print("Uso: python -m app.auth create <usuario> <contrasinal> [admin|user]")
