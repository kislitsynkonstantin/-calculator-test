#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка: свои позиции без цвета — один пункт со списком внутри.

Константин 30.09.2026, снимком вкладки «Проверка»: «сделай общий пункт
выделить позиции цветом и чтобы можно было провалиться в список, где все эти
ручные позиции указаны».

Проба на 390 и 1440 держит:
  • три свои позиции без цвета в разных разделах — один пункт «Выделить свои
    позиции цветом» с числом 3 и названиями разделов, а не три пункта;
  • список закрыт; нажатие раскрывает его — три строки с названиями позиций,
    стрелка повёрнута; ничего не вылезает за карточку;
  • строка списка ведёт к своей позиции: карточка закрывается, позиция на
    экране и подсвечена;
  • выделили две — в пункте число 1.

    python3 check_check_group.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИД = """() => { const п = document.getElementById('pcPane-c'); if (!п) return null; const г = п.querySelector('.pc-ck-grp'); const r = document.getElementById('presetChipCard').getBoundingClientRect();
  const вылез = [...п.querySelectorAll('*')].filter(э => { const q = э.getBoundingClientRect(); return q.width && (q.right > r.right + .5 || q.left < r.left - .5); }).length;
  return { групп: п.querySelectorAll('.pc-ck-grp').length, пунктов: [...п.querySelectorAll('.pc-ck > li')].map(л => л.querySelector('.pc-ck-tx').textContent.trim()),
    число: г ? (г.querySelector('.pc-ck-n') || {}).textContent : null, разделы: г ? г.querySelector('.pc-ck-sx').textContent : '',
    открыт: !!(г && г.classList.contains('open')), строк: г ? [...г.querySelectorAll('.pc-ck-sub button')].filter(б => б.getBoundingClientRect().height > 0).length : 0,
    имена: г ? [...г.querySelectorAll('.pc-ck-sub .pc-ck-tx')].map(т => т.textContent.trim()) : [], вылез }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.evaluate("""() => { const д = (р, ид, имя) => { customOptions[р] = customOptions[р] || []; customOptions[р].push({ id: ид, name: имя, price: 1000, checked: true }); };
      д('foundation', 'гр1', 'Демонтаж старого фундамента'); д('interior', 'гр2', 'Полка над дверью'); д('extra', 'гр3', 'Навес для дров');
      renderOptionSections(); calc(); }""")
    стр.wait_for_timeout(500)
    к.открыть(стр); к.вкладка(стр, "c"); стр.wait_for_timeout(400)
    с = стр.evaluate(ВИД)
    if not с or с["групп"] != 1 or с["число"] != "3" or any(т.startswith("Выделить свою") for т in с["пунктов"]) or с["открыт"] or с["строк"]:
        НАХОДКИ.append(f"{н} до раскрытия: {с}")
    elif not all(x in с["разделы"] for x in ("Фундамент", "Внутренняя отделка")):
        НАХОДКИ.append(f"{н} у пункта не названы разделы: {с['разделы']}")
    стр.locator('#pcPane-c [data-act="ck-grp"]').click(); стр.wait_for_timeout(400)
    с = стр.evaluate(ВИД)
    if not с["открыт"] or с["строк"] != 3 or "Полка над дверью" not in с["имена"] or с["вылез"]:
        НАХОДКИ.append(f"{н} после раскрытия: {с}")
    стр.screenshot(path=str(м.СНИМКИ / f"check-group-{ш}.png"))
    # Строка списка ведёт к позиции.
    стр.locator('#pcPane-c .pc-ck-sub button').nth(1).click(); стр.wait_for_timeout(1200)
    р = стр.evaluate("""() => { const э = document.getElementById('lbl_custom_гр2'); if (!э) return null; const q = э.getBoundingClientRect();
      return { видна: q.top >= 0 && q.bottom <= innerHeight, вспышка: э.classList.contains('pc-flash-row'), карточка: document.getElementById('presetChipCard').classList.contains('show') }; }""")
    if not р or not р["видна"] or not р["вспышка"] or р["карточка"]:
        НАХОДКИ.append(f"{н} строка списка не привела к позиции: {р}")
    # Выделили две — осталась одна.
    стр.evaluate("() => { highlightedOpts.add('custom_гр1'); highlightedOpts.add('custom_гр3'); calc(); }")
    к.открыть(стр); к.вкладка(стр, "c"); стр.wait_for_timeout(400)
    с = стр.evaluate(ВИД)
    if not с or с["число"] != "1":
        НАХОДКИ.append(f"{н} после выделения двух: {с}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 390, 844)
            прогон(бр, порт, 1440, 900)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: свои позиции без цвета — один пункт с числом и разделами; раскрывается списком позиций, строка "
          "ведёт к позиции и подсвечивает её; выделенные уходят из числа — на 390 и 1440.")


if __name__ == "__main__":
    главная()
