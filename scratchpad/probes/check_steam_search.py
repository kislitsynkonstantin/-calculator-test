#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск по опциям в парной.

Константин 28.10.2026: «Сделай поиск по опциям в парной, сейчас не работает».
До этого кнопка поиска в парной отвечала «в следующей сборке».

Проба держит:
  • поиск открывается в парной и находит её строки по названию и в чужой
    раскладке («jkm[» — «ольх»);
  • нажатие по строке опции включает её в расчёт парной, итог меняется; второе
    — выключает;
  • строка базы отмечена и снимается поиском, как нажатием в расчёте; строка
    под замком (обрешётка) и сборка премиальной — видны, но не переключаются;
  • «Выбранные» показывают отмеченное в парной, подвал считает опции парной;
  • «Перейти» ведёт к строке в расчёте; окно поиска на 390 px не шире экрана.

    python3 check_steam_search.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_steam_tab as п
from playwright.sync_api import sync_playwright

НАХОДКИ = []
def плохо(т): НАХОДКИ.append(т)

СТРОКИ = """() => [...document.querySelectorAll('#optSearchResults .ops-row')].map(р => ({
  имя: р.querySelector('.ops-name').textContent, отмечена: р.querySelector('.ops-chk').checked,
  выкл: р.querySelector('.ops-chk').disabled }))"""
ИТОГ = "() => Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, ''))"


def искать(стр, т):
    стр.fill("#optSearchInput", т); стр.wait_for_timeout(250)
    return стр.evaluate(СТРОКИ)


def строка(стр, часть):
    return стр.locator("#optSearchResults .ops-row", has_text=часть).first


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    стр, ош = п.открыть(бр, порт, ш)
    п.в_парную(стр)
    тосты = []
    стр.evaluate("() => { window.__т = []; const был = window.showToast; window.showToast = function (т) { window.__т.push(String(т)); return был.apply(this, arguments); }; }")
    стр.evaluate("() => openOptSearch()"); стр.wait_for_timeout(300)
    if not стр.evaluate("() => getComputedStyle(document.getElementById('optSearchOverlay')).display !== 'none'"):
        плохо(f"{н} поиск по опциям в парной не открылся: {стр.evaluate('() => window.__т')}")
        стр.close(); return
    р = искать(стр, "ольх")
    имена = [х["имя"] for х in р]
    if not any("Вагонка из ольхи" in и for и in имена) or not any("Полки из ольхи" in и for и in имена):
        плохо(f"{н} «ольх» в парной: {имена}")
    if [х["имя"] for х in искать(стр, "jkm[")] != имена:
        плохо(f"{н} «jkm[» (раскладка) находит не то же, что «ольх»")
    искать(стр, "ольх")
    до = стр.evaluate(ИТОГ)
    строка(стр, "Вагонка из ольхи").click(); стр.wait_for_timeout(300)
    if not стр.evaluate("() => ПАР.вкл.has('olha')") or стр.evaluate(ИТОГ) <= до:
        плохо(f"{н} нажатие по «Вагонка из ольхи» не включило опцию: вкл {стр.evaluate('() => [...ПАР.вкл]')}, итог {до} → {стр.evaluate(ИТОГ)}")
    if not next((х for х in стр.evaluate(СТРОКИ) if "Вагонка из ольхи" in х["имя"]), {}).get("отмечена"):
        плохо(f"{н} строка «Вагонка из ольхи» в поиске не отмечена после включения")
    строка(стр, "Вагонка из ольхи").click(); стр.wait_for_timeout(300)
    if стр.evaluate("() => ПАР.вкл.has('olha')") or стр.evaluate(ИТОГ) != до:
        плохо(f"{н} второе нажатие не сняло ольху: итог {стр.evaluate(ИТОГ)}, ждали {до}")
    # Строка базы: дверь — снимается поиском.
    р = искать(стр, "дверь стеклянная")
    дв = next((х for х in р if "Дверь стеклянная" in х["имя"]), None)
    if not дв or not дв["отмечена"] or дв["выкл"]:
        плохо(f"{н} дверь (строка базы) в поиске: {дв}")
    else:
        строка(стр, "Дверь стеклянная").click(); стр.wait_for_timeout(300)
        if not стр.evaluate("() => ПАР.снятыСтроки.has('door')") or стр.evaluate(ИТОГ) >= до:
            плохо(f"{н} поиск не снял дверь из базы")
        строка(стр, "Дверь стеклянная").click(); стр.wait_for_timeout(300)
    # Под замком и сборка премиальной — не переключаются.
    for часть, к in (("Обрешётка", "obr"), ("Сборка премиальной", "premium")):
        р = искать(стр, часть.lower())
        х = next((х for х in р if часть in х["имя"]), None)
        if not х or not х["выкл"]:
            плохо(f"{н} «{часть}» в поиске переключается, а не должна: {х}")
    # «Выбранные» и подвал.
    стр.evaluate("() => { ПАР.вкл.add('maslo'); calc(); }")
    стр.evaluate("() => setOptSearchFilter('on')"); стр.wait_for_timeout(250)
    стр.fill("#optSearchInput", ""); стр.wait_for_timeout(250)
    р = стр.evaluate(СТРОКИ)
    if not any("маслом" in х["имя"] for х in р) or any("ольхи" in х["имя"] for х in р):
        плохо(f"{н} «Выбранные» в парной: {[х['имя'] for х in р][:8]}")
    подвал = стр.evaluate("() => document.getElementById('optSearchFoot').textContent")
    if "Выбрано опций: 1" not in подвал:
        плохо(f"{н} подвал поиска в парной: «{подвал}» — ждали одну опцию")
    if стр.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"):
        плохо(f"{н} окно поиска шире экрана")
    стр.screenshot(path=f"/tmp/steam-search-{ш}.png")
    # «Перейти» — к строке в расчёте.
    стр.evaluate("() => setOptSearchFilter('all')")
    искать(стр, "масло")
    строка(стр, "маслом").locator(".ops-go").click(); стр.wait_for_timeout(900)
    if стр.evaluate("() => getComputedStyle(document.getElementById('optSearchOverlay')).display !== 'none'") or \
       not стр.evaluate("() => { const р = document.getElementById('lbl_par_maslo').getBoundingClientRect(); return р.top >= 0 && р.bottom <= innerHeight; }"):
        плохо(f"{н} «Перейти» не привело к строке масла в расчёте")
    for е in [е for е in ош if "supabase" not in е.lower()][:3]:
        плохо(f"{н} ошибка страницы: {е[:160]}")
    стр.close()


def main():
    с, порт = п.м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=п.м.хром())
            for ш in (1440, 390):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: поиск по опциям работает в парной — находит её строки и в чужой раскладке, включает и снимает опции, "
          "снимает строки базы, замок и сборку премиальной не трогает, «Выбранные» и подвал считают парную, «Перейти» ведёт к строке.")


if __name__ == "__main__":
    main()
