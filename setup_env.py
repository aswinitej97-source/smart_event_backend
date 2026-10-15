from pathlib import Path
import secrets

from dotenv import dotenv_values

path = Path(".env")

existing = path.read_text() if path.exists() else ""
values = dotenv_values(path) if path.exists() else {}

if len(values.get("SECRET_KEY") or "") < 32:
    existing += (
        "\nSECRET_KEY="
        + secrets.token_urlsafe(48)
        + "\n"
    )

if not values.get("DATABASE_URL"):
    existing += (
        "\nDATABASE_URL=sqlite:///./smartevent.db\n"
    )

if not values.get("FRONTEND_ORIGINS"):
    existing += (
        "\nFRONTEND_ORIGINS="
        "http://localhost:5173,"
        "http://127.0.0.1:5173\n"
    )

path.write_text(existing)

print("Environment configured successfully.")