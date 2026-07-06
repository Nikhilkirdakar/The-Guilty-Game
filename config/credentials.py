"""
Credential loader — reads test-account secrets from environment / .env.

SECURITY: credentials are NEVER hardcoded or committed. Put them in a local
`.env` file (git-ignored) or export them as environment variables:

    TGG_USERNAME=your-test-account@example.com
    TGG_PASSWORD=your-password

Use a DEDICATED throwaway test account — never a personal account.
"""
import os

# Load a local .env if python-dotenv is installed (optional dependency).
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from the current working directory if present
except Exception:
    pass

USERNAME = os.getenv("TGG_USERNAME", "").strip()
PASSWORD = os.getenv("TGG_PASSWORD", "").strip()

# Gate for actually running auth tests (skips by default so CI stays green
# until a test account + verified selectors are in place).
RUN_AUTH = os.getenv("TGG_RUN_AUTH", "false").lower() == "true"


def has_credentials() -> bool:
    return bool(USERNAME and PASSWORD)
