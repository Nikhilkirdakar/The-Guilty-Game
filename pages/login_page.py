"""
LoginPage — the SIGN IN flow (Clerk email/password, rendered inline).

theguiltygame.com uses Clerk (https://clerk.com) for auth, rendered directly on
the page (no iframe, no OAuth redirect — the URL stays on theguiltygame.com), so
the native email/password form is automatable. Selectors below are pinned to the
real Clerk DOM captured 2026-07-06 via inspect_signin.py:

    email    -> input#identifier-field   (name='identifier', type='text')
    password -> input#password-field     (name='password',   type='password')
    submit   -> button.cl-formButtonPrimary  ("VERIFY IDENTITY")

Notes:
  * A "Continue with Google" social button also exists — we intentionally use
    the native form instead (Google OAuth can't be UI-automated).
  * Clerk PRODUCTION instances may enable bot protection (Cloudflare Turnstile).
    If a challenge appears, `sign_in()` raises SignInBlocked so the test skips
    with a clear reason rather than hanging or silently failing.
"""
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from pages.game_page import GamePage
from utils.logger import get_logger

log = get_logger(__name__)


class OAuthNotAutomatable(Exception):
    """Raised when SIGN IN delegates to a 3rd-party OAuth provider."""


class SignInBlocked(Exception):
    """Raised when a bot-protection challenge (e.g. Turnstile) blocks sign-in."""


class LoginPage(BasePage):

    # --- Clerk form fields (primary = real selectors, then generic fallbacks) ---
    EMAIL = [
        (By.CSS_SELECTOR, "#identifier-field"),
        (By.CSS_SELECTOR, "input[name='identifier']"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[placeholder*='mail' i]"),
    ]
    PASSWORD = [
        (By.CSS_SELECTOR, "#password-field"),
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]
    # Clerk email-first flow sometimes shows a "Continue" before the password.
    CONTINUE = [
        (By.CSS_SELECTOR, "button.cl-formButtonPrimary"),
        (By.CSS_SELECTOR, "form button[type='submit']"),
    ]
    SUBMIT = [
        (By.CSS_SELECTOR, "button.cl-formButtonPrimary"),
        (By.CSS_SELECTOR, "form button[type='submit']"),
        (By.XPATH, "//button[contains(translate(., 'VERIFYIDENT', 'verifyident'), 'verify identity')]"),
        (By.XPATH, "//button[contains(translate(., 'SIGNLOGCTUE', 'signlogctue'), 'sign in')]"),
    ]

    # Authenticated signals: Clerk user button OR in-game CTA OR sign-out.
    LOGGED_IN_SIGNALS = [
        (By.CSS_SELECTOR, ".cl-userButtonBox, .cl-userButtonTrigger, .cl-avatarBox"),
        (By.XPATH, "//button[contains(translate(., 'RESUME', 'resume'), 'resume')]"),
        (By.XPATH, "//button[contains(translate(., 'SIGNOUTLG', 'signoutlg'), 'sign out')]"),
    ]

    # Clerk surfaces field/form errors here.
    ERROR = (By.CSS_SELECTOR, ".cl-formFieldErrorText, .cl-formFieldError, [data-feedback='error']")
    # Bot-protection challenge (Cloudflare Turnstile) rendered by Clerk.
    CAPTCHA = (By.CSS_SELECTOR, "#clerk-captcha, .cl-captcha, iframe[src*='challenges.cloudflare.com']")

    OAUTH_HOSTS = ("accounts.google.com", "facebook.com", "appleid.apple.com",
                   "login.microsoftonline.com")

    def sign_in(self, username: str, password: str) -> "GamePage":
        """Complete the Clerk email/password form. Caller must have already
        clicked SIGN IN (so the form is visible). Returns a fresh GamePage."""
        # If somehow we ended up on a real OAuth provider domain, bail.
        if any(host in self.current_url for host in self.OAUTH_HOSTS):
            raise OAuthNotAutomatable(f"SIGN IN left the site: {self.current_url}")

        self._focus_window_with_form()

        email_el = self.find_first_available(self.EMAIL, timeout=20)
        email_el.clear()
        email_el.send_keys(username)

        # Password may already be visible (single-step) or gated behind Continue.
        if not self._password_visible(timeout=3):
            try:
                self.find_first_available(self.CONTINUE, timeout=5).click()
            except Exception:
                pass  # single-step form; ignore

        pwd_el = self.find_first_available(self.PASSWORD, timeout=20)
        pwd_el.clear()
        pwd_el.send_keys(password)

        self._raise_if_blocked()

        self.find_first_available(self.SUBMIT, timeout=10).click()

        # Give Clerk a moment, then surface an inline error if the creds failed.
        if self.is_visible(self.ERROR, timeout=5):
            raise AssertionError(f"Clerk reported a sign-in error: {self.get_text(self.ERROR)}")

        return GamePage(self.driver)

    def is_logged_in(self, timeout: int = 20) -> bool:
        try:
            self.find_first_available(self.LOGGED_IN_SIGNALS, timeout=timeout)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _password_visible(self, timeout: int = 3) -> bool:
        return any(self.is_present(loc, timeout=1) for loc in self.PASSWORD[:2]) or \
            self.is_present(self.PASSWORD[-1], timeout=timeout)

    def _raise_if_blocked(self):
        if self.is_present(self.CAPTCHA, timeout=2):
            raise SignInBlocked(
                "Clerk bot-protection challenge (Cloudflare Turnstile) detected; "
                "UI automation cannot pass it. Use a Clerk development instance "
                "with a +clerk_test account, or session-cookie injection."
            )

    def _focus_window_with_form(self):
        """Clicking SIGN IN can open a second window/tab; switch to whichever
        window actually contains the identifier field."""
        handles = self.driver.window_handles
        if len(handles) <= 1:
            return
        current = self.driver.current_window_handle
        for h in handles:
            self.driver.switch_to.window(h)
            if self.is_present(self.EMAIL[0], timeout=2):
                return
        self.driver.switch_to.window(current)
