"""Рабочий макет страницы «Парная»: настоящая разметка калькулятора + расчёт.

    /usr/bin/python3 собрать_страницу.py  →  mockups/steam-page-v1.html
"""
import pathlib, re, sys
П = pathlib.Path('/home/user/-calculator-test/scratchpad/probes'); sys.path.insert(0, str(П))
import check_preset_chip as м
from playwright.sync_api import sync_playwright
ЗДЕСЬ = pathlib.Path(__file__).parent
ШРИФТЫ = (П / "шрифты_google.css").read_text(encoding="utf-8")
ПРЕОБР = (ЗДЕСЬ / 'преобразовать.js').read_text(encoding='utf-8')
ЖИВОЙ = (ЗДЕСЬ / 'живой.js').read_text(encoding='utf-8')
ВЫХ = pathlib.Path('/home/user/-calculator-test/mockups/steam-page-v1.html')
СТИЛЬ = """
.opt-unit{font-size:.7rem;color:var(--gray-light);margin-left:2px}
.opt-included + .opt-qty-stepper,.opt-included + .opt-dims{margin-left:8px}
.opt-why[hidden],.opt-calc[hidden]{display:none!important}
.opt-dims{display:inline-flex;align-items:center;gap:5px;color:var(--gray-light)}
.opt-dims i{font-style:normal;font-size:.7rem}
.dim-in{width:48px;height:28px;padding:0 4px;border:1px solid var(--border);border-radius:6px;background:var(--card-bg);color:inherit;font:inherit;font-size:.8rem;font-weight:600;text-align:center;outline:none}
.dim-in:focus{border-color:var(--green-mid)}
.opt-why{display:inline-block;font-size:.58rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--green-dark);background:var(--green-bg);border-radius:20px;padding:2px 8px;white-space:nowrap}
.opt-why.warn{color:#c06010;background:#f7efe6}
.opt-calc{margin-top:4px;font-size:.66rem;line-height:1.4;color:var(--gray-light)}
.opt-item[data-k="premium"]{cursor:default}
"""
с, порт = м.сервер()
try:
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
        стр = бр.new_page(viewport={"width": 1440, "height": 900})
        стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
        стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
        стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
        стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
          selectProjectOption(0); await new Promise(r => setTimeout(r, 1500)); }""")
        print(стр.evaluate(ПРЕОБР))
        стр.evaluate("""() => { const в = document.getElementById('versionBadge'); if (в) в.textContent = 'макет · 27.10.2026';
          document.getElementById('totalStrip').classList.remove('on'); }""")
        html = стр.content()
        бр.close()
finally:
    с.shutdown()
html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S)
html = re.sub(r'\s+on[a-zA-Z]+="[^"]*"', '', html)
html = re.sub(r'<link[^>]+fonts\.googleapis\.com[^>]*>', '', html)
html = re.sub(r'<link[^>]+fonts\.gstatic\.com[^>]*>', '', html)
html = html.replace('</head>', '<style>' + ШРИФТЫ + '</style><style>' + СТИЛЬ + '</style></head>', 1)
html = html.replace('<title>', '<title>Макет · Парная — ', 1) if '<title>' in html else html
html = html.replace('</body>', '<script>' + ЖИВОЙ + '</script></body>', 1)
ВЫХ.write_text(html, encoding='utf-8')
print(ВЫХ, len(html))
