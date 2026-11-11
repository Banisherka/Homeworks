"""Выдаёт тестовый JWT для Postman/curl:  python scripts/make_token.py alice"""
import os
import sys
import time

import jwt

user = sys.argv[1] if len(sys.argv) > 1 else "alice"
print(jwt.encode({"sub": user, "exp": int(time.time()) + 3600},
                 os.getenv("JWT_SECRET", "dev-secret"), algorithm="HS256"))
