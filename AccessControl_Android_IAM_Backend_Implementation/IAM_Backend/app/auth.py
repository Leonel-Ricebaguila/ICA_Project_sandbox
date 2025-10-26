import time, jwt, os
from passlib.hash import argon2
from .config import cfg
import pyotp

def hash_password(password: str) -> str:
    return argon2.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return argon2.verify(password, hashed)
    except Exception:
        return False

def create_jwt(payload: dict, exp_seconds: int = None) -> str:
    exp = int(time.time()) + (exp_seconds or cfg.JWT_EXP_SECONDS)
    payload2 = payload.copy()
    payload2.update({"exp": exp})
    return jwt.encode(payload2, cfg.SECRET_KEY, algorithm="HS256")

def verify_jwt(token: str) -> dict:
    return jwt.decode(token, cfg.SECRET_KEY, algorithms=["HS256"])

def create_totp_secret() -> str:
    return pyotp.random_base32()

def verify_totp(secret, code) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
