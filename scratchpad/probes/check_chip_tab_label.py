#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Надпись значка мини-окна от вкладки не зависит.

Константин 28.10.2026 сначала попросил назвать на значке открытую вкладку
(«Если выбран Чат, то пишем там „Чат“»), затем — через черту после подписи
(«А какая вкладка через „|“ ставь»), и следом передумал: «Стоп. Я передумал.
Название мини-окна не меняй, как сейчас подписан оставляй. По вкладке не меняй
название».

Проба держит — в каркасе, клеёном брусе и парной, на 390 и 1440 px:
  • на «Пресете», «Журнале», «Проверке» и «Чате» значок своего пресета пишет
    одно и то же — «Мой пресет», без вкладки и без черты, и подсказка для
    чтения с экрана вкладку не называет;
  • закрытое и открытое заново окно открывается на той вкладке, на которой
    его закрыли;
  • у общего пресета на любой вкладке — «Общий пресет · …»;
  • значок в кадре, подпись не обрезана.

    python3 check_chip_tab_label.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_steam_tab as п
from playwright.sync_api import sync_playwright

НАХОДКИ = []
def плохо(т): НАХОДКИ.append(т)

ЗНАЧОК = """() => { const з = document.getElementById('presetChip'), л = з.querySelector('.pc-lbl'), т = з.querySelector('.pc-body');
  const в = з.querySelector('.pc-tabname'), r = з.getBoundingClientRect();
  return { надпись: (л ? л.textContent : '') + (в ? ' ' + в.textContent.replace('|', '| ') : ''), подсказка: т ? т.getAttribute('aria-label') : '',
    обрезана: (л ? л.scrollWidth > л.clientWidth + 1 : false) || (в ? в.scrollWidth > в.clientWidth + 1 || в.getBoundingClientRect().right > r.right : false),
    вКадре: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight,
    вкладка: (document.querySelector('#presetChipCard .pc-tab[aria-selected="true"]') || {}).id || '',
    открыта: document.getElementById('presetChipCard').classList.contains('show') }; }"""

ИМЕНА = {"p": "Мой пресет", "l": "Журнал", "c": "Проверка", "m": "Чат"}
НАДПИСИ = {в: "Мой пресет" for в in ИМЕНА}


def сохранить(стр):
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
    стр.locator("#pcName").press("Enter"); стр.wait_for_timeout(2600)


def открыть_окно(стр):
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(400)


def закрыть_окно(стр):
    # Крестиком: на телефоне раскрытое окно стоит поверх значка.
    if стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.locator("#presetChipCard .pc-x").click(); стр.wait_for_timeout(300)


def прогон(бр, порт, ш, расчёт):
    н = f"[{расчёт} {ш}]"
    стр, ош = п.открыть(бр, порт, ш)
    if расчёт == "Парная":
        п.в_парную(стр)
    else:
        стр.evaluate("""async (т) => { if (т !== 'Каркас') { selectTech(т); await new Promise(r => setTimeout(r, 900)); }
          selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""", расчёт)
    сохранить(стр)
    з = стр.evaluate(ЗНАЧОК)
    if з["надпись"] != "Мой пресет":
        плохо(f"{н} сохранённый пресет: значок «{з['надпись']}», ждали «Мой пресет»"); стр.close(); return
    for в in ("l", "c", "m", "p"):
        открыть_окно(стр)
        стр.locator(f"#pcTab-{в}").click(); стр.wait_for_timeout(350)
        з = стр.evaluate(ЗНАЧОК)
        if з["надпись"] != НАДПИСИ[в] or з["обрезана"] or not з["вКадре"]:
            плохо(f"{н} вкладка «{ИМЕНА[в]}»: значок «{з['надпись']}», обрезан {з['обрезана']}, в кадре {з['вКадре']} — ждали «{НАДПИСИ[в]}»")
        if в != "p" and ИМЕНА[в] in (з["подсказка"] or ""):
            плохо(f"{н} вкладка «{ИМЕНА[в]}»: подсказка значка называет вкладку: {з['подсказка']!r}")
        # Закрыть и открыть заново — окно на той вкладке, что на значке.
        закрыть_окно(стр)
        if стр.evaluate(ЗНАЧОК)["надпись"] != НАДПИСИ[в]:
            плохо(f"{н} окно закрыто на «{ИМЕНА[в]}» — значок «{стр.evaluate(ЗНАЧОК)['надпись']}», ждали «Мой пресет»")
        открыть_окно(стр)
        з = стр.evaluate(ЗНАЧОК)
        if з["вкладка"] != f"pcTab-{в}":
            плохо(f"{н} значок «{ИМЕНА[в]}», а окно открылось на {з['вкладка']}")
        if ш == 1440 and в == "m":
            стр.screenshot(path=f"/tmp/chip-tab-{расчёт}-{ш}.png")
    # Общий пресет: и на «Пресете», и на «Чате» — «Общий пресет · …».
    if расчёт == "Каркас":
        открыть_окно(стр)
        стр.locator("#presetChipCard [data-act='publish']").click(); стр.wait_for_timeout(1500)
        открыть_окно(стр)
        стр.locator("#presetChipCard [data-act='to-shared']").click(); стр.wait_for_timeout(800)
        открыть_окно(стр)
        з = стр.evaluate(ЗНАЧОК)
        if not з["надпись"].startswith("Общий пресет"):
            плохо(f"{н} общий пресет на «Пресете»: значок «{з['надпись']}»")
        стр.locator("#pcTab-m").click(); стр.wait_for_timeout(350)
        з = стр.evaluate(ЗНАЧОК)
        if not з["надпись"].startswith("Общий пресет") or "|" in з["надпись"] or "Чат" in (з["подсказка"] or ""):
            плохо(f"{н} общий пресет на «Чате»: значок «{з['надпись']}», подсказка {з['подсказка']!r} — ждали «Общий пресет · …» без вкладки")
        закрыть_окно(стр)
        стр.screenshot(path=f"/tmp/chip-tab-shared-{ш}.png")
    for е in [е for е in ош if "supabase" not in е.lower()][:3]:
        плохо(f"{н} ошибка страницы: {е[:160]}")
    стр.close()


def main():
    с, порт = п.м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=п.м.хром())
            for расчёт in ("Каркас", "Клеёный брус", "Парная"):
                for ш in (390, 1440):
                    прогон(бр, порт, ш, расчёт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: надпись значка мини-окна от вкладки не зависит — «Мой пресет» на «Пресете», «Журнале», «Проверке» "
          "и «Чате», у общего — «Общий пресет · …», подсказка вкладку не называет; окно открывается на вкладке, где его "
          "закрыли — в каркасе, клеёном брусе и парной, на 390 и 1440 px.")


if __name__ == "__main__":
    main()
