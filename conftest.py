"""
Global pytest configuration & fixtures.

Responsibilities:
  * Register CLI options (--browser, --headless, --base-url).
  * Provide the WebDriver fixture with guaranteed teardown.
  * Capture a screenshot on ANY test failure and embed it in the
    pytest-html report (plus save a file copy to reports/screenshots).
"""
import base64
import os

import pytest

from config import settings
from utils.driver_factory import create_driver
from utils.logger import get_logger

log = get_logger("conftest")


# --------------------------------------------------------------------------- #
# CLI options
# --------------------------------------------------------------------------- #
def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="store",
        default=settings.DEFAULT_BROWSER,
        help="Browser to run against: chrome | firefox | edge",
    )
    parser.addoption(
        "--headless",
        action="store",
        default=str(settings.DEFAULT_HEADLESS).lower(),
        help="Run headless: true | false",
    )
    parser.addoption(
        "--base-url",
        action="store",
        default=settings.BASE_URL,
        help="Base URL of the application under test",
    )


# --------------------------------------------------------------------------- #
# Session-scoped resolved config
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def browser_name(request):
    return request.config.getoption("--browser")


@pytest.fixture(scope="session")
def headless(request):
    return str(request.config.getoption("--headless")).lower() == "true"


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url")


# --------------------------------------------------------------------------- #
# WebDriver fixture (function-scoped: fresh browser per test = isolation)
# --------------------------------------------------------------------------- #
@pytest.fixture
def driver(request, browser_name, headless):
    """Create a WebDriver, expose it, and always quit it afterwards.

    A per-test `locale_lang` can be injected via indirect parametrization or
    by setting `request.node._locale_lang` before the fixture resolves
    (localization tests use the dedicated `localized_game` fixture instead).
    """
    locale_lang = getattr(request.node, "_locale_lang", None)
    drv = create_driver(browser=browser_name, headless=headless, locale_lang=locale_lang)
    # Stash on the node so the failure hook can grab it for a screenshot.
    request.node._driver = drv
    yield drv
    drv.quit()


@pytest.fixture
def game_page(driver, base_url):
    """Convenience fixture returning a loaded GamePage."""
    from pages.game_page import GamePage
    page = GamePage(driver)
    page.load(base_url)
    return page


# --------------------------------------------------------------------------- #
# Screenshot-on-failure -> embed in pytest-html
# --------------------------------------------------------------------------- #
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach screenshots to the pytest-html report.

    * Always embeds any per-locale screenshots captured during setup
      (item._embed_images: list of (name, base64_png)).
    * On failure, additionally captures & embeds a failure screenshot.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    pytest_html = item.config.pluginmanager.getplugin("html")
    extras = getattr(report, "extras", [])

    # 1. Locale evidence screenshots (attached for pass AND fail).
    for name, b64 in (getattr(item, "_embed_images", None) or []):
        if pytest_html:
            extras.append(pytest_html.extras.image(b64, name=name, mime_type="image/png"))

    # 2. Failure screenshot.
    if report.failed:
        driver = getattr(item, "_driver", None)
        if driver is not None:
            os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
            file_path = os.path.join(settings.SCREENSHOTS_DIR, f"FAIL_{item.name}.png")
            try:
                driver.save_screenshot(file_path)
                png_b64 = driver.get_screenshot_as_base64()
                if pytest_html:
                    extras.append(pytest_html.extras.image(png_b64, name="FAILURE", mime_type="image/png"))
                    extras.append(pytest_html.extras.url(driver.current_url, name="Failing URL"))
                log.info("Embedded failure screenshot for %s", item.name)
            except Exception as e:  # pragma: no cover
                log.error("Could not capture/embed failure screenshot: %s", e)

    if pytest_html and extras:
        report.extras = extras


# --------------------------------------------------------------------------- #
# HTML report metadata / title
# --------------------------------------------------------------------------- #
def pytest_html_report_title(report):
    report.title = "The Guilty Game — Selenium/Pytest Automation Report"


def pytest_sessionfinish(session, exitstatus):
    """After the run, (re)build the per-locale screenshot gallery if any
    locale screenshots were captured this session."""
    # xdist worker processes shouldn't each build it — only the controller.
    if getattr(session.config, "workerinput", None) is not None:
        return
    try:
        from utils.generate_gallery import generate_gallery
        path = generate_gallery()
        if path:
            log.info("Locale screenshot gallery: %s", path)
    except Exception as e:  # never fail the session over reporting
        log.error("Gallery generation failed: %s", e)


def pytest_configure(config):
    # Marker registration (also declared in pytest.ini for redundancy).
    config.addinivalue_line("markers", "p0: launch-blocking priority tests")
    config.addinivalue_line("markers", "p1: important priority tests")
    config.addinivalue_line("markers", "functional: end-to-end functional flow")
    config.addinivalue_line("markers", "localization: i18n / locale coverage")
    config.addinivalue_line("markers", "smoke: fast sanity checks")
