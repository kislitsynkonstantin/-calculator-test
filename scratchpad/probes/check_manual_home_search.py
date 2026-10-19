#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск на оглавлении справки.

Константин 19.10.2026, снимком оглавления справки на телефоне с чертой под
«Что нового»: «Сюда на главную тоже размести поиск, который есть в боковом
меню». На телефоне меню спрятано, и до поиска было два нажатия.

Проба держит, через калькулятор (тест), на 390 и 1440, днём и ночью:
  • на оглавлении есть строка поиска — под «Что нового» и над первым
    разделом, не вплотную ни к одному (зазор от 10 px), во всю колонку, не
    ниже 40 px; кегль поля 16 px — мельче iPhone увеличивает страницу;
  • ночью поле не белое, текст в нём светлый;
  • набранное слово раскрывает выдачу под полем, выдача в экране и лежит
    поверх разделов (её строку можно нажать); крестик появляется и очищает;
  • нажатие на строку выдачи открывает главу, где это слово есть; на
    оглавлении после возврата поле пустое; Esc выдачу закрывает;
  • поиск в меню работает как прежде (на компьютере, где меню видно);

в бою (оболочка с ?contour=prod) до выпуска 2.5.19 поиска на оглавлении нет.

    python3 check_manual_home_search.py
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_manual_home as д  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
СЛОВО = "задат"

МЕРА = """() => {
  const п = document.getElementById('homeSearch');
  if (!п) return null;
  const о = п.closest('.hm-srch'), r = п.getBoundingClientRect();
  const нов = document.querySelector('#ch-home .hm-news'), рз = document.querySelector('#ch-home .hm-h');
  const кол = document.querySelector('#ch-home .hm-cols').getBoundingClientRect();
  const с = getComputedStyle(п);
  return { в: r.top, н: r.bottom, л: r.left, п: r.right, выс: r.height, W: innerWidth,
    колЛ: кол.left, колП: кол.right,
    новНиз: нов ? нов.getBoundingClientRect().bottom : null, разделВерх: рз ? рз.getBoundingClientRect().top : null,
    кегль: parseFloat(с.fontSize), фон: с.backgroundColor, цвет: с.color };
}"""

ВЫДАЧА = """() => {
  const р = document.querySelector('#ch-home .hm-srch .srch-results');
  const пр = document.querySelectorAll('.srch-results.open');
  if (!р) return null;
  const rr = р.getBoundingClientRect(), стр = р.querySelector('.srch-item');
  let сверху = false;
  if (стр) { const б = стр.getBoundingClientRect(); const э = document.elementFromPoint(б.left + 20, б.top + б.height / 2);
    сверху = !!(э && стр.contains(э)); }
  const кр = document.querySelector('#ch-home .hm-srch .srch-clr');
  return { открыта: р.classList.contains('open'), строк: р.querySelectorAll('.srch-item').length, всего: пр.length,
    низ: rr.bottom, право: rr.right, лево: rr.left, H: innerHeight, W: innerWidth, сверху,
    крестик: кр ? getComputedStyle(кр).display : null };
}"""


def плохо(т):
    НАХОДКИ.append(т)


def яркость(css):
    ч = [float(x) for x in css[css.index("(") + 1:css.index(")")].split(",")[:3]]
    return sum(ч) / 3


