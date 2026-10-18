#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Платёжный план основного договора по правилу сходится с ценой до рубля.

Константин 18.10.2026, снимком договора «Виго» (пресет 321 910): «Тут проверь,
почему расхождение. Автоматом же ставит». Цена 6 169 840 ₽, этапы — 6 170 000 ₽:
этапы округляются вверх до 5 000 и перебрали цену, а этап плёнок, который
собирает остаток, вышел −160 ₽ и был обрезан до нуля.

Проба держит, на правиле основного договора с фундаментом 480 000 ₽:
  • «Виго»: каркас 925 000, плёнки 4 840 — сумма этапов 6 169 840;
  • на 300 случайных ценах от 1,5 до 9 млн: сумма этапов равна цене, ни один
    этап не меньше нуля, все этапы, кроме плёнок, кратны 5 000.

    python3 check_pp_rounding.py
"""
import pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ПЛАН = """(цены) => { const c = { id: 1, payments: [{ pct: 30, label: 'Аванс по договору' }, { pct: 0, label: 'Платёж за фундамент', foundationFixed: true },
    { pct: 40, label: 'При заезде бригады' }, { pct: 15, label: 'По завершении каркасных работ' },
    { pct: 7, label: 'По завершении кровельных работ', roofAdjusted: true }, { pct: 0, label: 'По завершении утепления и плёнок' }] };
  const был = window.ppGetFoundationAmt, сохр = ppState[1];
  window.ppGetFoundationAmt = () => 480000;
  try { return цены.map(т => { ppInitContractТело(c, т); return { т, a: ppState[1].amounts.slice(), ф: ppState[1].finalAmt || 0 }; }); }
  finally { window.ppGetFoundationAmt = был; ppState[1] = сохр; } }"""


def главная():
    random.seed(18102026)
    цены = [6169840] + [random.randint(1_500_000, 9_000_000) for _ in range(300)]
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                к, стр, ош = о.начать(бр, порт, 1440, "admin")
                итоги = стр.evaluate(ПЛАН, цены)
                к.close()
            finally:
                бр.close()
    finally:
        с.shutdown()
    виго = итоги[0]
    if виго["a"] != [1855000, 480000, 2470000, 925000, 435000, 4840]:
        НАХОДКИ.append(f"«Виго» 6 169 840: этапы {виго['a']}, сумма {sum(виго['a'])}")
    for р in итоги:
        if sum(р["a"]) + р["ф"] != р["т"]:
            НАХОДКИ.append(f"цена {р['т']}: этапы {р['a']} в сумме {sum(р['a'])}")
        if any(а < 0 for а in р["a"]):
            НАХОДКИ.append(f"цена {р['т']}: отрицательный этап {р['a']}")
        if any(а % 5000 for а in р["a"][:-1]):
            НАХОДКИ.append(f"цена {р['т']}: этап не кратен 5 000 {р['a']}")
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ[:12]:
            print(" —", т)
        print(f"всего находок: {len(НАХОДКИ)}")
        sys.exit(1)
    print("Чисто: план основного договора по правилу сходится с ценой до рубля на «Виго» и 300 случайных ценах; этапы кратны 5 000, остаток — в плёнках.")


if __name__ == "__main__":
    главная()
