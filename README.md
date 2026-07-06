# The Guilty Game — Selenium + Pytest Automation Framework

A production-grade, Page Object Model (POM) test automation framework for
[theguiltygame.com](https://theguiltygame.com/), covering an end-to-end
functional flow and data-driven localization testing across **24 locales**
(8 P0 + 16 P1), with `pytest-html` reporting and screenshot-on-failure.

> ℹ️ The brief mentioned "25 locales" but the enumerated list contains 24
> distinct codes (8 P0 + 16 P1). All 24 are implemented; add a 25th to
> `config/locales.py` if one was intended.

> ✅ **Selectors are pinned to the real rendered DOM** (captured 2026-07-06 via
> `inspect_site.py`). Re-run that script if the site markup changes.
>
> **Two findings from inspecting the live site:**
> 1. It's a **Vite/React single-page marketing site**. The game starts behind
>    CTAs (`SIGN IN`, `PLAY FREE >`, `START FIRST CASE >`); there is no game
>    board, `<a>` links, or `<input>` fields in the landing DOM. The functional
>    suite tests the landing render + CTA presence + click-through transitions.
> 2. **The site is English-only** (`<html lang="en">`, no language switcher).
>    Locale query params don't change content today. The localization suite
>    therefore hard-asserts *healthy load + no broken assets* per locale, and
>    keeps the "text is localized" check as an **`xfail`** that documents the
>    i18n gap and will `xpass` automatically once localization ships.

---

## 1. Project Structure

```
theguiltygame_automation/
├── conftest.py                  # Fixtures, CLI options, screenshot-on-failure hook
├── pytest.ini                   # Markers, HTML report defaults, logging
├── requirements.txt             # Dependencies
├── .gitignore                   # Python / Selenium / IDE ignores
├── README.md                    # This guide
│
├── config/                      # Configuration (no test logic)
│   ├── __init__.py
│   ├── settings.py              # URLs, timeouts, browser defaults (env-overridable)
│   ├── locales.py               # P0/P1 locale catalogue + URL-routing strategy
│   └── credentials.py           # Secrets loader (env / .env) — never hardcoded
│
├── pages/                       # Page Object Model layer (locators + actions)
│   ├── __init__.py
│   ├── base_page.py             # Waits, clicks, typing, screenshots, i18n helpers
│   ├── game_page.py             # theguiltygame.com landing/game page object
│   └── login_page.py            # SIGN IN flow (Clerk email/password; selectors pinned)
│
├── tests/                       # Test scripts (assertions only, no raw Selenium)
│   ├── __init__.py
│   ├── test_functional_flow.py  # Script 1: end-to-end functional flow
│   ├── test_localization.py     # Script 2: 24-locale i18n suite + per-locale screenshots
│   └── test_authenticated.py    # Script 3: SIGN IN flow (credential-gated, skipped by default)
│
├── inspect_site.py              # One-off: dump landing DOM
├── inspect_signin.py            # One-off: dump the sign-in form DOM
├── .env.example                 # Template for local secrets (copy to .env)
│
├── utils/                       # Cross-cutting helpers
│   ├── __init__.py
│   ├── driver_factory.py        # Browser launch (chrome/firefox/edge, headless)
│   └── logger.py                # Shared logging config
│
├── ci/
│   └── Jenkinsfile              # Declarative pipeline (P0 + P1 + artifacts)
│
└── reports/                     # Generated artifacts (git-ignored)
    ├── report.html
    └── screenshots/
        └── .gitkeep
```

**Design principle:** locators + interactions live in `pages/`; tests only
call page methods and assert. Change a selector once in `game_page.py` and
every test benefits.

---

## 2. Setup (PyCharm)

1. **Open the project:** PyCharm → *Open* → select `theguiltygame_automation/`.
2. **Create a virtual environment:** PyCharm → *Settings* → *Project* →
   *Python Interpreter* → *Add* → *Virtualenv* (Python 3.9+).
3. **Install dependencies** (PyCharm terminal):
   ```bash
   pip install -r requirements.txt
   ```
   Selenium ≥ 4.6 ships **Selenium Manager**, which auto-downloads the correct
   browser driver — no manual `chromedriver` setup needed.
4. **Mark `pytest` as the test runner:** *Settings* → *Tools* → *Python
   Integrated Tools* → *Default test runner* → **pytest**.

---

## 3. Running Tests

```bash
# Everything, headless Chrome, HTML report auto-written to reports/report.html
pytest

# Watch it run in a real browser window
pytest --headless=false

# Functional flow only
pytest tests/test_functional_flow.py -m functional

# Just the launch-blocking locales (fast gate)
pytest tests/test_localization.py -m p0

# P1 locales, parallelised across CPU cores (needs pytest-xdist)
pytest tests/test_localization.py -m p1 -n auto

# Different browser
pytest --browser=firefox

# Retry flaky tests twice (needs pytest-rerunfailures)
pytest -m p0 --reruns 2
```

**Useful CLI options** (defined in `conftest.py`):
| Option | Default | Meaning |
|---|---|---|
| `--browser` | `chrome` | `chrome` \| `firefox` \| `edge` |
| `--headless` | `true` | `true` \| `false` |
| `--base-url` | `https://theguiltygame.com/` | App under test |

Everything is also overridable via env vars (`TGG_BASE_URL`, `TGG_BROWSER`,
`TGG_HEADLESS`, `TGG_TIMEOUT`, …) — see `config/settings.py`.

---

## 4. Reporting & Artifacts

- **HTML report:** `reports/report.html` (self-contained; open in any browser).
- **Screenshot on failure:** every failed test auto-captures a screenshot,
  saves it to `reports/screenshots/FAIL_<test>.png`, **and embeds it inline**
  in the HTML report along with the failing URL (see the hook in `conftest.py`).
- **Per-locale screenshots:** every localization test captures full-resolution
  screenshots right after switching locale and stores them **in one folder per
  locale**, then embeds them in the HTML report (pass or fail):
  ```
  reports/screenshots/
    ├── de_DE/  de_DE_landing_01.png ... _06.png  de_DE_full.png
    ├── es_ES/  ...
    └── ...  (one folder per locale)
  ```
  The scrolling series (`_landing_NN.png`) captures lazy-mounted sections that
  a single shot would miss; `_full.png` is a stitched full-page capture.
  Images are never downscaled.
- **Per-locale gallery:** a single browsable HTML page grouping every
  screenshot by locale is auto-generated at `reports/locale_gallery.html` at the
  end of any run that produced locale screenshots. Regenerate manually anytime:
  ```bash
  python -m utils.generate_gallery            # relative-link gallery (small file)
  python -m utils.generate_gallery --embed    # base64-embedded, fully portable
  open reports/locale_gallery.html
  ```

---

## 5. GitHub Setup

The local repo is **already initialized and committed** on branch `main`
(27 source files; venv / reports / screenshots / `.env` are git-ignored).
You only need to create the remote and push:

```bash
# From the project root. Using GitHub CLI:
gh repo create theguiltygame-automation --private --source=. --remote=origin --push

# ...or with a manually created empty repo:
git remote add origin https://github.com/<you>/theguiltygame-automation.git
git push -u origin main
```

> If you want the commit under a personal (non-work) email, set it before pushing:
> `git config user.email "you@personal.com"` then `git commit --amend --reset-author`.

CI is preconfigured in **`.github/workflows/tests.yml`** — on push/PR (and nightly)
it runs the functional + P0 + P1 suites headless and uploads the HTML reports and
per-locale screenshots as workflow artifacts.

The `.gitignore` keeps generated reports, screenshots, virtualenvs,
`__pycache__`, IDE files, `.env`, and inspector DOM dumps out of version control
(the empty `reports/screenshots/` folder is preserved via `.gitkeep`).

---

## 6. Jenkins Pipeline

`ci/Jenkinsfile` is a declarative pipeline that:
1. **Cleans the workspace** (`cleanWs()`) and checks out `scm`.
2. **Creates a virtualenv** and installs `requirements.txt`.
3. Runs the **Functional Flow**, then **Localization P0**, then **P1**
   (P0/P1 parallelised with `-n auto`).
4. **Publishes JUnit results** and **archives** all HTML reports +
   failure screenshots as build artifacts.

Create a *Pipeline* job → *Pipeline script from SCM* → point it at your repo,
set *Script Path* to `ci/Jenkinsfile`. Parameters (`BASE_URL`, `BROWSER`,
`HEADLESS`) are exposed at build time.

---

## 7. Authenticated SIGN IN flow (optional)

Credential-gated and **skipped by default** so default runs / CI stay green.
Auth is **Clerk** (email/password form rendered inline on the page) — selectors
are already pinned in `pages/login_page.py`.

```bash
# 1. Register a DEDICATED throwaway test account on theguiltygame.com
#    (use the "Sign up" tab; a burner / +alias email is fine). Do this ONCE.

# 2. Create a local, git-ignored secrets file
cp .env.example .env

# 3. Edit .env with that test account:
#    TGG_USERNAME=your-test-account@example.com
#    TGG_PASSWORD=your-password
#    TGG_RUN_AUTH=true

# 4. Run the auth suite
pytest tests/test_authenticated.py -v
```

- Secrets are read via `config/credentials.py` from the environment or `.env`
  (`.env` is git-ignored). **Nothing is ever hardcoded or committed.**
- Clerk PRODUCTION may enable bot protection (Cloudflare Turnstile). If a
  challenge appears at sign-in, `login_page.py` raises `SignInBlocked` and the
  test **skips** with a clear reason. In that case use a Clerk *development*
  instance with a `+clerk_test` account, or session-cookie injection.
- `inspect_signin.py` can be re-run anytime the Clerk markup changes.

> ⚠️ Do **not** use a personal Gmail/account for automated login. Use a
> throwaway test account — storing personal creds in test infra is a risk, and
> provider anti-automation may lock the account.

---

## 8. Hardening Checklist (after selector verification)

- [ ] Confirm each `# VERIFY` locator in `pages/game_page.py` against the live DOM.
- [ ] Set `EXPECTED_TITLE_SUBSTRING` in `config/settings.py` to the real title.
- [ ] Confirm `LOCALE_URL_STRATEGY` in `config/locales.py` matches how the site
      routes languages (`?hl=`, `?lang=`, `/de_DE/`, or `/de/`).
- [ ] If the site has no i18n at all, the localization suite's text-change
      assertion will (correctly) flag it — treat that as a real finding.
```
