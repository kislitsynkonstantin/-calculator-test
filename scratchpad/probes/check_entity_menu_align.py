#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Меню документа в окне печати: значки и названия пунктов — в одну колонку.

Найдено 19.10.2026 на снимке для статьи «Как печатать документы»: у пункта
«Согласие на обработку данных» название в две строки, значок ужимался, и
пункт стоял левее соседних. Проба держит, на 390 и 1440 в настоящих шрифтах:
у всех видимых пунктов значок одной ширины и с одного края, названия
начинаются с одного края.

    python3 check_entity_menu_align.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
from playwright.sync_api import sync_playwright

НАХОДКИ = []

МЕРА = """() => [...document.querySelectorAll('#previewEntityMenu button')].filter(к => к.getClientRects().length).map(к => {
  const з = к.querySelector(':scope > svg'), н = к.querySelector('.ent-name') || к.querySelector('span');
  return { т: к.textContent.replace(/\\s+/g, ' ').trim().slice(0, 30), зл: з ? Math.round(з.getBoundingClientRect().left) : null,
    зш: з ? Math.round(з.getBoundingClientRect().width) : null, нл: н ? Math.round(н.getBoundingClientRect().left) : null }; })"""


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                к, стр, ош = о.начать(бр, порт, ш, "manager")
                стр.evaluate("() => { window.согласованиеДействует = () => true; const ч = document.getElementById('cashDiscountCheck'); if (ч) { ч.checked = true; ч.dispatchEvent(new Event('change', { bubbles: true })); } calc(); обновитьМенюДокумента(); }")
                стр.locator('#previewEntityBtn').click(); стр.wait_for_timeout(400)
                п = стр.evaluate(МЕРА)
                if len(п) < 6:
                    НАХОДКИ.append(f"[{ш}] в меню документа меньше шести пунктов: {п}")
                for ключ, имя in (("зл", "значок слева"), ("зш", "ширина значка"), ("нл", "название слева")):
                    знач = {x[ключ] for x in п if x[ключ] is not None}
                    if len(знач) > 1 and max(знач) - min(знач) > 1:
                        НАХОДКИ.append(f"[{ш}] {имя} разное у пунктов: " + ", ".join(f"{x['т']} {x[ключ]}" for x in п))
                к.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: в меню документа значки одной ширины и с одного края, названия — с одного края; на 390 и 1440.")


if __name__ == "__main__":
    главная()
