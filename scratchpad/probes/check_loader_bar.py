#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полоска загрузки справки и базы знаний — цвета оформления.

Константин 26.09.2026: «это на загрузку Справки. Цвет полоски ставь под
цветовую схему активную» (вариант A из mockups/manual-loader-v1.html) и «ещё
есть места, где может так грузиться… например, база знаний».

Проба держит, в бирюзовом и «Зелёном-графите», днём и ночью, на 390 и 1440:
  • пока справка не пришла, в окне справки стоит полоска с бегущим отрезком
    под подписью «Справка загружается…», по центру окна;
  • отрезок — цвета оформления: днём --br-28, ночью --br-48 своего тона;
  • справка не пришла — полоски нет, остаётся текст ошибки;
  • у базы знаний вместо кружка-спиннера та же полоска того же цвета.

    python3 check_loader_bar.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ЦВЕТ = """(ночь) => { const s = getComputedStyle(document.documentElement).getPropertyValue(ночь ? '--br-48' : '--br-28').trim();
  const d = document.createElement('div'); d.style.color = s; document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }"""

СПРАВКА = """async () => {
  _справка = null;
  window.загрузитьСправку = () => new Promise(() => {});   // справка «идёт» бесконечно
  openManual(); await new Promise(r => setTimeout(r, 400));
  const f = document.getElementById('manualFrame'), d = f.contentDocument;
  const bar = d.querySelector('.bm-load'), cap = [...d.querySelectorAll('div')].find(x => x.textContent.trim() === 'Справка загружается…' && !x.children.length);
  if (!bar) return { нет: true };
  const i = bar.querySelector('i'), br = bar.getBoundingClientRect(), W = d.documentElement.clientWidth, H = d.documentElement.clientHeight;
  const cr = cap ? cap.getBoundingClientRect() : null;
  const о = { цвет: getComputedStyle(i).backgroundColor, ш: Math.round(br.width), в: br.height,
    центрX: Math.abs((br.left + br.right) / 2 - W / 2), центрY: Math.abs(br.top - H / 2),
    подписьНиже: !!(cr && cr.top >= br.bottom + 8), анимация: getComputedStyle(i).animationName };
  document.getElementById('manualOverlay').style.display = 'none';
  return о;
}"""

ОШИБКА = """async () => {
  _справка = null;
  window.загрузитьСправку = () => Promise.reject(new Error('нет связи'));
  openManual(); await new Promise(r => setTimeout(r, 400));
  const d = document.getElementById('manualFrame').contentDocument;
  const о = { полоска: !!d.querySelector('.bm-load'), текст: d.body.innerText };
  document.getElementById('manualOverlay').style.display = 'none';
  return о;
}"""

БАЗА = """async () => {
  openGuide(); await new Promise(r => setTimeout(r, 300));
  const л = document.getElementById('guideLoader');
  const bar = л && л.querySelector('.bm-load');
  const о = bar ? { цвет: getComputedStyle(bar.querySelector('i')).backgroundColor, ш: Math.round(bar.getBoundingClientRect().width),
    кружок: !![...л.querySelectorAll('div')].find(x => /guideSpin/.test(x.getAttribute('style') || '')) } : { нет: true };
  document.getElementById('guideOverlay').style.display = 'none';
  return о;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }""")
                for тон in ("", "bmsk"):
                    for ночь in (False, True):
                        стр.evaluate(f"() => {{ applyTone('{тон}', false); document.body.classList.toggle('dark', {str(ночь).lower()}); }}")
                        н = f"{ш} {тон or 'бирюза'} {'ночь' if ночь else 'день'}"
                        ждём = стр.evaluate(ЦВЕТ, ночь)
                        р = стр.evaluate(СПРАВКА)
                        if р.get("нет"):
                            плохо(н + ": в окне справки нет полоски загрузки"); continue
                        if р["цвет"] != ждём: плохо(н + f": отрезок не цвета оформления ({р['цвет']} вместо {ждём})")
                        if р["ш"] != 180 or р["в"] != 3: плохо(н + f": полоска не 180×3 ({р['ш']}×{р['в']})")
                        if р["центрX"] > 2 or р["центрY"] > 40: плохо(н + f": полоска не по центру ({р['центрX']:.0f}, {р['центрY']:.0f})")
                        if not р["подписьНиже"]: плохо(н + ": подпись не под полоской")
                        if р["анимация"] in ("none", ""): плохо(н + ": отрезок не бежит")
                        б = стр.evaluate(БАЗА)
                        if б.get("нет"): плохо(н + ": у базы знаний нет полоски")
                        else:
                            if б["кружок"]: плохо(н + ": у базы знаний остался кружок-спиннер")
                            if б["цвет"] != ждём: плохо(н + f": полоска базы знаний не цвета оформления ({б['цвет']} вместо {ждём})")
                        if ш == 390 and not тон and not ночь:
                            print(f"  {н}: справка {json.dumps(р, ensure_ascii=False)}, база {json.dumps(б, ensure_ascii=False)}")
                о = стр.evaluate(ОШИБКА)
                if о["полоска"] or "не удалось" not in о["текст"]:
                    плохо(f"{ш}: при ошибке загрузки справки не то: {о}")
                for е in [е for е in ошибки if "supabase.co" not in е and "knowledge.baniamsk" not in е][:3]:
                    плохо(f"{ш}: ошибка страницы: {е[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:30]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: пока справка идёт, в окне по центру бежит отрезок цвета оформления над подписью; при ошибке — только текст; "
          "у базы знаний та же полоска вместо кружка — в бирюзе и «Зелёном-графите», днём и ночью, на 390 и 1440.")


if __name__ == "__main__":
    главная()
