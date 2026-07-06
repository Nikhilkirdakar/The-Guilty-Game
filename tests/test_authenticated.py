"""
Script 3 — Authenticated SIGN IN flow (optional, credential-gated).

These tests are SKIPPED by default. They run only when BOTH are true:
  * TGG_RUN_AUTH=true
  * TGG_USERNAME / TGG_PASSWORD are set (via .env or environment)

Setup:
  1. cp .env.example .env      # .env is git-ignored
  2. Fill TGG_USERNAME / TGG_PASSWORD with a DEDICATED test account.
  3. Set TGG_RUN_AUTH=true
  4. Verify the login selectors first:  python inspect_signin.py --show
     then pin them in pages/login_page.py.

Then:  pytest tests/test_authenticated.py -v
"""
import pytest

from config import credentials
from pages.game_page import GamePage
from pages.login_page import LoginPage, OAuthNotAutomatable, SignInBlocked

# Whole module skips unless explicitly enabled + credentials present.
pytestmark = [
    pytest.mark.functional,
    pytest.mark.skipif(
        not (credentials.RUN_AUTH and credentials.has_credentials()),
        reason="Auth tests disabled. Set TGG_RUN_AUTH=true and TGG_USERNAME/"
        "TGG_PASSWORD in .env to enable.",
    ),
]


@pytest.fixture
def landing(driver, base_url):
    page = GamePage(driver)
    page.load(base_url)
    return page


def test_sign_in_succeeds(landing, driver):
    """Sign in with the test account and confirm an authenticated state."""
    landing.click_sign_in()

    login = LoginPage(driver)
    try:
        login.sign_in(credentials.USERNAME, credentials.PASSWORD)
    except OAuthNotAutomatable as e:
        pytest.skip(f"Sign-in delegates to OAuth provider: {e}")
    except SignInBlocked as e:
        pytest.skip(f"Sign-in blocked by bot protection: {e}")

    assert login.is_logged_in(), "No authenticated signal after sign-in"


def test_resume_investigation_available_when_logged_in(landing, driver):
    """Logged-in users should see RESUME INVESTIGATION / an in-game entry."""
    landing.click_sign_in()

    login = LoginPage(driver)
    try:
        login.sign_in(credentials.USERNAME, credentials.PASSWORD)
    except OAuthNotAutomatable as e:
        pytest.skip(f"Sign-in delegates to OAuth provider: {e}")
    except SignInBlocked as e:
        pytest.skip(f"Sign-in blocked by bot protection: {e}")

    assert login.is_logged_in(), "Sign-in did not reach an authenticated state"

    # Back on the game surface, a game-entry CTA must be present.
    game = GamePage(driver)
    assert game.has_start_first_case() or game.has_play_free(), (
        "No game-entry CTA visible after authentication"
    )
