"""
Locale catalogue for data-driven localization testing.

Tiering (P0 = launch-blocking, P1 = important) matches the priority scheme
used for i18n coverage. Each locale carries:
    code        - canonical locale identifier (lang_REGION)
    hl          - value passed to the site (query param / path segment)
    lang        - ISO-639 language subtag used for <html lang="..."> assertion
    name        - human-readable label (for report readability)

NOTE on routing: theguiltygame.com's exact language-routing scheme could not
be inspected in this environment. `LOCALE_URL_STRATEGY` below lets you switch
between the common approaches without touching test code. VERIFY the real one
in DevTools (look at how the site's own language switcher rewrites the URL).
"""

# How the site injects locale into the URL. Change ONE line to match reality.
#   "query_hl"   -> https://site/?hl=de_DE
#   "query_lang" -> https://site/?lang=de
#   "path"       -> https://site/de_DE/
#   "path_lang"  -> https://site/de/
LOCALE_URL_STRATEGY = "query_hl"


def _l(code, hl, lang, name):
    return {"code": code, "hl": hl, "lang": lang, "name": name}


# --- P0: launch-blocking locales ------------------------------------------
P0_LOCALES = [
    _l("de_DE", "de_DE", "de", "German (Germany)"),
    _l("es_ES", "es_ES", "es", "Spanish (Spain)"),
    _l("en_GB", "en_GB", "en", "English (UK)"),
    _l("es_LA", "es_LA", "es", "Spanish (Latin America)"),
    _l("fr_FR", "fr_FR", "fr", "French (France)"),
    _l("it_IT", "it_IT", "it", "Italian (Italy)"),
    _l("ja_JP", "ja_JP", "ja", "Japanese (Japan)"),
    _l("ko_KR", "ko_KR", "ko", "Korean (Korea)"),
]

# --- P1: important locales -------------------------------------------------
P1_LOCALES = [
    _l("cs_CZ", "cs_CZ", "cs", "Czech (Czechia)"),
    _l("da_DK", "da_DK", "da", "Danish (Denmark)"),
    _l("el_GR", "el_GR", "el", "Greek (Greece)"),
    _l("fi_FI", "fi_FI", "fi", "Finnish (Finland)"),
    _l("nb_NO", "nb_NO", "nb", "Norwegian Bokmal (Norway)"),
    _l("nl_NL", "nl_NL", "nl", "Dutch (Netherlands)"),
    _l("pl_PL", "pl_PL", "pl", "Polish (Poland)"),
    _l("pt_BR", "pt_BR", "pt", "Portuguese (Brazil)"),
    _l("pt_PT", "pt_PT", "pt", "Portuguese (Portugal)"),
    _l("ro_RO", "ro_RO", "ro", "Romanian (Romania)"),
    _l("ru_RU", "ru_RU", "ru", "Russian (Russia)"),
    _l("sv_SE", "sv_SE", "sv", "Swedish (Sweden)"),
    _l("tr_TR", "tr_TR", "tr", "Turkish (Turkey)"),
    _l("zh_CN", "zh_CN", "zh", "Chinese (Simplified, China)"),
    _l("zh_HK", "zh_HK", "zh", "Chinese (Hong Kong)"),
    _l("zh_TW", "zh_TW", "zh", "Chinese (Traditional, Taiwan)"),
]

ALL_LOCALES = P0_LOCALES + P1_LOCALES


def build_localized_url(base_url, locale):
    """Return `base_url` rewritten to request the given `locale` dict.

    Kept locale-routing-strategy-agnostic so switching strategies is a
    one-line change in LOCALE_URL_STRATEGY.
    """
    base = base_url.rstrip("/")
    hl = locale["hl"]
    lang = locale["lang"]

    if LOCALE_URL_STRATEGY == "query_hl":
        return f"{base}/?hl={hl}"
    if LOCALE_URL_STRATEGY == "query_lang":
        return f"{base}/?lang={lang}"
    if LOCALE_URL_STRATEGY == "path":
        return f"{base}/{hl}/"
    if LOCALE_URL_STRATEGY == "path_lang":
        return f"{base}/{lang}/"
    raise ValueError(f"Unknown LOCALE_URL_STRATEGY: {LOCALE_URL_STRATEGY}")
