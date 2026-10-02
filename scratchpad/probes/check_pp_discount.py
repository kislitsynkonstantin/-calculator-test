#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Этапы оплаты — от цены договора со скидкой.

Константин 02.10.2026, двумя снимками договора: в п. 2.1 цена 1 559 368 ₽
(спец. цена −3 % за наличные), а этапы оплаты складывались в 1 607 596 ₽ — цену
без скидки. «В договоре и в этапах должна быть цена со скидкой, если скидка
указана». План собирался один раз и за ценой не следил.

Проба на 390 и 1440 держит, для обоих договоров:
  • скидку дали после того, как план собран, — этапы и финальный платёж
    складываются ровно в цену договора со скидкой, и в договоре (п. 2.1 и
    строки платежей) — тоже;
  • план, собранный по правилу, после скидки совпадает с тем, что правило
    даёт на новую цену (в том числе этап парной и 50 000 финального);
  • сумма, вписанная руками, после скидки не теряется, а меняется в той же
    пропорции, что и цена; сумма этапов — ровно цена;
  • план, сохранённый до этой правки (без пометок), подгоняется так же;
  • сброшенный план (все этапы по нулям) остаётся по нулям;
  • скидку сняли — план вернулся к цене без скидки;
  • в окне плана «Итого распределено» — ровно 100,0 %, без красной поправки:
    доля считается из сумм, а не сложением округлённых долей этапов.

    python3 check_pp_discount.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []

СВОД = """() => getPPContracts().map(c => { const st = ppState[c.id]; if (!st) return null;
  const v = getContractVarsKar(c.id), num = т => Number(String(т || '').replace(/[^\\d]/g, '')) || 0;
  const сумма = st.amounts.reduce((a, b) => a + b, 0) + ((st.hasFinal || st.hasFinalFixed) ? (st.finalAmt || 0) : 0);
  return { id: c.id, total: ppGetTotal(c), сумма, amounts: st.amounts.slice(), finalAmt: st.finalAmt,
    договор: num(v.contractTotal), платежи: num(v.paymentTotal) }; })"""

ПО_ПРАВИЛУ = """(ид) => { const c = getPPContracts().find(x => x.id === ид), сохр = ppState[ид];
  ppInitContract(c); const эталон = ppState[ид]; ppState[ид] = сохр; return { amounts: эталон.amounts, finalAmt: эталон.finalAmt }; }"""


def скидка(стр, проц):
    стр.evaluate("(п) => { document.getElementById('discountPctInput').value = String(п); calc(); }", проц)
    стр.wait_for_timeout(150)


def сходится(н, свод, со_скидкой):
    for д in свод:
        if not д:
            НАХОДКИ.append(f"{н} нет плана у договора"); continue
        и = f"{н} договор {д['id']}:"
        if abs(д["сумма"] - д["total"]) > 1:
            НАХОДКИ.append(f"{и} этапы {д['сумма']} ≠ цена {д['total']}")
        if abs(д["договор"] - д["total"]) > 1:
            НАХОДКИ.append(f"{и} в п. 2.1 договора {д['договор']}, а цена {д['total']}")
        if abs(д["платежи"] - д["договор"]) > 1:
            НАХОДКИ.append(f"{и} платежи в договоре {д['платежи']} ≠ п. 2.1 {д['договор']}{' (скидка дана)' if со_скидкой else ''}")


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                стр, ош = к.начать(СоШрифтами(бр), порт, ш, 900, False)
                стр.evaluate("() => { ppState = {}; getPPContracts().forEach(c => ppInitContract(c)); }")
                без = стр.evaluate(СВОД)
                сходится(f"{н} без скидки:", без, False)
                # 1. Скидка после плана.
                скидка(стр, 3)
                со = стр.evaluate(СВОД)
                if all(abs(a["total"] - b["total"]) < 1 for a, b in zip(без, со)):
                    НАХОДКИ.append(f"{н} скидка 3 % не изменила цену договоров — проверять нечего")
                сходится(f"{н} скидка 3 %:", со, True)
                for д in со:
                    э = стр.evaluate(ПО_ПРАВИЛУ, д["id"])
                    if э["amounts"] != д["amounts"] or abs((э["finalAmt"] or 0) - (д["finalAmt"] or 0)) > 1:
                        НАХОДКИ.append(f"{н} договор {д['id']}: план по правилу после скидки {д['amounts']}+{д['finalAmt']}, "
                                       f"а правило даёт {э['amounts']}+{э['finalAmt']}")
                # 2. Правка руками, потом скидка 5 %.
                стр.evaluate("() => { ppOnAmtBlur(1, 0, String(ppState[1].amounts[0] + 7000)); }")
                руками = стр.evaluate("() => ({ a: ppState[1].amounts[0], t: ppGetTotal(getPPContracts().find(c => c.id === 1)) })")
                скидка(стр, 5)
                после = стр.evaluate(СВОД)
                сходится(f"{н} правка руками, скидка 5 %:", после, True)
                д1 = next(д for д in после if д["id"] == 1)
                ждём = руками["a"] * д1["total"] / руками["t"]
                # Крупный этап забирает остаток округления — допускаем его.
                if abs(д1["amounts"][0] - ждём) > 3000 and д1["amounts"][0] != max(д1["amounts"]):
                    НАХОДКИ.append(f"{н} правка руками после скидки {д1['amounts'][0]}, ждали около {round(ждём)} (доля сохранена)")
                э1 = стр.evaluate(ПО_ПРАВИЛУ, 1)
                if э1["amounts"] == д1["amounts"]:
                    НАХОДКИ.append(f"{н} правка руками стёрта: план собран заново по правилу")
                # 3. Старый план без пометок, собранный по правилу.
                стр.evaluate("() => { ppState = {}; getPPContracts().forEach(c => ppInitContract(c)); Object.values(ppState).forEach(st => { delete st.база; delete st.руками; }); }")
                скидка(стр, 2)
                сходится(f"{н} старый план, скидка 2 %:", стр.evaluate(СВОД), True)
                # 4. Сброшенный план.
                стр.evaluate("() => { ppReset(2); }")
                скидка(стр, 4)
                if any(стр.evaluate("() => ppState[2].amounts")):
                    НАХОДКИ.append(f"{н} сброшенный план после скидки заполнился сам")
                # 5. Скидку сняли.
                стр.evaluate("() => { ppDistribute(2); }")
                скидка(стр, 0)
                сходится(f"{н} скидку сняли:", стр.evaluate(СВОД), False)
                if ш == 1440:
                    скидка(стр, 3)
                    стр.evaluate("() => { openPaymentPlan(); }"); стр.wait_for_timeout(500)
                    стр.screenshot(path=str(м.СНИМКИ / "pp-discount-1440.png"))
                    итоги = стр.evaluate("() => [...document.querySelectorAll('.pp-pctbar')].map(э => э.textContent.replace(/\\s+/g, ' ').trim())")
                    if any("100,0" not in и or "(" in и for и in итоги):
                        НАХОДКИ.append(f"{н} в окне плана «Итого распределено» не 100 %: {итоги}")
                    if стр.locator(".pp-rest").count():
                        НАХОДКИ.append(f"{н} в окне плана после скидки «{стр.locator('.pp-rest').first.inner_text()}»")
                for о in [о for о in ош if "supabase.co" not in о][:3]:
                    НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: этапы оплаты и финальный платёж следуют за ценой договора со скидкой — в окне плана, в п. 2.1 "
          "и в строках платежей обоих договоров; план по правилу собирается заново, правка руками сохраняет "
          "долю, сброшенный план не заполняется — на 390 и 1440.")


if __name__ == "__main__":
    главная()
