#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Снять базу» / «Добавить базу» в каждом разделе.

Константин 18.10.2026, снимком раздела «Парное отделение»: «Тут в каждом
разделе добавь аккуратную подпись-кнопку «Снять/добавить» базу, чтобы менялась
подпись. Когда надо раздел отключить, чтобы одной кнопкой и он не уходил в
платежный план».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • кнопка есть у каждого раздела с базовыми позициями и только у них;
    подпись — «Снять базу», пока хоть одна базовая отмечена, иначе
    «Добавить базу»;
  • «Снять базу» в парной снимает все её базовые позиции, итог падает на
    стоимость базы раздела, этап парной уходит из платёжного плана договора
    на отделку; «Добавить базу» возвращает итог и план как были;
  • вёрстка на 390 и 1440: кнопка в строке подписи раздела, у правого края,
    под суммой, не налезает на подпись и не вылезает за раздел; поле
    нажатия не меньше 44 px по высоте; ничего не шире экрана.

    python3 check_section_base.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


СОСТОЯНИЕ = """() => ({
  кнопки: Object.fromEntries(SECTIONS.map(с => { const б = document.getElementById('sec_base_' + с.key); return [с.key, б && !б.hidden ? б.textContent : null]; })),
  естьБаза: Object.fromEntries(SECTIONS.map(с => [с.key, базовыеРаздела(с.key).length > 0])),
  итог: Math.round(_currentTotal),
  база: OPTIONS.filter(o => o.included && !o.auto && o.section === 'steam' && isOptionVisible(o)).map(o => !!checkedOptions[o.id]),
  план: (getContractVarsKar(2).paymentRows || []).map(р => р.amount) })"""

ВЁРСТКА = """() => { const н = [], W = document.documentElement.clientWidth;
  SECTIONS.forEach(с => { const б = document.getElementById('sec_base_' + с.key); if (!б || б.hidden || !б.getClientRects().length) return;
    const р = б.getBoundingClientRect(), стр = б.parentElement, ср = стр.getBoundingClientRect(), т = стр.querySelector('.sec-note-t').getBoundingClientRect();
    const сумма = document.getElementById('sec_total_' + с.key).getBoundingClientRect();
    if (р.right > ср.right + .5 || р.left < ср.left - .5) н.push(с.key + ': кнопка за строкой подписи');
    if (т.width && р.left - т.right < 8 && Math.abs(р.top - т.top) < 10) н.push(с.key + ': кнопка вплотную к подписи: ' + Math.round(р.left - т.right));
    if (Math.abs(р.right - сумма.right) > 2) н.push(с.key + ': кнопка не под суммой: ' + Math.round(р.right - сумма.right));
    const сп = getComputedStyle(б, '::before'), h = р.height - parseFloat(сп.top) - parseFloat(сп.bottom);
    if (h < 43.5) н.push(с.key + ': поле нажатия по высоте ' + Math.round(h)); });
  if (document.documentElement.scrollWidth > W + 1) н.push('страница шире экрана');
  return н; }"""


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к, стр, ош = о.начать(бр, порт, ш, "admin")
    стр.evaluate("() => closePrintPreview()"); стр.wait_for_timeout(400)
    до = стр.evaluate(СОСТОЯНИЕ)
    for ключ, подпись in до["кнопки"].items():
        if до["естьБаза"][ключ] and подпись != "Снять базу":
            плохо(f"{н} {ключ}: у раздела с базой подпись «{подпись}»")
        if not до["естьБаза"][ключ] and подпись is not None:
            плохо(f"{н} {ключ}: кнопка у раздела без базы")
    if not all(до["база"]):
        плохо(f"{н} в начале база парной снята: {до['база']}")
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {т}")
    стр.evaluate("() => document.getElementById('sec_base_steam').scrollIntoView({ block: 'center' })"); стр.wait_for_timeout(300)
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"section-base-{ш}.png"))
    стр.locator("#sec_base_steam").click(); стр.wait_for_timeout(600)
    сн = стр.evaluate(СОСТОЯНИЕ)
    # База раздела без галочек показана бледной суммой в заголовке.
    база_парной = стр.evaluate("() => { const э = document.getElementById('sec_total_steam'); return { сумма: +э.textContent.replace(/\\D/g, ''), бледно: getComputedStyle(э).opacity < 0.5 }; }")
    if not база_парной["бледно"]:
        плохо(f"{н} без базы сумма парной не бледная")
    база_парной = база_парной["сумма"]
    if any(сн["база"]) or сн["кнопки"]["steam"] != "Добавить базу":
        плохо(f"{н} «Снять базу»: позиции {сн['база']}, подпись «{сн['кнопки']['steam']}»")
    if до["итог"] - сн["итог"] != round(база_парной):
        плохо(f"{н} итог упал на {до['итог'] - сн['итог']}, база парной {база_парной}")
    if len(сн["план"]) >= len(до["план"]) or sum(сн["план"]) != sum(до["план"]) - round(база_парной):
        плохо(f"{н} этап парной остался в плане отделки: было {до['план']}, стало {сн['план']}")
    стр.locator("#sec_base_steam").click(); стр.wait_for_timeout(600)
    об = стр.evaluate(СОСТОЯНИЕ)
    if об["итог"] != до["итог"] or об["план"] != до["план"] or not all(об["база"]) or об["кнопки"]["steam"] != "Снять базу":
        плохо(f"{н} «Добавить базу» не вернула как было: итог {об['итог']}/{до['итог']}, план {об['план']}/{до['план']}")
    if ош:
        плохо(f"{н} ошибки страницы: {ош[:3]}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440)
                прогон(бр, порт, 390)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Снять базу» / «Добавить базу» у каждого раздела с базой, снимает базу раздела, итог и платёжный план идут следом, "
          "возврат — как было; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
