#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Статья о выпуске открывается сразу, без загрузки по нажатию.

Константин 27.09.2026: «когда захожу в статью, долго всегда грузит. Ты можешь
ускорить? Можешь статьи сразу грузить при загрузке справки».

Проба держит:
  • текст статей приходит в фоне после входа, до того как справку открыли;
  • открытие справки начинает тянуть снимки статей (они уже в запросах
    браузера, пока справка на экране);
  • нажатие по «Журналу выпуска» ставит статью в окно без экрана «Статья
    загружается…» и без нового запроса к базе;
  • если текста в памяти нет (запрос после входа не прошёл), статья всё равно
    открывается — со строкой загрузки и одним запросом.

    python3 check_release_preload.py
"""
import importlib.util, json, pathlib, sys
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
с_ = importlib.util.spec_from_file_location("ра", ЗДЕСЬ / "check_release_article.py")
ра = importlib.util.module_from_spec(с_); с_.loader.exec_module(ра)
НАХОДКИ = []

СЧЁТ = """() => { window.__кБазе = [];
  const был = _sb.from.bind(_sb);
  _sb.from = т => { window.__кБазе.push(т); return был(т); }; }"""

НАЖАТЬ = """async () => {
  const к = document.getElementById('manualFrame');
  const виды = [];
  const было = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'srcdoc');
  Object.defineProperty(к, 'srcdoc', { configurable: true, get() { return было.get.call(this); },
    set(в) { виды.push(/Статья загружается/.test(в) ? 'заглушка' : (/Версия 2\\.5\\.12/.test(в) ? 'статья' : 'другое')); было.set.call(this, в); } });
  const т0 = performance.now();
  к.contentDocument.querySelector('[data-release="2.5.12"] [role=link]').click();
  for (let i = 0; i < 40 && !виды.includes('статья'); i++) await new Promise(r => setTimeout(r, 25));
  const мс = Math.round(performance.now() - т0);
  delete к.srcdoc;
  return { виды, мс, кБазе: window.__кБазе.filter(т => т === 'app_docs').length };
}"""


def прогон(бр, порт, теплый):
    н = "[в памяти]" if теплый else "[без памяти]"
    стр = бр.new_page(viewport={"width": 390, "height": 844})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ра.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\nwindow.__ТАБЛИЦЫ.app_docs = "
                        + json.dumps(ра.ряды(), ensure_ascii=False) + ";\nObject.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(ра.ЦЕНЫ, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2600)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    вПамяти = стр.evaluate("() => typeof _статьи !== 'undefined' && _статьи.has('2.5.12')")
    if теплый and not вПамяти:
        НАХОДКИ.append(f"{н} текст статьи не пришёл в фоне после входа — его грузит только нажатие"); стр.close(); return
    if not теплый:
        стр.evaluate("() => { if (typeof _статьи !== 'undefined') { _статьи.clear(); _статьиЖдут = null; _снимкиСтатейГреются = true; } }")
    стр.evaluate(СЧЁТ)
    стр.evaluate("() => openManual()")
    кадр = ра.ждать_кадр(стр, "#ch-updates")
    if not кадр:
        НАХОДКИ.append(f"{н} справка не открылась"); стр.close(); return
    стр.wait_for_timeout(1600)
    if теплый:
        снимки = стр.evaluate("() => performance.getEntriesByType('resource').filter(р => /assets\\/releases\\//.test(р.name)).length")
        if снимки < 5:
            НАХОДКИ.append(f"{н} при открытой справке снимки статьи ещё не запрошены: {снимки}")
    стр.evaluate("() => { window.__кБазе.length = 0; }")
    р = стр.evaluate(НАЖАТЬ)
    print(f"  {н}", json.dumps(р, ensure_ascii=False))
    if "статья" not in р["виды"]:
        НАХОДКИ.append(f"{н} статья не открылась: {р}")
    elif теплый and (р["виды"][0] != "статья" or р["кБазе"]):
        НАХОДКИ.append(f"{н} статья из памяти открылась через загрузку или новый запрос к базе: {р}")
    elif not теплый and р["кБазе"] != 1:
        НАХОДКИ.append(f"{н} без памяти статья должна прийти одним запросом: {р}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = ра.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=ра.хром(), args=["--no-sandbox"])
            прогон(бр, порт, True)
            прогон(бр, порт, False)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: текст статей приходит в фоне после входа, снимки тянутся с открытием справки, "
          "статья открывается из памяти без строки загрузки и без запроса к базе; без памяти — одним запросом.")


if __name__ == "__main__":
    главная()
