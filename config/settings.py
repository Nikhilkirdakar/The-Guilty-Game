"""
Central configuration for the framework.

Values here can be overridden at runtime via environment variables or
pytest CLI options (see conftest.py). Keeping them in one place means a
single edit propagates everywhere.
"""
import os

# ---------------------------------------------------------------------------
# Application under test
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("TGG_BASE_URL", "https://theguiltygame.com/")

# Expected substring in the <title> on a healthy home page load.
# VERIFY: open the site, check the real <title> text and tighten this.
EXPECTED_TITLE_SUBSTRING = os.getenv("TGG_TITLE", "Guilty")

# ---------------------------------------------------------------------------
# Timeouts (seconds)
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT = int(os.getenv("TGG_TIMEOUT", "15"))
PAGE_LOAD_TIMEOUT = int(os.getenv("TGG_PAGE_LOAD_TIMEOUT", "30"))
POLL_FREQUENCY = float(os.getenv("TGG_POLL", "0.5"))

# ---------------------------------------------------------------------------
# Browser defaults (overridable from CLI: --browser / --headless)
# ---------------------------------------------------------------------------
DEFAULT_BROWSER = os.getenv("TGG_BROWSER", "chrome")   # chrome | firefox | edge
DEFAULT_HEADLESS = os.getenv("TGG_HEADLESS", "true").lower() == "true"
WINDOW_SIZE = os.getenv("TGG_WINDOW_SIZE", "1920,1080")

# ---------------------------------------------------------------------------
# Artifact locations
# ---------------------------------------------------------------------------
REPORTS_DIR = os.getenv("TGG_REPORTS_DIR", "reports")
SCREENSHOTS_DIR = os.path.join(REPORTS_DIR, "screenshots")
