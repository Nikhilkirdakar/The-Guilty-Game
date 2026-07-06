"""
Sign-in flow inspector.

Clicks the SIGN IN button and dumps whatever appears (modal form, dedicated
page, or a third-party OAuth redirect) so the LoginPage selectors can be
pinned to reality. Run once and paste the output back.

    python inspect_signin.py            # headless
    python inspect_signin.py --show     # visible window (recommended for OAuth)
"""
import json
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    for _ in range(40):
        if d.execute_script("return !!document.querySelector('#root') && document.querySelector('#root').children.length>0"):
            break
        time.sleep(0.5)
    time.sleep(1.5)

    print("URL before:", d.current_url)

    # Click SIGN IN (button.tg-ghost, or any button whose text says 'sign in')
    clicked = d.execute_script("""
        const btns = Array.from(document.querySelectorAll('button'));
        const b = document.querySelector('button.tg-ghost')
              || btns.find(x => (x.innerText||'').toLowerCase().includes('sign in'));
        if (b) { b.click(); return (b.innerText||'').trim(); }
        return null;
    """)
    print("Clicked SIGN IN button:", clicked)
    time.sleep(3)

    print("URL after :", d.current_url)
    print("Windows/tabs:", len(d.window_handles))

    # If it redirected to an OAuth provider, report and stop.
    url = d.current_url.lower()
    for provider in ["accounts.google.com", "facebook.com", "apple.com", "auth0", "clerk", "supabase"]:
        if provider in url:
            print(f"\n>>> OAuth / 3rd-party auth detected: {provider}")
            print(">>> Native username/password automation will NOT work here.")
            break

    info = d.execute_script(r"""
    function attrs(e){
      const o={tag:e.tagName.toLowerCase()};
      if(e.id)o.id=e.id;
      const c=e.getAttribute('class'); if(c)o.class=c;
      for(const a of e.attributes){
        if(a.name.startsWith('data-')||['role','aria-label','type','name','placeholder','href'].includes(a.name))
          o[a.name]=a.value;
      }
      const t=(e.innerText||'').trim(); if(t)o.text=t.slice(0,60);
      return o;
    }
    return {
      inputs:  Array.from(document.querySelectorAll('input,textarea,select')).map(attrs),
      buttons: Array.from(document.querySelectorAll('button,[role=button],a[href]')).map(attrs).slice(0,40),
      dialogs: Array.from(document.querySelectorAll('[role=dialog],.modal,dialog,form')).map(attrs),
      iframes: Array.from(document.querySelectorAll('iframe')).map(f => ({src:f.src, id:f.id, title:f.title})),
    };
    """)
    for k in ["dialogs", "inputs", "buttons", "iframes"]:
        print(f"\n=== {k.upper()} ({len(info[k])}) ===")
        print(json.dumps(info[k], indent=1, ensure_ascii=False))

    with open("tgg_signin.html", "w", encoding="utf-8") as f:
        f.write(d.page_source)
    print("\nSaved -> tgg_signin.html")
finally:
    d.quit()
