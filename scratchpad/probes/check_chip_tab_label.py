#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок мини-окна называет вкладку, с которой окно откроется.

Константин 28.10.2026, снимком значка «Мой пресет» и вкладок мини-окна: «Тут
пиши, какой раздел выбран в мини-окне. Если выбран Чат, то пишем там „Чат“.
Так будет понятно, при нажатии на кнопку мини-окна, какой раздел сразу
откроется. Это примени во всех технологиях/расчётах».

И следом, снимками значков «Мой пресет», «Общий пресет · Максим Г.» и «Чат»:
«Тут вот эти подписи пресетов надо сохранить. А какая вкладка через „|“ ставь».

Проба держит — в каркасе, клеёном брусе и парной:
  • на вкладке «Пресет» значок прежний — «Мой пресет»; на «Журнале»,
    «Проверке» и «Чате» — подпись пресета и вкладка через черту: «Мой пресет |
    Чат», и подсказка для чтения с экрана вкладку тоже называет;
  • значок меняет надпись сразу при смене вкладки, без иных событий;
  • закрытое и открытое заново окно открывается ровно на той вкладке, которую
    называет значок;
  • у общего пресета на «Пресете» — «Общий пресет · …», на «Чате» —
    «Общий пресет · … | Чат»;
  • значок в кадре на 390 и 1440 px; вкладка видна целиком, а если места мало,
    сжимается подпись пресета.

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
НАДПИСИ = {"p": "Мой пресет", "l": "Мой пресет | Журнал", "c": "Мой пресет | Проверка", "m": "Мой пресет | Чат"}


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
        if в != "p" and f"«{ИМЕНА[в]}»" not in (з["подсказка"] or ""):
            плохо(f"{н} вкладка «{ИМЕНА[в]}»: подсказка значка её не называет: {з['подсказка']!r}")
        # Закрыть и открыть заново — окно на той вкладке, что на значке.
        закрыть_окно(стр)
        if стр.evaluate(ЗНАЧОК)["надпись"] != НАДПИСИ[в]:
            плохо(f"{н} окно закрыто на «{ИМЕНА[в]}» — значок забыл вкладку: «{стр.evaluate(ЗНАЧОК)['надпись']}»")
        открыть_окно(стр)
        з = стр.evaluate(ЗНАЧОК)
        if з["вкладка"] != f"pcTab-{в}":
            плохо(f"{н} значок «{ИМЕНА[в]}», а окно открылось на {з['вкладка']}")
        if ш == 1440 and в == "m":
            стр.screenshot(path=f"/tmp/chip-tab-{расчёт}-{ш}.png")
    # Общий пресет: на «Пресете» — «Общий пресет · …», на «Чате» — «Общий пресет · … | Чат».
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
        if not (з["надпись"].startswith("Общий пресет") and з["надпись"].endswith(" | Чат")) or "«Чат»" not in (з["подсказка"] or "") \
                or з["обрезана"] and "| Чат" not in з["надпись"] or not з["вКадре"]:
            плохо(f"{н} общий пресет на «Чате»: значок «{з['надпись']}», подсказка {з['подсказка']!r}, в кадре {з['вКадре']}")
        # Длинная подпись на узком экране: сжимается подпись, вкладка видна целиком.
        в = стр.evaluate("""() => { _значокНадпись = null; const sp = _sharedPresets.find(p => p.short_code === _activeSharedCode);
          if (sp) { sp.author_name = 'Константинопольская-Ростовская'; sp.author_id = 'чужой'; } отрисоватьЗначокПресета();
          const з = document.getElementById('presetChip'), т = з.querySelector('.pc-tabname'), r = з.getBoundingClientRect(), тр = т.getBoundingClientRect();
          return { текст: т.textContent, целиком: т.scrollWidth <= т.clientWidth + 1 && тр.right <= r.right + 0.5, вКадре: r.left >= 0 && r.right <= innerWidth }; }""")
        стр.screenshot(path=f"/tmp/chip-tab-long-{ш}.png")
        if в["текст"] != "|Чат" or not в["целиком"] or not в["вКадре"]:
            плохо(f"{н} длинный автор: вкладка {в} — ждали «| Чат» целиком и значок в кадре")
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
    print("Чисто: значок мини-окна хранит подпись пресета и называет вкладку через черту — «Мой пресет» на «Пресете», "
          "«Мой пресет | Журнал», «| Проверка», «| Чат» на остальных — в каркасе, клеёном брусе и парной, на 390 и 1440 px; "
          "меняется сразу, окно открывается на названной вкладке; у общего пресета — «Общий пресет · … | Чат», при длинном "
          "авторе сжимается подпись, вкладка видна целиком.")


if __name__ == "__main__":
    main()
