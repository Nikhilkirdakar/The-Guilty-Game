"""
One-off DOM inspector for theguiltygame.com.

Run this ONCE to capture the real rendered structure (buttons, links, inputs,
headings, clickable elements). Paste the console output back so the locators
in pages/game_page.py can be pinned to real selectors.

    python inspect_site.py            # headless
    python inspect_site.py --show     # visible browser window
"""
import json
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SHOW = "--show" in sys.argv

opts = Options()
if not SHOW:
    opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")

d = webdriver.Chrome(options=opts)
try:
    d.get("https://theguiltygame.com/")

    # Wait for the React/Vite SPA to hydrate #root.
    for _ in range(40):
        ready = d.execute_script(
            "return !!document.querySelector('#root') "
            "&& document.querySelector('#root').children.length > 0"
        )
        if ready:
            break
        time.sleep(0.5)
    time.sleep(2)  # let animations/content settle

    print("TITLE     :", d.title)
    print("URL       :", d.current_url)
    print("HTML_LANG :", d.execute_script("return document.documentElement.lang"))

    info = d.execute_script(r"""
    function attrs(e){
      const o = {tag: e.tagName.toLowerCase()};
      if (e.id) o.id = e.id;
      const c = e.getAttribute('class'); if (c) o.class = c;
      for (const a of e.attributes){
        if (a.name.startsWith('data-') || ['role','aria-label','href','type','name','placeholder'].includes(a.name))
          o[a.name] = a.value;
      }
      const t = (e.innerText || '').trim(); if (t) o.text = t.slice(0, 70);
      return o;
    }
    return {
      buttons:  Array.from(document.querySelectorAll('button')).map(attrs),
      links:    Array.from(document.querySelectorAll('a')).map(attrs),
      inputs:   Array.from(document.querySelectorAll('input,textarea,select')).map(attrs),
      headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(attrs),
      clickable: Array.from(document.querySelectorAll(
                   '[role="button"],[onclick],[class*="btn"],[class*="button"],[class*="start"],[class*="play"],[class*="card"]'
                 )).map(attrs).slice(0, 40),
    };
    """)

    for section in ["headings", "buttons", "links", "inputs", "clickable"]:
        print(f"\n=== {section.upper()} ({len(info[section])}) ===")
        print(json.dumps(info[section], indent=1, ensure_ascii=False))

    with open("tgg_rendered.html", "w", encoding="utf-8") as f:
        f.write(d.page_source)
    print("\nFull rendered HTML saved -> tgg_rendered.html (%d bytes)" % len(d.page_source))
finally:
    d.quit()
