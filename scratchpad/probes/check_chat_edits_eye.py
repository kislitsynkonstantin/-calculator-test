#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Проверка»: глаз и птичка в шапке «Правки из чата».

Константин 18.10.2026, двумя снимками вкладки «Проверка»: «Тут добавь глаз,
чтобы можно было скрывать правки из чата» и «И тут добавь птичку, в целом
сворачивать все ручные правки (когда скрыты или не скрыты)». Глаз прячет
выполненные правки, птичка сворачивает весь список.

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • глаз и птичка — после плашки «N осталось», нарисованы в 28 px (шапка
    раздела — заголовком, вариант А макета check-sections-v2, 20.10.2026); поле
    нажатия глаза — 44 px, птички — не меньше 32 по ширине и 44 по высоте;
    поля не наезжают друг на друга, нажатие в зазоре между значками попадает
    в ближний; птичка не ближе края карточки, вкладка вбок не ходит;
  • глаз прячет выполненные правки, открытые остаются; все выполнены —
    строка «Выполненные правки скрыты»; число «из» и счёт вкладки те же;
  • птичка сворачивает весь список, при глазе и без него; глаз при свёрнутом
    списке его не разворачивает;
  • выбор глаза и птички помнится после закрытия и открытия мини-окна;
  • птичка «Автоматической проверки» — мелкая, поле нажатия 32×44, в
    карточке; сворачивает итог, пункты и подсказку, число в шапке остаётся,
    фокус на птичке; выбор помнится;
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
  try { localStorage.removeItem('banya_chat_edits_done_hidden'); localStorage.removeItem('banya_chat_edits_folded'); } catch (e) {} _правкиЧатаСкрыты = false; _правкиЧатаСвёрнуты = false; }"""

ГРУППА = """() => { const к = document.getElementById('presetChipCard'), г = к.querySelector('.pc-grp'), глаз = к.querySelector('[data-act="ch-hide"]'), пт = к.querySelector('[data-act="ch-fold"]');
  if (!г || !глаз || !пт) return null;
  const кр = к.getBoundingClientRect(), cs = getComputedStyle(к), край = кр.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
  const поле = э => { const р = э.getBoundingClientRect(), с = getComputedStyle(э, '::before');
    return { l: р.left + parseFloat(с.left), r: р.right - parseFloat(с.right), t: р.top + parseFloat(с.top), b: р.bottom - parseFloat(с.bottom), р }; };
  const пг = поле(глаз), пп = поле(пт), число = г.querySelector('.pc-sec-pill').getBoundingClientRect(), пане = к.querySelector('.pc-pane.on');
  return { шапка: г.innerText.replace(/\\s+/g, ' ').trim().toLowerCase(), пунктов: к.querySelectorAll('.pc-pr li').length,
    скрыто: !!к.querySelector('.pc-pr-none'), глаз: глаз.getAttribute('aria-pressed'), развёрнут: пт.getAttribute('aria-expanded'),
    рисунок: Math.round(Math.max(пг.р.height, пп.р.height)), полеГлаза: [Math.round(пг.r - пг.l), Math.round(пг.b - пг.t)],
    полеПтички: [Math.round(пп.r - пп.l), Math.round(пп.b - пп.t)], наезд: Math.round(пг.r - пп.l), доЧисла: Math.round(пг.р.left - число.right),
    доКрая: Math.round(край - пп.r), вбок: пане ? пане.scrollWidth - пане.clientWidth : 0,
    зазор: [Math.round(пг.р.right), Math.round(пп.р.left), Math.round((пг.р.top + пг.р.bottom) / 2)],
    счёт: +(((к.querySelector('#pcTab-c .pc-cnt') || {}).textContent) || 0),
    линия: [...к.querySelectorAll('.pc-sec')].map(с => parseFloat(getComputedStyle(с).borderBottomWidth)),
    // Название раздела — в одну строку и не обрезано многоточием.
    строка: [...к.querySelectorAll('.pc-sec-t')].map(т => т.scrollWidth <= т.clientWidth + 1 && т.getBoundingClientRect().height < parseFloat(getComputedStyle(т).fontSize) * 1.7) }; }"""


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    стр.evaluate(ПРАВКИ)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(600); ч.вкладка(стр, "c"); стр.wait_for_timeout(500)
    г = lambda: стр.evaluate(ГРУППА)
    до = г()
    if not до or до["пунктов"] != 3 or "2 осталось" not in до["шапка"] or до["глаз"] != "false" or до["развёрнут"] != "true" or до["рисунок"] > 28 \
            or min(до["полеГлаза"]) < 43.5 or до["полеПтички"][0] < 31.5 or до["полеПтички"][1] < 43.5 or до["наезд"] > 0 \
            or до["доЧисла"] < 6 or до["доКрая"] < 0 or до["вбок"] > 0:
        плохо(f"{н} глаз и птичка в шапке: {до}")
    ч.вёрстка(стр, н, "«Проверка» с глазом и птичкой")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"eye-{ш}{'-n' if ночь else ''}.png"))
    if not до:
        стр.close(); return
    # Нажатие в зазоре: левее середины — глаз, правее — птичка.
    л, п_, y = до["зазор"]
    сер = (л + п_) / 2
    стр.mouse.click(сер - 1, y); стр.wait_for_timeout(300)
    а = г()
    if not а or а["глаз"] != "true" or а["развёрнут"] != "true" or а["пунктов"] != 2 or "2 осталось" not in а["шапка"] or а["счёт"] != до["счёт"]:
        плохо(f"{н} глаз (нажатие в зазоре у глаза) — выполненные спрятаны, открытые на месте: {а}")
    стр.mouse.click(сер + 1, y); стр.wait_for_timeout(300)
    б = г()
    if not б or б["развёрнут"] != "false" or б["глаз"] != "true" or б["пунктов"] or б["скрыто"] or б["счёт"] != до["счёт"]:
        плохо(f"{н} птичка (нажатие в зазоре у птички) при глазе — список свёрнут: {б}")
    if до and not all(до["строка"]):
        плохо(f"{н} название раздела не в одну строку или обрезано: {до['строка']}")
    # Вариант А: зелёная черта 2 px только под открытым разделом, под свёрнутым — 1 px.
    if до and б and (до["линия"][:1] != [2] or б["линия"][:1] != [1]):
        плохо(f"{н} черта под шапкой «Правки из чата»: открыт {до['линия']}, свёрнут {б['линия']} — ждали 2 и 1 px")
    стр.screenshot(path=str(СНИМКИ / f"fold-{ш}{'-n' if ночь else ''}.png"))
    стр.locator("#presetChipCard [data-act='ch-hide']").click(); стр.wait_for_timeout(300)
    б = г()
    if not б or б["пунктов"] or б["глаз"] != "false":
        плохо(f"{н} глаз при свёрнутом списке развернул его: {б}")
    # Выбор помнится.
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300); ч.открыть(стр); стр.wait_for_timeout(300)
    б = г()
    if not б or б["развёрнут"] != "false" or стр.evaluate("() => localStorage.getItem('banya_chat_edits_folded')") != "1":
        плохо(f"{н} свёрнутый список не запомнился: {б}")
    стр.locator("#presetChipCard [data-act='ch-fold']").click(); стр.wait_for_timeout(300)
    б = г()
    if not б or б["пунктов"] != 3 or б["развёрнут"] != "true":
        плохо(f"{н} птичка без глаза не развернула все три: {б}")
    # Все выполнены и спрятаны — строка, а не пустое место.
    стр.evaluate("() => { (_чат.сообщения || []).forEach(с => { if (с.review_state) с.review_state = 'done'; }); заполнитьКарточкуЗначка(); }")
    стр.locator("#presetChipCard [data-act='ch-hide']").click(); стр.wait_for_timeout(300)
    б = г()
    if not б or б["пунктов"] or not б["скрыто"] or "готово" not in б["шапка"]:
        плохо(f"{н} все выполнены и спрятаны: {б}")
    ч.вёрстка(стр, н, "«Проверка», выполненные скрыты")
    # Птичка «Автоматической проверки» (Константин 18.10.2026: «На
    # автоматическую проверку поставь тоже птичку, чтобы свернуть можно было»).
    стр.evaluate("() => { try { localStorage.removeItem('banya_auto_check_folded'); } catch (e) {} _автоПроверкаСвёрнута = false; заполнитьКарточкуЗначка(); }")
    стр.wait_for_timeout(300)
    АВТО = """() => { const к = document.getElementById('presetChipCard'), пт = к.querySelector('[data-act="ck-fold"]');
      if (!пт) return null;
      const г = пт.closest('.pc-grp'), р = пт.getBoundingClientRect(), с = getComputedStyle(пт, '::before');
      const кр = к.getBoundingClientRect(), cs = getComputedStyle(к), край = кр.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
      return { шапка: г.innerText.replace(/\\s+/g, ' ').trim().toLowerCase(), развёрнут: пт.getAttribute('aria-expanded'), фокус: document.activeElement === пт,
        итог: !!к.querySelector('.pc-ck-s'), пунктов: к.querySelectorAll('.pc-ck > li, .pc-q').length,
        рисунок: Math.round(р.height), поле: [Math.round(р.width - parseFloat(с.left) - parseFloat(с.right)), Math.round(р.height - parseFloat(с.top) - parseFloat(с.bottom))],
        доКрая: Math.round(край - р.right) }; }"""
    а = стр.evaluate(АВТО)
    if not а or "автоматическая проверка" not in а["шапка"] or а["развёрнут"] != "true" or not а["итог"] or а["рисунок"] > 28 \
            or а["поле"][0] < 31.5 or а["поле"][1] < 43.5 or а["доКрая"] < 0:
        плохо(f"{н} птичка «Автоматической проверки»: {а}")
    if а:
        число = а["шапка"].replace("автоматическая проверка", "").strip()
        стр.locator("#presetChipCard [data-act='ck-fold']").click(); стр.wait_for_timeout(300)
        б = стр.evaluate(АВТО)
        if not б or б["развёрнут"] != "false" or б["итог"] or б["пунктов"] or not б["фокус"] or б["шапка"].replace("автоматическая проверка", "").strip() != число:
            плохо(f"{н} «Автоматическая проверка» не свернулась или потеряла число: {б}")
        стр.screenshot(path=str(СНИМКИ / f"autofold-{ш}{'-n' if ночь else ''}.png"))
        стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300); ч.открыть(стр); стр.wait_for_timeout(300)
        б = стр.evaluate(АВТО)
        if not б or б["развёрнут"] != "false" or стр.evaluate("() => localStorage.getItem('banya_auto_check_folded')") != "1":
            плохо(f"{н} свёрнутая «Автоматическая проверка» не запомнилась: {б}")
        стр.locator("#presetChipCard [data-act='ck-fold']").click(); стр.wait_for_timeout(300)
        б = стр.evaluate(АВТО)
        if not б or б["развёрнут"] != "true" or not б["итог"]:
            плохо(f"{н} «Автоматическая проверка» не развернулась: {б}")
        ч.вёрстка(стр, н, "«Проверка», птичка автоматической проверки")
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
    print("Чисто: глаз прячет выполненные правки, птичка сворачивает весь список при глазе и без него, поля нажатия не наезжают и не выходят за край, число и счёт те же, выбор помнится; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
