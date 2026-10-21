#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск на оглавлении справки.

Константин 19.10.2026, снимком оглавления справки на телефоне с чертой под
«Что нового»: «Сюда на главную тоже размести поиск, который есть в боковом
меню». На телефоне меню спрятано, и до поиска было два нажатия.

Следом, тем же днём, снимком поиска в операциях Adesk: «Так не пойдёт.
Сделай аккуратную. Вот как тут сделай» — кнопкой, раскрывающейся в поле.

Проба держит, через калькулятор (тест), на 390 и 1440, днём и ночью:
  • у заголовка «Справка» справа — кнопка поиска 40 px (поле нажатия 44),
    у правого края колонки, по центру строки заголовка и не ближе 8 px к
    крестику окна справки (на телефоне он стоял прямо на ней); поле свёрнуто
    и в порядок Tab не входит;
  • нажатие раскрывает поле: шире 150 px, в фокусе, кегль 16 px (мельче
    iPhone увеличивает страницу), в колонке и не наезжает на заголовок;
    ночью поле не белое, текст в нём светлый;
  • набранное слово раскрывает выдачу во всю ширину колонки под строкой
    заголовка, выдача в экране и лежит поверх разделов (её строку можно
    нажать); крестик появляется и очищает, поле остаётся открытым;
  • Esc и пустое поле, потерявшее фокус, сворачивают его в кнопку;
  • нажатие на строку выдачи открывает главу, где это слово есть; на
    оглавлении после возврата поле свёрнуто и пустое;
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
  const п = document.getElementById('homeSearch'), о = document.getElementById('homeSrch');
  if (!п || !о) return null;
  const б = о.querySelector('.hm-srch-b'), r = о.getBoundingClientRect(), rb = б.getBoundingClientRect();
  // Заголовок — по самим буквам, а не по коробке: ужатая коробка уже текста,
  // и поле, наехавшее на «Справка», по ней выглядело бы свободным.
  const тэ = document.querySelector('#ch-home .hm-t'), д_ = document.createRange(); д_.selectNodeContents(тэ);
  const тб = тэ.getBoundingClientRect(), тр = [...д_.getClientRects()].reduce((м_, р) => Math.max(м_, р.right), 0);
  const т = { right: Math.max(тб.right, тр), top: тб.top, bottom: тб.bottom };
  const кол = document.querySelector('#ch-home .hm-cols').getBoundingClientRect();
  const с = getComputedStyle(п), со = getComputedStyle(о), сб = getComputedStyle(б, '::before');
  return { открыто: о.classList.contains('open'), л: r.left, п: r.right, в: r.top, н: r.bottom, ш: r.width, выс: r.height,
    кнВыс: rb.height - (parseFloat(сб.top) || 0) - (parseFloat(сб.bottom) || 0), кнШир: rb.width - (parseFloat(сб.left) || 0) - (parseFloat(сб.right) || 0),
    тП: т.right, тЦ: (т.top + т.bottom) / 2, колЛ: кол.left, колП: кол.right, W: innerWidth,
    видно: parseFloat(с.opacity), таб: п.tabIndex, фокус: document.activeElement === п,
    кегль: parseFloat(с.fontSize), фон: со.backgroundColor, цвет: с.color, знач: п.value };
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
    мера = lambda: тело.evaluate("() => (" + МЕРА + ")()")
    м = мера()
    if not м:
        плохо(f"{н} на оглавлении нет кнопки поиска"); стр.close(); return
    if м["открыто"] or м["видно"] > 0.01 or м["таб"] != -1:
        плохо(f"{н} поле поиска не свёрнуто до нажатия: {м}")
    if м["кнВыс"] < 43.5 or м["кнШир"] < 43.5 or м["выс"] < 39.5 or м["выс"] > 42:
        плохо(f"{н} кнопка поиска {м['выс']} px, поле нажатия {м['кнШир']}×{м['кнВыс']}")
    if м["п"] > м["колП"] + 1 or м["колП"] - м["п"] > 40:
        плохо(f"{н} кнопка поиска не у правого края колонки: {round(м['п'])} против {round(м['колП'])}")
    # Крестик окна справки стоит поверх неё в правом верхнем углу: кнопка не
    # под ним и не вплотную (было: на телефоне крестик накрывал кнопку).
    кр = стр.evaluate("""() => { const б = document.getElementById('manualCloseBtn'); if (!б || !б.offsetParent) return null;
      const r = б.getBoundingClientRect(), ф = [...document.querySelectorAll('iframe')].find(f => f.offsetParent && f.getBoundingClientRect().width > 200).getBoundingClientRect();
      return { л: r.left - ф.left, п: r.right - ф.left, в: r.top - ф.top, н: r.bottom - ф.top }; }""")
    if кр:
        зазор = max(кр["л"] - м["п"], м["л"] - кр["п"], кр["в"] - м["н"], м["в"] - кр["н"])
        if зазор < 8:
            плохо(f"{н} кнопка поиска под крестиком окна или вплотную к нему: зазор {round(зазор)} px")
    if abs((м["в"] + м["н"]) / 2 - м["тЦ"]) > 3:
        плохо(f"{н} кнопка поиска не по центру строки заголовка")
    if not ночь:
        стр.screenshot(path=str(СНИМКИ / f"manual-home-search-closed-{ш}.png"))
    к.locator("#homeSrch .hm-srch-b").evaluate("б => б.click()")
    стр.wait_for_timeout(350)
    м = мера()
    if not м["открыто"] or м["ш"] < 150 or not м["фокус"] or м["видно"] < 0.99:
        плохо(f"{н} нажатие не раскрыло поле: {м}")
    if м["л"] < м["тП"] + 6 or м["п"] > м["колП"] + 1 or м["п"] > м["W"]:
        плохо(f"{н} раскрытое поле наезжает на заголовок или выходит за колонку: {round(м['л'])}…{round(м['п'])}, заголовок до {round(м['тП'])}")
    if м["кегль"] < 16:
        плохо(f"{н} кегль поля {м['кегль']} px — iPhone увеличит страницу при нажатии")
    if ночь and (яркость(м["фон"]) > 128 or яркость(м["цвет"]) < 128):
        плохо(f"{н} ночью поле светлое или текст тёмный: фон {м['фон']}, текст {м['цвет']}")
    поле = к.locator("#homeSearch")
    поле.press_sequentially(СЛОВО, delay=20)
    стр.wait_for_timeout(300)
    в = тело.evaluate("() => (" + ВЫДАЧА + ")()")
    if not в or not в["открыта"] or в["строк"] < 1:
        плохо(f"{н} по «{СЛОВО}» выдача не раскрылась: {в}")
    else:
        if в["низ"] > в["H"] + 1 or в["право"] > в["W"] or в["лево"] < 0:
            плохо(f"{н} выдача за краем экрана: {в}")
        if abs(в["лево"] - м["колЛ"]) > 1.5 or abs(в["право"] - м["колП"]) > 1.5:
            плохо(f"{н} выдача не во всю колонку: {round(в['лево'])}…{round(в['право'])} при колонке {round(м['колЛ'])}…{round(м['колП'])}")
        if not в["сверху"]:
            плохо(f"{н} строку выдачи накрывает оглавление")
        if в["всего"] != 1:
            плохо(f"{н} раскрылась не одна выдача: {в['всего']}")
        if в["крестик"] != "flex":
            плохо(f"{н} крестик очистки не появился: {в['крестик']}")
    стр.screenshot(path=str(СНИМКИ / f"manual-home-search-{ш}-{'night' if ночь else 'day'}.png"))
    if not ночь:
        # крестик: очищает, поле остаётся открытым
        к.locator("#ch-home .hm-srch .srch-clr").evaluate("б => б.click()")
        стр.wait_for_timeout(200)
        п = тело.evaluate("() => [document.getElementById('homeSearch').value, (" + ВЫДАЧА + ")()]")
        if п[0] or п[1]["открыта"] or п[1]["крестик"] != "none" or not мера()["открыто"]:
            плохо(f"{н} крестик не очистил поиск или свернул поле: {п}")
        # Esc сворачивает
        поле.press_sequentially(СЛОВО, delay=20)
        стр.wait_for_timeout(200)
        поле.press("Escape")
        стр.wait_for_timeout(350)
        м = мера()
        if тело.evaluate("() => (" + ВЫДАЧА + ")()")["открыта"] or м["открыто"] or м["знач"]:
            плохо(f"{н} Esc не свернул поиск: {м}")
        # пустое поле без фокуса сворачивается
        к.locator("#homeSrch .hm-srch-b").evaluate("б => б.click()"); стр.wait_for_timeout(250)
        к.locator("#ch-home .hm-s").click(); стр.wait_for_timeout(450)
        if мера()["открыто"]:
            плохо(f"{н} пустое поле не свернулось, когда ушёл фокус")
        # переход к найденному
        к.locator("#homeSrch .hm-srch-b").evaluate("б => б.click()"); стр.wait_for_timeout(250)
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
        м = мера()
        if м["знач"] or м["открыто"]:
            плохо(f"{н} на оглавлении после возврата поле не свёрнуто или в нём слово: {м}")
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
    """Оболочка одна на тест и бой: с выпуска 2.5.19 (21.10.2026) поиск на оглавлении есть и в бою."""
    стр = бр.new_page(viewport={"width": 390, "height": 900})
    адрес = f"http://127.0.0.1:{порт}/__manual-probe.html?contour=prod"
    html = д.в_тоне(бр, порт, д.справка.достать("manual").replace("<html", '<html data-start="home"', 1))
    стр.route(адрес, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=html))
    стр.goto(адрес, wait_until="load")
    стр.wait_for_timeout(500)
    р = стр.evaluate("() => [!!document.querySelector('#ch-home .hm-cols'), !!document.getElementById('homeSearch')]")
    if not р[0] or not р[1]:
        плохо(f"[бой] оглавление {р[0]}, поиск на нём {р[1]} — с выпуска 2.5.19 поиск в бою есть")
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
    print("Чисто: на оглавлении справки поиск — кнопкой у заголовка, раскрывается в поле; выдача во всю колонку поверх "
          "разделов и в экране, крестик очищает, Esc и пустое поле без фокуса сворачивают, строка выдачи открывает главу; "
          "поиск в меню работает; на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
