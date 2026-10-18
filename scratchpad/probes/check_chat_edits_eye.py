#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Проверка»: глаз в шапке «Правки из чата» скрывает и показывает список.

Константин 18.10.2026, снимком вкладки «Проверка»: «Тут добавь глаз, чтобы
можно было скрывать правки из чата».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • глаз стоит в шапке группы после «N из M», не ближе 6 px к числу и к
    краю карточки; нарисован мелко (не выше 18 px), а поле нажатия — не
    меньше 44 px;
  • нажатие прячет список правок: шапка и «N из M» остаются, число на
    вкладке «Проверка» то же (открытая правка не перестаёт быть открытой);
  • выбор помнится: после закрытия и открытия мини-окна список скрыт;
    второе нажатие возвращает его;
  • вёрстка на 390 и 1440 — как в пробе чата.

    python3 check_chat_edits_eye.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


ПРАВКИ = """() => { const т = window.__ТАБЛИЦЫ.preset_messages;
  т[0].review_state = 'done'; т[2].review_state = 'open'; т[3].review_state = 'open';
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  try { localStorage.removeItem('banya_chat_edits_hidden'); } catch (e) {} _правкиЧатаСкрыты = false; }"""

ГРУППА = """() => { const к = document.getElementById('presetChipCard'), г = к.querySelector('.pc-grp'), глаз = к.querySelector('[data-act="ch-hide"]');
  if (!г || !глаз) return null;
  const кр = к.getBoundingClientRect(), cs = getComputedStyle(к), край = кр.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
  const р = глаз.getBoundingClientRect(), с = getComputedStyle(глаз, '::before'), число = г.querySelector('.pc-grp-r > span').getBoundingClientRect();
  return { шапка: г.innerText.replace(/\\s+/g, ' ').trim().toLowerCase(), пунктов: к.querySelectorAll('.pc-pr li').length, нажат: глаз.getAttribute('aria-pressed'),
    подпись: глаз.getAttribute('aria-label'), рисунок: Math.round(р.height),
    поле: [Math.round(р.width - parseFloat(с.left) - parseFloat(с.right)), Math.round(р.height - parseFloat(с.top) - parseFloat(с.bottom))],
    доЧисла: Math.round(р.left - число.right), доКрая: Math.round(край - р.right),
    счёт: +(((к.querySelector('#pcTab-c .pc-cnt') || {}).textContent) || 0) }; }"""


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    стр.evaluate(ПРАВКИ)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(600); ч.вкладка(стр, "c"); стр.wait_for_timeout(500)
    до = стр.evaluate(ГРУППА)
    if not до or до["пунктов"] != 3 or "1 из 3" not in до["шапка"] or до["нажат"] != "false" or до["подпись"] != "Скрыть правки из чата" \
            or до["рисунок"] > 18 or min(до["поле"]) < 43.5 or до["доЧисла"] < 6 or до["доКрая"] < 0:
        плохо(f"{н} глаз в шапке правок: {до}")
    ч.вёрстка(стр, н, "«Проверка» с глазом")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"eye-{ш}{'-n' if ночь else ''}.png"))
    стр.locator("#presetChipCard [data-act='ch-hide']").click(); стр.wait_for_timeout(300)
    п = стр.evaluate(ГРУППА)
    if not п or п["пунктов"] or "1 из 3" not in п["шапка"] or п["нажат"] != "true" or п["подпись"] != "Показать правки из чата" or (до and п["счёт"] != до["счёт"]):
        плохо(f"{н} после нажатия: {п} (до {до})")
    ч.вёрстка(стр, н, "«Проверка», правки скрыты")
    стр.screenshot(path=str(СНИМКИ / f"eye-off-{ш}{'-n' if ночь else ''}.png"))
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300); ч.открыть(стр); стр.wait_for_timeout(300)
    п = стр.evaluate(ГРУППА)
    if not п or п["пунктов"] or стр.evaluate("() => localStorage.getItem('banya_chat_edits_hidden')") != "1":
        плохо(f"{н} выбор не запомнился: {п}")
    стр.locator("#presetChipCard [data-act='ch-hide']").click(); стр.wait_for_timeout(300)
    п = стр.evaluate(ГРУППА)
    if not п or п["пунктов"] != 3 or п["нажат"] != "false":
        плохо(f"{н} второе нажатие не вернуло список: {п}")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, False)
                прогон(бр, порт, 390, 844, True)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: глаз в шапке правок из чата — мелкий, с полем 44 px, прячет и возвращает список, число и счёт на вкладке те же, выбор помнится; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
