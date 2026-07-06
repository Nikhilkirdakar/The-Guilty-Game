"""
Script 2 — Comprehensive localization (i18n) testing.

Data-driven across 24 locales via @pytest.mark.parametrize, split into P0
(launch-blocking) and P1 (important) tiers using pytest markers.

REALITY CHECK (captured 2026-07-06 via inspect_site.py)
-------------------------------------------------------
theguiltygame.com currently ships **English only**: <html lang="en">, all copy
is English, and there is no language switcher (only a SIGN IN button). Passing
`?hl=<locale>` does not change the content.

Therefore the suite is structured as:
  * HARD assertions (must pass) — per the brief's "...OR that the application
    loads without broken assets under these locales": each localized URL loads
    healthily, renders the hero + key CTA, and has no broken assets. This is
    genuinely valuable: it proves a locale query param doesn't break rendering.
  * DOCUMENTED GAP — a dedicated xfail test asserts that UI text changes per
    locale. It is expected to fail today and will start passing (xpass) the
    moment the site adds real localization — turning the suite into a live
    i18n readiness monitor.

Flip `strict=True` on the xfail marker once i18n is expected to be live, so a
regression (i18n removed) fails the build.
"""
import base64
import os

import pytest

from config import settings
from config.locales import P0_LOCALES, P1_LOCALES, build_localized_url
from pages.game_page import GamePage
from utils.driver_factory import create_driver
from utils.logger import get_logger

log = get_logger("test_localization")


def _capture_locale_screenshots(page: GamePage, locale) -> list:
    """Capture per-locale screenshots into reports/screenshots/<code>/ and
    return [(display_name, base64_png), ...] for embedding in the HTML report.

    Full-resolution, never downscaled. Organized in one folder per locale.
    """
    code = locale["code"]
    out_dir = os.path.join(settings.SCREENSHOTS_DIR, code)

    # A scrolling series (captures lazy-mounted sections) ...
    series = page.capture_scrolling_screenshots(out_dir, f"{code}_landing", positions=6)
    # ... plus one stitched full-page shot.
    full = page.save_full_page_screenshot(os.path.join(out_dir, f"{code}_full.png"))

    log.info("[%s] captured %d screenshots in %s", code, len(series) + bool(full), out_dir)

    # Embed the full page + the first (hero) frame in the report.
    embeds = []
    for path in ([full] + series[:1]):
        if not path:
            continue
        try:
            with open(path, "rb") as f:
                embeds.append((f"{code}: {os.path.basename(path)}",
                               base64.b64encode(f.read()).decode()))
        except Exception:
            pass
    return embeds


# --------------------------------------------------------------------------- #
# Session baseline: default (English) rendered body text, captured once.
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def english_baseline(browser_name, headless, base_url):
    drv = create_driver(browser=browser_name, headless=headless, locale_lang="en")
    try:
        page = GamePage(drv)
        page.load(base_url)
        return {
            "body_text": page.visible_body_text().strip(),
            "html_lang": page.html_lang(),
        }
    finally:
        drv.quit()


# --------------------------------------------------------------------------- #
# Per-locale driver: fresh browser launched WITH that locale's Accept-Language,
# loading the locale-routed URL. Guaranteed teardown.
# --------------------------------------------------------------------------- #
@pytest.fixture
def localized_game(request, browser_name, headless, base_url):
    locale = request.param
    drv = create_driver(browser=browser_name, headless=headless, locale_lang=locale["lang"])
    request.node._driver = drv  # for the failure-screenshot hook
    try:
        page = GamePage(drv)
        page.load(build_localized_url(base_url, locale))
        # Collect per-locale screenshots right after switching locale, and
        # stash them so the report hook embeds them (pass or fail).
        request.node._embed_images = _capture_locale_screenshots(page, locale)
        yield page, locale
    finally:
        drv.quit()


def _assert_locale_healthy(page: GamePage, locale):
    """HARD checks that must pass for every locale (robustness of locale routing)."""
    code = locale["code"]

    # 1. Landing rendered (SPA hydrated + hero visible) — no blank/crashed page.
    assert page.is_loaded(), f"[{code}] Landing did not render under this locale"

    # 2. Title non-empty ('page didn't die' guard).
    assert page.title, f"[{code}] Page title empty under this locale"

    # 3. Key game-entry CTA still present (core UX intact regardless of locale).
    assert page.has_play_free() or page.has_start_first_case(), (
        f"[{code}] No primary CTA (PLAY FREE / START FIRST CASE) under this locale"
    )

    # 4. No broken assets under this locale.
    broken = page.count_broken_images()
    assert broken == 0, f"[{code}] {broken} broken image(s) under this locale"


# --------------------------------------------------------------------------- #
# P0 — launch-blocking locales : health / robustness (HARD, should pass)
# --------------------------------------------------------------------------- #
@pytest.mark.localization
@pytest.mark.p0
@pytest.mark.parametrize(
    "localized_game", P0_LOCALES, ids=[l["code"] for l in P0_LOCALES], indirect=True
)
def test_localization_p0_loads_cleanly(localized_game):
    page, locale = localized_game
    _assert_locale_healthy(page, locale)


# --------------------------------------------------------------------------- #
# P1 — important locales : health / robustness (HARD, should pass)
# --------------------------------------------------------------------------- #
@pytest.mark.localization
@pytest.mark.p1
@pytest.mark.parametrize(
    "localized_game", P1_LOCALES, ids=[l["code"] for l in P1_LOCALES], indirect=True
)
def test_localization_p1_loads_cleanly(localized_game):
    page, locale = localized_game
    _assert_locale_healthy(page, locale)


# --------------------------------------------------------------------------- #
# DOCUMENTED i18n GAP: assert UI text actually localizes.
# Expected to FAIL today (site is English-only). Marked xfail so it does NOT
# break the build but IS visible in the report, and will xpass automatically
# once real localization ships. English locales are excluded (their text
# legitimately matches the baseline).
# --------------------------------------------------------------------------- #
_NON_ENGLISH_P0 = [l for l in P0_LOCALES if l["lang"] != "en"]


@pytest.mark.localization
@pytest.mark.p0
@pytest.mark.xfail(
    reason="theguiltygame.com is currently English-only; no i18n detected. "
    "This test documents the gap and will xpass when localization ships.",
    strict=False,
)
@pytest.mark.parametrize(
    "localized_game", _NON_ENGLISH_P0, ids=[l["code"] for l in _NON_ENGLISH_P0], indirect=True
)
def test_ui_text_is_localized_p0(localized_game, english_baseline):
    page, locale = localized_game
    html_lang = page.html_lang()
    body = page.visible_body_text().strip()

    lang_matches = html_lang == locale["lang"]
    text_changed = bool(body) and body != english_baseline["body_text"]

    if not (lang_matches or text_changed):
        log.warning("[%s] No localization detected (html_lang=%s)", locale["code"], html_lang)

    assert lang_matches or text_changed, (
        f"[{locale['code']}] UI not localized: html_lang={html_lang!r} "
        f"(expected {locale['lang']!r}) and body text identical to English baseline"
    )
