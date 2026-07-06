"""
GamePage: page object for theguiltygame.com.

Selectors below are pinned to the REAL rendered DOM (captured 2026-07-06 via
inspect_site.py). theguiltygame.com is a Vite/React single-page marketing site:
the landing page presents CTAs (SIGN IN / PLAY FREE / START FIRST CASE) that
lead into the game; there are no <a> links, <input> fields, or game board in
the landing DOM itself.

Observed buttons (class -> text):
    button.tg-brand                 "THE GUILTY ..."         (logo)
    button.tg-ghost                 "SIGN IN"
    button.tg-cut.clip-cut-corner   "PLAY FREE >"
    button[aria-label='Enter fullscreen']
    button.tg-cut.clip-cut-corner   "START FIRST CASE >"
    button.tg-cut.clip-cut-corner   "RESUME INVESTIGATION"
    button.tg-cut.clip-cut-corner   "TRY IT YOURSELF >"
    button.tg-cut.clip-cut-corner   "OPEN THE CASE FILE >"
    button.tg-cut.clip-cut-corner   "FIND OUT — PLAY FREE >"

Because the primary CTAs share the class `tg-cut clip-cut-corner`, we target
them by their (stable, human-readable) text via XPath.
"""
from selenium.webdriver.common.by import By

from config import settings
from pages.base_page import BasePage


def _btn_with_text(fragment: str):
    """Case-insensitive 'button whose text contains <fragment>' XPath locator."""
    frag = fragment.lower()
    return (
        By.XPATH,
        f"//button[contains(translate(normalize-space(.), "
        f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{frag}')]",
    )


class GamePage(BasePage):

    # ------------------------------------------------------------------ #
    # Locators (pinned to real DOM)
    # ------------------------------------------------------------------ #
    BRAND = (By.CSS_SELECTOR, "button.tg-brand")
    SIGN_IN = (By.CSS_SELECTOR, "button.tg-ghost")
    FULLSCREEN = (By.CSS_SELECTOR, "button[aria-label='Enter fullscreen']")

    HERO_HEADING = (By.CSS_SELECTOR, "h1.tg-h1")
    ALL_HEADINGS = (By.CSS_SELECTOR, "h1, h2, h3")
    PRIMARY_CTAS = (By.CSS_SELECTOR, "button.tg-cut")

    # Named CTAs (targeted by visible text — resilient to class churn)
    PLAY_FREE = _btn_with_text("play free")
    START_FIRST_CASE = _btn_with_text("start first case")
    RESUME = _btn_with_text("resume investigation")

    # The 4 "how it works" steps (h3 copy from the real page)
    STEP_HEADINGS = [
        "Read the room",
        "Interrogate the suspects",
        "Connect the motive",
        "File the accusation",
    ]

    # Cookie/consent banner (not observed on the live page, kept as a safety net)
    COOKIE_ACCEPT = (
        By.XPATH,
        "//button[contains(translate(., 'ACEPT', 'acept'), 'accept')]",
    )

    # ------------------------------------------------------------------ #
    # Load / setup
    # ------------------------------------------------------------------ #
    def load(self, url: str = None):
        self.open(url or settings.BASE_URL)
        self.wait_for_document_ready()
        self._wait_for_spa()
        self.accept_cookies_if_present()
        return self

    def _wait_for_spa(self):
        """Wait for the React app to hydrate the #root container."""
        self.wait.until(
            lambda d: d.execute_script(
                "return !!document.querySelector('#root') "
                "&& document.querySelector('#root').children.length > 0"
            ),
            message="SPA (#root) never hydrated",
        )
        # Hero heading is the first meaningful content element.
        self.find_visible(self.HERO_HEADING)
        return self

    def accept_cookies_if_present(self):
        if self.is_visible(self.COOKIE_ACCEPT, timeout=2):
            self.click(self.COOKIE_ACCEPT)
        return self

    # ------------------------------------------------------------------ #
    # Landing-page queries
    # ------------------------------------------------------------------ #
    def is_loaded(self) -> bool:
        return self.is_visible(self.HERO_HEADING, timeout=self.timeout)

    def hero_text(self) -> str:
        return self.get_text(self.HERO_HEADING)

    def cta_texts(self) -> list:
        """Return the text of every primary CTA button on the page."""
        return [el.text.strip() for el in self.find_all(self.PRIMARY_CTAS)]

    def heading_texts(self) -> list:
        return [el.text.strip() for el in self.find_all(self.ALL_HEADINGS) if el.text.strip()]

    def has_sign_in(self) -> bool:
        return self.is_visible(self.SIGN_IN, timeout=5)

    def has_play_free(self) -> bool:
        return self.is_visible(self.PLAY_FREE, timeout=5)

    def has_start_first_case(self) -> bool:
        return self.is_visible(self.START_FIRST_CASE, timeout=5)

    def all_steps_present(self) -> bool:
        # The 4 step h3s are lazy-mounted AND unmounted as they scroll in/out,
        # so capture each one the instant it appears during a full scroll.
        found = self.texts_present_while_scrolling(self.STEP_HEADINGS)
        return len(found) == len(self.STEP_HEADINGS)

    def found_steps(self) -> list:
        """Diagnostic: which steps were actually seen while scrolling."""
        return sorted(self.texts_present_while_scrolling(self.STEP_HEADINGS))

    # ------------------------------------------------------------------ #
    # Interactions / navigation
    # ------------------------------------------------------------------ #
    def dom_signature(self) -> dict:
        """A lightweight fingerprint of current page state, for change detection."""
        return self.driver.execute_script(
            """
            return {
              url: location.href,
              buttons: document.querySelectorAll('button').length,
              inputs: document.querySelectorAll('input,textarea,select').length,
              bodyLen: (document.body.innerText || '').length,
              dialogs: document.querySelectorAll('[role=dialog],.modal,dialog').length
            };
            """
        )

    def click_sign_in(self):
        self.click(self.SIGN_IN)
        return self

    def start_game(self):
        """Click the primary game-entry CTA (START FIRST CASE, else PLAY FREE)."""
        if self.is_visible(self.START_FIRST_CASE, timeout=5):
            self.click(self.START_FIRST_CASE)
        else:
            self.click(self.PLAY_FREE)
        return self

    def state_changed_since(self, before: dict, timeout: int = 10) -> bool:
        """True if clicking produced any observable transition vs `before`.

        A transition = URL change, a dialog/modal opening, new input fields
        appearing, or a substantial change in button count / body length.
        """
        def _changed(_):
            now = self.dom_signature()
            return (
                now["url"] != before["url"]
                or now["dialogs"] > before["dialogs"]
                or now["inputs"] > before["inputs"]
                or now["buttons"] != before["buttons"]
                or abs(now["bodyLen"] - before["bodyLen"]) > 40
            )

        try:
            self._wait(timeout).until(_changed)
            return True
        except Exception:
            return False