def прогон(бр, порт, ш, ночь):
    н = f"[{ш} {'ночь' if ночь else 'день'}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900}, color_scheme="dark" if ночь else "light")
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=д.ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(д.ЗАГЛУШКА)
    стр.add_init_script(д.ЦЕНЫ)
    стр.add_init_script("window.__ТАБЛИЦЫ.app_docs = " + json.dumps(д.ряды(), ensure_ascii=False) + ";")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("(ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';"
                 " try { applyThemeMode(ночь ? 'dark' : 'light', false); } catch (e) {} }", ночь)
    стр.evaluate("() => openManual()")
    к = д.кадр_справки(стр)
    стр.wait_for_timeout(1200)
    тело = к.locator("body")
    м = тело.evaluate("() => (" + МЕРА + ")()")
    if not м:
        плохо(f"{н} на оглавлении нет строки поиска"); стр.close(); return
    if м["новНиз"] is not None and м["в"] - м["новНиз"] < 10:
        плохо(f"{н} поиск вплотную к «Что нового»: {round(м['в'] - м['новНиз'])} px")
    if м["разделВерх"] is None or м["разделВерх"] - м["н"] < 16:
        плохо(f"{н} поиск вплотную к первому разделу: {м['разделВерх']} против низа {round(м['н'])}")
    if abs(м["л"] - м["колЛ"]) > 1 or abs(м["п"] - м["колП"]) > 1 or м["п"] > м["W"]:
        плохо(f"{н} поле не во всю колонку: {round(м['л'])}…{round(м['п'])} при колонке {round(м['колЛ'])}…{round(м['колП'])}")
    if м["выс"] < 40:
        плохо(f"{н} поле ниже 40 px: {м['выс']}")
    if м["кегль"] < 16:
        плохо(f"{н} кегль поля {м['кегль']} px — iPhone увеличит страницу при нажатии")
    if ночь and (яркость(м["фон"]) > 128 or яркость(м["цвет"]) < 128):
        плохо(f"{н} ночью поле светлое или текст тёмный: фон {м['фон']}, текст {м['цвет']}")
    поле = к.locator("#homeSearch")
    поле.click()
    поле.press_sequentially(СЛОВО, delay=20)
    стр.wait_for_timeout(300)
    в = тело.evaluate("() => (" + ВЫДАЧА + ")()")
    if not в or not в["открыта"] or в["строк"] < 1:
        плохо(f"{н} по «{СЛОВО}» выдача не раскрылась: {в}")
    else:
        if в["низ"] > в["H"] + 1 or в["право"] > в["W"] or в["лево"] < 0:
            плохо(f"{н} выдача за краем экрана: {в}")
        if not в["сверху"]:
            плохо(f"{н} строку выдачи накрывает оглавление")
        if в["всего"] != 1:
            плохо(f"{н} раскрылась не одна выдача: {в['всего']}")
        if в["крестик"] != "flex":
            плохо(f"{н} крестик очистки не появился: {в['крестик']}")
    стр.screenshot(path=str(СНИМКИ / f"manual-home-search-{ш}-{'night' if ночь else 'day'}.png"))
    if not ночь:
        # крестик
        к.locator("#ch-home .hm-srch .srch-clr").click()
        стр.wait_for_timeout(200)
        п = тело.evaluate("() => [document.getElementById('homeSearch').value, (" + ВЫДАЧА + ")()]")
        if п[0] or п[1]["открыта"] or п[1]["крестик"] != "none":
            плохо(f"{н} крестик не очистил поиск: {п}")
        # Esc
        поле.press_sequentially(СЛОВО, delay=20)
        стр.wait_for_timeout(200)
        поле.press("Escape")
        стр.wait_for_timeout(200)
        if тело.evaluate("() => (" + ВЫДАЧА + ")()")["открыта"]:
            плохо(f"{н} Esc не закрыл выдачу")
        # переход к найденному
        поле.fill("")
        поле.press_sequentially(СЛОВО, delay=20)
        стр.wait_for_timeout(300)
        к.locator("#ch-home .hm-srch .srch-item").first.dispatch_event("mousedown")
        стр.wait_for_timeout(600)
        г = тело.evaluate("""(_, с) => { const ч = document.querySelector('.ch.on');
          return [ч && ч.id, ч ? ч.textContent.toLowerCase().includes(с) : false]; }""", СЛОВО)
        if not г[0] or г[0] == "ch-home" or not г[1]:
            плохо(f"{н} строка выдачи не открыла главу со словом: {г}")
        тело.evaluate("() => go('home')")
        стр.wait_for_timeout(200)
        if тело.evaluate("() => document.getElementById('homeSearch').value"):
            плохо(f"{н} на оглавлении после возврата в поле осталось слово")
        if ш >= 1000:
            м_ = к.locator("#guideSearch")
            м_.click()
            м_.press_sequentially(СЛОВО, delay=20)
            стр.wait_for_timeout(300)
            о = тело.evaluate("() => { const р = document.getElementById('srchResults'); return [р.classList.contains('open'), р.querySelectorAll('.srch-item').length]; }")
            if not о[0] or о[1] < 1:
                плохо(f"{н} поиск в меню перестал работать: {о}")
    for о in [о for о in ошибки if not any(ш_ in о for ш_ in д.ШУМ)][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def в_бою(бр, порт):
    """Оболочка одна на тест и бой: до выпуска 2.5.19 поиска на оглавлении в бою нет."""
    стр = бр.new_page(viewport={"width": 390, "height": 900})
    адрес = f"http://127.0.0.1:{порт}/__manual-probe.html?contour=prod"
    html = д.справка.достать("manual").replace("<html", '<html data-start="home"', 1)
    стр.route(адрес, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=html))
    стр.goto(адрес, wait_until="load")
    стр.wait_for_timeout(500)
    р = стр.evaluate("() => [!!document.querySelector('#ch-home .hm-cols'), !!document.getElementById('homeSearch')]")
    if not р[0] or р[1]:
        плохо(f"[бой] оглавление {р[0]}, поиск на нём {р[1]} — в бою до выпуска поиска быть не должно")
    стр.close()


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = д.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=д.хром(), args=["--no-sandbox"])
            в_бою(бр, порт)
            for ш in (390, 1440):
                for ночь in (False, True):
                    прогон(бр, порт, ш, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: на оглавлении справки строка поиска под «Что нового», выдача поверх разделов и в экране, "
          "крестик и Esc закрывают, строка выдачи открывает главу; поиск в меню работает; на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
