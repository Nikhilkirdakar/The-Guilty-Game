"""
Per-locale screenshot gallery generator.

Scans reports/screenshots/<locale>/ and builds a single self-navigable HTML
page grouping every screenshot by locale — an at-a-glance i18n evidence report.

Usage:
    python -m utils.generate_gallery                 # relative-link gallery (small file)
    python -m utils.generate_gallery --embed         # base64-embedded, fully portable
    python -m utils.generate_gallery --out reports/gallery.html

It also runs automatically at the end of any test session that produced
per-locale screenshots (wired in conftest.py:pytest_sessionfinish).
"""
import argparse
import base64
import html
import os

from config import settings

# Optional: pretty locale names (e.g. "German (Germany)") if the catalogue loads.
try:
    from config.locales import ALL_LOCALES
    _NAMES = {l["code"]: l["name"] for l in ALL_LOCALES}
except Exception:
    _NAMES = {}


def _img_src(path: str, embed: bool, gallery_dir: str) -> str:
    """Return an <img src> value: base64 data URI if embed, else a relative path."""
    if embed:
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            return ""
    return os.path.relpath(path, gallery_dir).replace(os.sep, "/")


def generate_gallery(screenshots_dir: str = None, out_path: str = None,
                     embed: bool = False) -> str:
    """Build the gallery HTML. Returns the output path (or '' if no shots)."""
    screenshots_dir = screenshots_dir or settings.SCREENSHOTS_DIR
    out_path = out_path or os.path.join(settings.REPORTS_DIR, "locale_gallery.html")

    if not os.path.isdir(screenshots_dir):
        return ""

    # Collect locale folders (each subdir is a locale code) that contain PNGs.
    locales = {}
    for entry in sorted(os.listdir(screenshots_dir)):
        sub = os.path.join(screenshots_dir, entry)
        if not os.path.isdir(sub):
            continue
        pngs = sorted(f for f in os.listdir(sub) if f.lower().endswith(".png"))
        if pngs:
            locales[entry] = [os.path.join(sub, p) for p in pngs]

    if not locales:
        return ""

    gallery_dir = os.path.dirname(os.path.abspath(out_path))
    total_shots = sum(len(v) for v in locales.values())

    # ------------------------------------------------------------------ #
    # Build HTML
    # ------------------------------------------------------------------ #
    nav_links = " · ".join(
        f'<a href="#{code}">{html.escape(code)}</a>' for code in locales
    )

    sections = []
    for code, paths in locales.items():
        name = _NAMES.get(code, "")
        cards = []
        for p in paths:
            src = _img_src(p, embed, gallery_dir)
            fname = html.escape(os.path.basename(p))
            cards.append(
                f'<figure class="card">'
                f'<a href="{src}" target="_blank" rel="noopener">'
                f'<img loading="lazy" src="{src}" alt="{fname}"></a>'
                f'<figcaption>{fname}</figcaption></figure>'
            )
        title = html.escape(code) + (f' — {html.escape(name)}' if name else "")
        sections.append(
            f'<section id="{html.escape(code)}">'
            f'<h2>{title} <span class="count">({len(paths)})</span></h2>'
            f'<div class="grid">{"".join(cards)}</div></section>'
        )

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Guilty Game — Localization Screenshot Gallery</title>
<style>
  :root {{ --bg:#0f1115; --card:#171a21; --line:#2a2f3a; --accent:#e8b84b; --muted:#8b93a1; --text:#e8eaed; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; }}
  header {{ position:sticky; top:0; background:rgba(15,17,21,.95); backdrop-filter:blur(6px);
           border-bottom:1px solid var(--line); padding:16px 24px; z-index:10; }}
  header h1 {{ margin:0 0 6px; font-size:18px; }}
  header .meta {{ color:var(--muted); font-size:12px; }}
  nav {{ margin-top:10px; font-size:12px; line-height:2; }}
  nav a {{ color:var(--accent); text-decoration:none; margin-right:4px; }}
  main {{ padding:24px; max-width:1400px; margin:0 auto; }}
  section {{ margin-bottom:40px; scroll-margin-top:120px; }}
  h2 {{ font-size:16px; border-bottom:1px solid var(--line); padding-bottom:8px; }}
  h2 .count {{ color:var(--muted); font-weight:400; font-size:12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:14px; }}
  .card {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
  .card img {{ width:100%; display:block; background:#000; aspect-ratio:16/10; object-fit:cover; }}
  .card figcaption {{ padding:6px 8px; font-size:11px; color:var(--muted); word-break:break-all; }}
  a.top {{ position:fixed; right:20px; bottom:20px; background:var(--accent); color:#111;
           padding:8px 12px; border-radius:20px; text-decoration:none; font-weight:600; }}
</style></head>
<body>
<header>
  <h1>The Guilty Game — Localization Screenshot Gallery</h1>
  <div class="meta">{len(locales)} locales · {total_shots} screenshots · full resolution</div>
  <nav>{nav_links}</nav>
</header>
<main>{"".join(sections)}</main>
<a class="top" href="#">↑ Top</a>
</body></html>"""

    os.makedirs(gallery_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Build the per-locale screenshot gallery")
    ap.add_argument("--dir", default=None, help="screenshots directory")
    ap.add_argument("--out", default=None, help="output HTML path")
    ap.add_argument("--embed", action="store_true", help="embed images as base64 (portable)")
    args = ap.parse_args()

    path = generate_gallery(args.dir, args.out, embed=args.embed)
    if path:
        print(f"Gallery written: {path}")
    else:
        print("No per-locale screenshots found — run the localization suite first.")


if __name__ == "__main__":
    main()
