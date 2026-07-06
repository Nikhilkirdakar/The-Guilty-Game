"""
Script 1 — End-to-end functional flow (default / English locale).

theguiltygame.com is a Vite/React single-page site. The testable functional
surface is: the landing page renders its hero + all CTAs + the 4-step "how it
works" section, and the game-entry CTAs (SIGN IN / START FIRST CASE / PLAY
FREE) produce an observable state transition when clicked.

Assertions are ordered cheapest-first so failures surface at the right altitude.
"""
import pytest

from config import settings
from pages.game_page import GamePage


@pytest.mark.functional
@pytest.mark.smoke
class TestLandingPage:
    """Fast sanity checks on the landing page."""

    def test_home_page_loads(self, game_page: GamePage):
        assert game_page.is_loaded(), "Landing hero (h1.tg-h1) never rendered"

    def test_page_title(self, game_page: GamePage):
        title = game_page.title
        assert title, "Page title is empty"
        assert settings.EXPECTED_TITLE_SUBSTRING.lower() in title.lower(), (
            f"Expected {settings.EXPECTED_TITLE_SUBSTRING!r} in title, got {title!r}"
        )

    def test_landed_on_correct_host(self, game_page: GamePage, base_url):
        host = base_url.split("//", 1)[-1].split("/")[0]
        assert host in game_page.current_url, (
            f"Unexpected URL after load: {game_page.current_url}"
        )

    def test_hero_headline_present(self, game_page: GamePage):
        hero = game_page.hero_text()
        assert hero, "Hero headline is empty"
        # Copy from the live page — tolerant to minor punctuation changes.
        assert "lied to you" in hero.lower(), f"Unexpected hero copy: {hero!r}"

    def test_no_broken_images_on_landing(self, game_page: GamePage):
        broken = game_page.count_broken_images()
        assert broken == 0, f"{broken} broken image(s) on landing page"


@pytest.mark.functional
class TestKeyCtasPresent:
    """The primary calls-to-action must all be visible and labelled."""

    def test_sign_in_present(self, game_page: GamePage):
        assert game_page.has_sign_in(), "SIGN IN button not visible"

    def test_play_free_present(self, game_page: GamePage):
        assert game_page.has_play_free(), "PLAY FREE CTA not visible"

    def test_start_first_case_present(self, game_page: GamePage):
        assert game_page.has_start_first_case(), "START FIRST CASE CTA not visible"

    def test_expected_ctas_rendered(self, game_page: GamePage):
        ctas = " | ".join(game_page.cta_texts()).lower()
        for expected in ["play free", "start first case", "resume investigation"]:
            assert expected in ctas, f"Missing CTA {expected!r}; found: {ctas!r}"

    def test_how_it_works_steps_present(self, game_page: GamePage):
        # The 4-step explainer is core landing content. Steps are lazy-mounted
        # on scroll, so all_steps_present() scrolls to reveal them.
        found = game_page.found_steps()
        missing = [s for s in game_page.STEP_HEADINGS if s not in found]
        assert not missing, f"Missing 'how it works' steps: {missing} (found: {found})"


@pytest.mark.functional
class TestGameEntryFlow:
    """Clicking a game-entry CTA must transition the app (nav / modal / sign-in)."""

    def test_start_first_case_triggers_transition(self, game_page: GamePage):
        before = game_page.dom_signature()
        game_page.start_game()
        assert game_page.state_changed_since(before), (
            "Clicking START FIRST CASE produced no observable state change"
        )

    def test_sign_in_triggers_transition(self, game_page: GamePage):
        before = game_page.dom_signature()
        game_page.click_sign_in()
        assert game_page.state_changed_since(before), (
            "Clicking SIGN IN produced no observable state change"
        )

    def test_play_free_triggers_transition(self, game_page: GamePage):
        before = game_page.dom_signature()
        game_page.click(GamePage.PLAY_FREE)
        assert game_page.state_changed_since(before), (
            "Clicking PLAY FREE produced no observable state change"
        )
