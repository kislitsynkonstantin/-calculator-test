#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Snapshot the real calculator page + 5 windows into one static mockup file.

    python3 snapshot.py out.html
"""
import json, pathlib, sys
import harness
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
ОКНА = {  # name -> overlay id, open code
    "presets":  ("presetPanel", "async () => { openPresetPanel(); await new Promise(r => setTimeout(r, 400)); switchPresetTab('shared'); await new Promise(r => setTimeout(r, 600)); switchPresetTab('my'); await new Promise(r => setTimeout(r, 500)); }"),
    "plan":     ("paymentPlanOverlay", "async () => { openPaymentPlan(); await new Promise(r => setTimeout(r, 600)); }"),
    "settings": ("settingsPanel", "async () => { openSettings(); switchSettingsTab('set'); await new Promise(r => setTimeout(r, 600)); }"),
    "log":      ("actionLogOverlay", "async () => { openActionLog(); await new Promise(r => setTimeout(r, 1200)); }"),
    "print":    ("printOverlay", "async () => { openPrintPreview(); await new Promise(r => setTimeout(r, 1500)); }"),
}

СОБРАТЬ = r"""async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  // Логотипы для каждого цвета: они перекрашиваются на холсте, стилями их не сменить.
  const лого = {};
  for (const т of ['teal', 'bmsk', 'sky']) {
    applyTone(т, false);
    for (let и = 0; и < 40; и++) { if (!текущийТон() || document.documentElement.dataset.toneReady) break; await ждать(50); }
    await ждать(150);
    лого[т] = { light: картинкаТона(_LOGO_LIGHT), dark: картинкаТона(_LOGO_DARK) };
  }
  applyTone('teal', false);
  return лого;
}"""

ОЧИСТИТЬ = r"""() => {
  const к = document.documentElement.cloneNode(true);
  к.querySelectorAll('script, link[href*="fonts.googleapis"], link[href*="fonts.gstatic"], link[rel="preconnect"], link[rel="manifest"], iframe').forEach(e => e.remove());
  к.querySelectorAll('*').forEach(e => { [...e.attributes].forEach(а => { if (/^on/i.test(а.name)) e.removeAttribute(а.name); }); });
  ['loginScreen', 'pricingErrorScreen', 'authModal', 'komplOverlay', 'statsOverlay'].forEach(ид => { const e = к.querySelector('#' + ид); if (e) e.remove(); });
  к.querySelector('body').classList.remove('sticky-active', 'total-strip-on');
  const hb = к.querySelector('#headerBtns'); if (hb) hb.classList.remove('sticky');
  const ts = к.querySelector('#totalStrip'); if (ts) ts.classList.remove('on');
  return '<!doctype html>\n' + к.outerHTML;
}"""


def ужать_картинки(html):
    # Логотип хранится в размере для печати (~80 КБ); на экране он 98 px.
    import base64, io, re
    from PIL import Image
    def ужать(м):
        данные = base64.b64decode(м.group(2))
        if len(данные) < 24000:
            return м.group(0)
        кар = Image.open(io.BytesIO(данные))
        if кар.width > 440:
            кар = кар.resize((440, round(кар.height * 440 / кар.width)), Image.LANCZOS)
        буф = io.BytesIO(); кар.save(буф, 'PNG', optimize=True)
        return м.group(1) + base64.b64encode(буф.getvalue()).decode()
    return re.sub(r'(data:image/png;base64,)([A-Za-z0-9+/=]+)', ужать, html)


def главная(выход):
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=harness.хром(), args=harness.АРГИ)
        стр = harness.открыть(бр, 1440, 'blank-light')
        состояния = {}
        for имя, (ид, код) in ОКНА.items():
            закрыт = стр.evaluate(f"() => {{ const e = document.getElementById('{ид}'); return {{ style: e.getAttribute('style'), cls: e.className }}; }}")
            стр.evaluate(код)
            открыт = стр.evaluate(f"() => {{ const e = document.getElementById('{ид}'); return {{ style: e.getAttribute('style'), cls: e.className, body: document.body.className }}; }}")
            стр.evaluate(harness.ЗАКРЫТЬ); стр.wait_for_timeout(400)
            состояния[имя] = {"id": ид, "open": открыт, "closed": закрыт}
        лого = стр.evaluate(СОБРАТЬ)
        стр.evaluate("() => window.scrollTo(0, 0)")
        html = стр.evaluate(ОЧИСТИТЬ)
        бр.close()
    шрифты = (ЗДЕСЬ / "fonts-embedded.css").read_text(encoding="utf-8")
    стекло = (ЗДЕСЬ / "glass.css").read_text(encoding="utf-8")
    ui = (ЗДЕСЬ / "mockup-ui.css").read_text(encoding="utf-8")
    js = (ЗДЕСЬ / "mockup.js").read_text(encoding="utf-8")
    шапка = (ЗДЕСЬ / "mockup-intro.html").read_text(encoding="utf-8")
    данные = "window.МК = " + json.dumps({"окна": состояния, "лого": лого}, ensure_ascii=False) + ";"
    html = html.replace("<head>", '<head>\n<meta charset="utf-8"><title>Стекло — макет</title>'
                        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">', 1)
    html = html.replace("</head>", f'<style id="mk-fonts">{шрифты}</style>\n<style id="mk-glass">{стекло}</style>\n'
                        f'<style id="mk-ui">{ui}</style>\n</head>', 1)
    import re
    # Тело ищем после </head>: в стилях есть комментарий со словом «<body>».
    г = html.index("</head>")
    т_ = html.index("<body", г); к_ = html.index(">", т_) + 1
    html = html[:к_] + "\n" + шапка + html[к_:]
    html = html.replace("</body>", f"<script>{данные}\n{js}</script>\n</body>", 1)
    html = ужать_картинки(html)
    pathlib.Path(выход).write_text(html, encoding="utf-8")
    print(выход, len(html.encode()) // 1024, "KB", {к: len(в["light"]) // 1024 for к, в in лого.items()})


if __name__ == "__main__":
    главная(sys.argv[1] if len(sys.argv) > 1 else str(ЗДЕСЬ / "glass-v2.html"))
