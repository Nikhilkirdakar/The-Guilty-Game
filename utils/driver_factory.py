"""
WebDriver factory.

Centralises all browser-launch logic so conftest.py stays thin and adding a
new browser is a single function edit. Uses Selenium Manager (built into
Selenium >= 4.6) to resolve drivers automatically — no manual chromedriver
downloads, no webdriver-manager required.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)


def _common_chromium_flags(options):
    """Flags shared by Chrome and Edge (both Chromium-based)."""
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--window-size={settings.WINDOW_SIZE}")
    # Reduce noise & flakiness in CI
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    return options


def create_driver(browser: str = None, headless: bool = None, locale_lang: str = None):
    """Build and return a configured WebDriver instance.

    Args:
        browser:      "chrome" | "firefox" | "edge" (defaults from settings)
        headless:     force headless on/off (defaults from settings)
        locale_lang:  ISO language (e.g. "de") to set as the browser's
                      Accept-Language / UI locale. This makes locale tests
                      exercise the real browser-negotiated language, not just
                      the URL parameter.
    """
    browser = (browser or settings.DEFAULT_BROWSER).lower()
    headless = settings.DEFAULT_HEADLESS if headless is None else headless

    log.info("Launching %s (headless=%s, locale=%s)", browser, headless, locale_lang)

    if browser == "chrome":
        options = _common_chromium_flags(ChromeOptions())
        if headless:
            options.add_argument("--headless=new")
        if locale_lang:
            options.add_argument(f"--lang={locale_lang}")
            options.add_experimental_option(
                "prefs", {"intl.accept_languages": locale_lang}
            )
        driver = webdriver.Chrome(options=options)

    elif browser == "edge":
        options = _common_chromium_flags(EdgeOptions())
        if headless:
            options.add_argument("--headless=new")
        if locale_lang:
            options.add_argument(f"--lang={locale_lang}")
        driver = webdriver.Edge(options=options)

    elif browser == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("-headless")
        w, h = settings.WINDOW_SIZE.split(",")
        options.add_argument(f"--width={w}")
        options.add_argument(f"--height={h}")
        if locale_lang:
            options.set_preference("intl.accept_languages", locale_lang)
        driver = webdriver.Firefox(options=options)

    else:
        raise ValueError(f"Unsupported browser: {browser!r}")

    driver.set_page_load_timeout(settings.PAGE_LOAD_TIMEOUT)
    if browser == "firefox":  # Chromium size is set via flag; Firefox via API
        driver.maximize_window()
    return driver
