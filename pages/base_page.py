"""
BasePage: the reusable foundation every page object inherits.

Wraps raw Selenium calls in explicit-wait-backed, self-documenting methods so
individual page objects never call WebDriverWait/find_element directly. This is
what keeps the POM layer clean and the tests readable.
"""
import base64
import os
import time

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)


class BasePage:
    def __init__(self, driver, timeout: int = None):
        self.driver = driver
        self.timeout = timeout or settings.DEFAULT_TIMEOUT
        self.wait = WebDriverWait(
            driver,
            self.timeout,
            poll_frequency=settings.POLL_FREQUENCY,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def open(self, url: str):
        log.info("GET %s", url)
        self.driver.get(url)
        return self

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    @property
    def title(self) -> str:
        return self.driver.title

    # ------------------------------------------------------------------ #
    # Core element helpers — all explicit-wait backed
    # ------------------------------------------------------------------ #
    def find(self, locator, timeout: int = None):
        """Wait for presence in DOM and return the element."""
        return self._wait(timeout).until(
            EC.presence_of_element_located(locator),
            message=f"Element not present: {locator}",
        )

    def find_visible(self, locator, timeout: int = None):
        """Wait for the element to be visible and return it."""
        return self._wait(timeout).until(
            EC.visibility_of_element_located(locator),
            message=f"Element not visible: {locator}",
        )

    def find_all(self, locator, timeout: int = None):
        """Wait for at least one match, return the full list."""
        return self._wait(timeout).until(
            EC.presence_of_all_elements_located(locator),
            message=f"No elements found: {locator}",
        )

    def find_first_available(self, locators, timeout: int = None):
        """Try a list of candidate locators, return the first that resolves.

        This is the resilience escape hatch: give a primary selector plus
        fallbacks and the framework survives minor DOM changes.
        """
        last_err = None
        # Short per-candidate timeout so we cycle through them quickly.
        per = max(2, (timeout or self.timeout) // max(1, len(locators)))
        for loc in locators:
            try:
                return self.find_visible(loc, timeout=per)
            except TimeoutException as e:
                last_err = e
                log.debug("Fallback: %s not found, trying next", loc)
        raise TimeoutException(
            f"None of the candidate locators matched: {locators}"
        ) from last_err

    # ------------------------------------------------------------------ #
    # Interactions
    # ------------------------------------------------------------------ #
    def click(self, locator, timeout: int = None):
        """Wait until clickable, then click — with a JS-click fallback for
        the classic 'element click intercepted' overlay problem."""
        el = self._wait(timeout).until(
            EC.element_to_be_clickable(locator),
            message=f"Element not clickable: {locator}",
        )
        try:
            el.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            log.warning("Native click failed on %s, retrying via JS", locator)
            self.scroll_into_view(el)
            self.driver.execute_script("arguments[0].click();", el)
        return self

    def type(self, locator, text: str, clear: bool = True, timeout: int = None):
        el = self.find_visible(locator, timeout)
        if clear:
            el.clear()
        el.send_keys(text)
        return self

    def get_text(self, locator, timeout: int = None) -> str:
        return self.find_visible(locator, timeout).text.strip()

    def get_attribute(self, locator, name: str, timeout: int = None) -> str:
        return self.find(locator, timeout).get_attribute(name)

    def scroll_into_view(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        return self

    def scroll_through_page(self, steps: int = 10, pause: float = 0.3):
        """Scroll top->bottom in increments to trigger lazy-mounted / animated
        content (IntersectionObserver reveals), then return to the top.

        Many marketing SPAs (incl. theguiltygame.com) only mount lower sections
        once they scroll into view, so tests must scroll before asserting on them.
        """
        height = self.driver.execute_script("return document.body.scrollHeight") or 0
        for i in range(1, steps + 1):
            self.driver.execute_script(f"window.scrollTo(0, {int(height * i / steps)});")
            time.sleep(pause)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(pause)
        return self

    def texts_present_while_scrolling(self, texts, positions: int = 14, pause: float = 0.25):
        """Return the subset of `texts` found in the rendered DOM at ANY point
        during a top->bottom scroll.

        Robust to sections that are BOTH lazy-mounted on scroll-in AND
        unmounted on scroll-away (common with scroll-animation libraries):
        each target is captured the instant it appears, so we never miss one
        just because it later unmounts.
        """
        found = set()
        targets = {t: t.lower() for t in texts}
        height = self.driver.execute_script("return document.body.scrollHeight") or 0
        for i in range(positions + 1):
            self.driver.execute_script(f"window.scrollTo(0, {int(height * i / positions)});")
            time.sleep(pause)
            src = self.driver.page_source.lower()
            for original, low in targets.items():
                if low in src:
                    found.add(original)
            if len(found) == len(targets):
                break
        self.driver.execute_script("window.scrollTo(0, 0);")
        return found

    # ------------------------------------------------------------------ #
    # State queries (never throw — return booleans)
    # ------------------------------------------------------------------ #
    def is_visible(self, locator, timeout: int = None) -> bool:
        try:
            self.find_visible(locator, timeout or 5)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_present(self, locator, timeout: int = None) -> bool:
        try:
            self.find(locator, timeout or 5)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def wait_for_url_contains(self, fragment: str, timeout: int = None) -> bool:
        return self._wait(timeout).until(
            EC.url_contains(fragment),
            message=f"URL never contained {fragment!r}: {self.current_url}",
        )

    def wait_for_document_ready(self, timeout: int = None):
        """Block until document.readyState == 'complete'."""
        self._wait(timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return self

    # ------------------------------------------------------------------ #
    # Localization helpers
    # ------------------------------------------------------------------ #
    def html_lang(self) -> str:
        """Return the <html lang="..."> attribute (primary subtag, lowercased)."""
        lang = self.driver.execute_script(
            "return document.documentElement.lang || '';"
        )
        return (lang or "").split("-")[0].lower()

    def visible_body_text(self) -> str:
        return self.driver.execute_script("return document.body.innerText || '';")

    def count_broken_images(self) -> int:
        """Return how many <img> failed to load (naturalWidth == 0).

        Used by localization tests to assert assets aren't broken per-locale.
        """
        return self.driver.execute_script(
            """
            const imgs = Array.from(document.images);
            return imgs.filter(i => i.complete && i.naturalWidth === 0).length;
            """
        )

    # ------------------------------------------------------------------ #
    # Screenshots
    # ------------------------------------------------------------------ #
    def take_screenshot(self, name: str) -> str:
        """Save a viewport screenshot under reports/screenshots and return path."""
        os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        path = os.path.join(settings.SCREENSHOTS_DIR, f"{safe}_{int(time.time())}.png")
        try:
            self.driver.save_screenshot(path)
            log.info("Screenshot saved: %s", path)
        except Exception as e:  # never let screenshotting break a test run
            log.error("Failed to save screenshot: %s", e)
            return ""
        return path

    def save_full_page_screenshot(self, path: str) -> str:
        """Capture the ENTIRE page (beyond the viewport) to `path`.

        Uses Firefox's native full-page API when available, else Chromium's
        DevTools Protocol (captureBeyondViewport), falling back to a plain
        viewport screenshot. Full-resolution — never downscaled.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        # Firefox: built-in full-page screenshot
        if hasattr(self.driver, "save_full_page_screenshot"):
            try:
                self.driver.save_full_page_screenshot(path)
                return path
            except Exception:
                pass

        # Chromium (Chrome/Edge): CDP full-page capture
        try:
            result = self.driver.execute_cdp_cmd(
                "Page.captureScreenshot",
                {"format": "png", "captureBeyondViewport": True, "fromSurface": True},
            )
            with open(path, "wb") as f:
                f.write(base64.b64decode(result["data"]))
            return path
        except Exception:
            pass

        # Last resort: viewport only
        try:
            self.driver.save_screenshot(path)
        except Exception as e:
            log.error("Full-page screenshot failed: %s", e)
            return ""
        return path

    def capture_scrolling_screenshots(self, out_dir: str, prefix: str,
                                      positions: int = 6, pause: float = 0.4) -> list:
        """Capture a series of full-resolution viewport screenshots while
        scrolling top->bottom.

        This is the reliable way to document a page whose sections are
        lazy-mounted on scroll-in (and unmounted on scroll-away) — a single
        full-page shot would miss those. Returns the list of saved file paths.
        """
        os.makedirs(out_dir, exist_ok=True)
        paths = []
        height = self.driver.execute_script("return document.body.scrollHeight") or 0
        vh = self.driver.execute_script("return window.innerHeight") or 900
        n = max(positions, 1)

        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(pause)
        for i in range(n):
            y = int((height - vh) * i / max(n - 1, 1)) if height > vh else 0
            self.driver.execute_script(f"window.scrollTo(0, {y});")
            time.sleep(pause)
            p = os.path.join(out_dir, f"{prefix}_{i + 1:02d}.png")
            try:
                self.driver.save_screenshot(p)
                paths.append(p)
            except Exception as e:
                log.error("Screenshot %s failed: %s", p, e)
        self.driver.execute_script("window.scrollTo(0, 0);")
        return paths

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _wait(self, timeout: int = None) -> WebDriverWait:
        if timeout is None:
            return self.wait
        return WebDriverWait(
            self.driver,
            timeout,
            poll_frequency=settings.POLL_FREQUENCY,
            ignored_exceptions=(StaleElementReferenceException,),
        )
