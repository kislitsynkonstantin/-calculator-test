#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Платёжный план договора на отделку: этап «парное отделение» — по парной и печи.

Константин 02.10.2026, снимками спецификации и окна договоров: «платёжный план
перепиши: если есть эти 2 этапа в спецификации — тогда есть этап оплаты
„парное отделение“ в договоре на отделку. Если нет печи и парной, то этого
этапа в автораспределении нет. И автоматом сам меняется платёжный план от
изменения этих этапов».

Проба на 390 и 1440 держит:
  • парная и печь в расчёте есть — в плане отделки три этапа: аванс, «перед
    монтажом парного отделения» с суммой, финальный 50 000; итог равен цене;
  • этап парной не меньше 150 000 ₽: недостающее берётся из аванса, аванс не
    больше 70 %, а когда парной и так хватает — ровно 70 % (цены 529 440,
    2 000 000, 300 000, 180 000; 03.10.2026);
  • парную и печь сняли — план пересчитался сам: этапа парной нет ни в окне
    плана (строка скрыта, номера идут 1, 2, в подвале этапов на один меньше),
    ни в договоре; остаток — в аванс,
    финальный по-прежнему 50 000; итог равен цене;
  • вернули опцию парной — этап вернулся сам;
  • правка суммы руками живёт, пока парная и печь не появились и не пропали:
    другая галочка план не пересчитывает;
  • план, сохранённый до этой правки (без пометки), пересчитывается при первом
    же расхождении.

    python3 check_pp_steam_stage.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ПЛАН = """() => { const c = getPPContracts().find(x => x.id === 2), st = ppState[2]; if (!st) return null;
  const total = ppGetTotal(c), сумма = st.amounts.reduce((a, b) => a + b, 0) + (st.finalAmt || 0);
  const html = buildContractHtmlKar(getContractVarsKar(2)), д = new DOMParser().parseFromString(html, 'text/html');
  return { total, сумма, amounts: st.amounts.slice(), finalAmt: st.finalAmt, парная: st.парная,
    договор: [...д.querySelectorAll('.g1 .tm')].map(т => т.textContent.trim()),
    пустые: [isPrintSectionEmpty('steam'), isPrintSectionEmpty('stove')] }; }"""

СНЯТЬ = """() => { OPTIONS.filter(o => o.section === 'steam' || o.section === 'stove').forEach(o => { checkedOptions[o.id] = false; });
  ['steam', 'stove'].forEach(к => { try { (getCustomOpts(к) || []).forEach(co => { co.checked = false; }); } catch (e) {} }); calc(); }"""
ВЕРНУТЬ = """() => { const о = OPTIONS.find(o => o.section === 'steam' && o.included && !o.auto); checkedOptions[о.id] = true; calc(); return о.id; }"""
СТРОКИ = """() => [...document.querySelectorAll('[id^="pprow_2_"]')].map(р => ({ видна: getComputedStyle(р).display !== 'none', номер: (р.querySelector('.pp-num') || {}).textContent }))"""


def проверить(н, п, парная):
    if not п:
        НАХОДКИ.append(f"{н} нет плана договора на отделку"); return
    if abs(п["сумма"] - п["total"]) > 1:
        НАХОДКИ.append(f"{н} сумма этапов {п['сумма']} не равна цене договора {п['total']}")
    if п["finalAmt"] < 50000 or п["finalAmt"] >= 51000:
        НАХОДКИ.append(f"{н} финальный платёж {п['finalAmt']}, ждали 50 000 (с копейками до тысячи)")
    if парная:
        if п["amounts"][1] < min(150000, п["total"] - п["finalAmt"]):
            НАХОДКИ.append(f"{н} этап парной {п['amounts'][1]} меньше 150 000")
        if п["парная"] is not True or not п["amounts"][1] > 0:
            НАХОДКИ.append(f"{н} парная и печь есть, а этапа парной нет: {п['amounts']}, пометка {п['парная']}")
        if not any("отделку парной" in т for т in п["договор"]):
            НАХОДКИ.append(f"{н} в договоре нет строки этапа парной: {п['договор']}")
    else:
        if п["парная"] is not False or п["amounts"][1] != 0:
            НАХОДКИ.append(f"{н} парной и печи нет, а этап парной в плане: {п['amounts']}, пометка {п['парная']}, пустые {п['пустые']}")
        if any("парной" in т for т in п["договор"]) or len(п["договор"]) != 2:
            НАХОДКИ.append(f"{н} в договоре без парной не два платежа: {п['договор']}")
        if abs(п["amounts"][0] - (п["total"] - п["finalAmt"])) > 1:
            НАХОДКИ.append(f"{н} без парной остаток не в авансе: аванс {п['amounts'][0]}, цена {п['total']}, финальный {п['finalAmt']}")


# Этап парной не меньше 150 000 ₽, недостающее — из аванса (Константин,
# 03.10.2026: «оставь аванс 70 %. Внедри только правило, что этап за парную не
# менее 150 000 р. Если меньше, получается, то забираем с аванса»).
ЦЕНЫ = """(цены) => { const c = getPPContracts().find(x => x.id === 2);
  return цены.map(т => { ppInitContract(c, т); const st = ppState[2]; return { т, аванс: st.amounts[0], парная: st.amounts[1], финал: st.finalAmt }; }); }"""


def по_ценам(н, стр):
    for р in стр.evaluate(ЦЕНЫ, [529440, 2000000, 300000, 180000]):
        т, а, п_, ф = р["т"], р["аванс"], р["парная"], р["финал"]
        и = f"{н} цена {т}:"
        if а + п_ + ф != т:
            НАХОДКИ.append(f"{и} этапы {а} + {п_} + {ф} не равны цене")
        if п_ < min(150000, т - ф):
            НАХОДКИ.append(f"{и} этап парной {п_} меньше 150 000")
        if а > round(т * 0.7 / 1000) * 1000:
            НАХОДКИ.append(f"{и} аванс {а} больше 70 %")
        if т * 0.7 < т - ф - 150000 and а != round(т * 0.7 / 1000) * 1000:
            НАХОДКИ.append(f"{и} парная и так не меньше 150 000, а аванс {а} не 70 %")
        if not 50000 <= ф < 51000:
            НАХОДКИ.append(f"{и} финальный {ф}, ждали 50 000")


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                стр, ош = к.начать(СоШрифтами(бр), порт, ш, 900, False)
                стр.evaluate("() => { ppState = {}; getPPContracts().forEach(c => ppInitContract(c)); }")
                п = стр.evaluate(ПЛАН)
                if п and (п["пустые"][0] and п["пустые"][1]):
                    НАХОДКИ.append(f"{н} в проекте пробы нет ни парной, ни печи — проверять нечего"); стр.close(); continue
                проверить(f"{н} с парной:", п, True)
                по_ценам(н, стр)
                стр.evaluate("() => { ppState = {}; getPPContracts().forEach(c => ppInitContract(c)); }")
                стр.evaluate(СНЯТЬ); стр.wait_for_timeout(200)
                проверить(f"{н} парную и печь сняли:", стр.evaluate(ПЛАН), False)
                # Окно плана: строка парной скрыта, номера подряд.
                стр.evaluate("() => { openPaymentPlan(); }"); стр.wait_for_timeout(500)
                строки = стр.evaluate(СТРОКИ)
                видимые = [с_["номер"] for с_ in строки if с_["видна"]]
                if видимые != ["1"]:
                    НАХОДКИ.append(f"{н} в окне плана видимые этапы отделки до финального: {видимые}, ждали только «1»")
                подвал = стр.evaluate("() => document.getElementById('ppFootCount').textContent")
                всего = стр.evaluate("() => getPPContracts().reduce((n, c) => n + c.payments.length, 0)")
                if f"{всего - 1} этап" not in подвал:
                    НАХОДКИ.append(f"{н} в подвале плана «{подвал}» — скрытый этап парной посчитан")
                if ш == 1440:
                    стр.screenshot(path=str(м.СНИМКИ / "pp-steam-off-1440.png"))
                стр.evaluate("() => { const о = document.getElementById('paymentPlanOverlay'); if (typeof closePaymentPlan === 'function') closePaymentPlan(); else о.classList.remove('open'); }")
                стр.evaluate(ВЕРНУТЬ); стр.wait_for_timeout(200)
                проверить(f"{н} опцию парной вернули:", стр.evaluate(ПЛАН), True)
                # Правка руками живёт, пока парная не появилась и не пропала.
                стр.evaluate("() => { ppOnAmtBlur(2, 0, String(ppState[2].amounts[0] + 7000)); }")
                руками = стр.evaluate("() => ppState[2].amounts[0]")
                стр.evaluate("() => { const о = OPTIONS.find(o => o.section === 'interior' && !o.included && !checkedOptions[o.id]); if (о) { checkedOptions[о.id] = true; calc(); } }")
                if стр.evaluate("() => ppState[2].amounts[0]") != руками:
                    НАХОДКИ.append(f"{н} другая галочка пересчитала план и стёрла правку руками")
                # План, сохранённый до пометки: этап парной с суммой, а парной уже нет.
                стр.evaluate("() => { delete ppState[2].парная; }")
                стр.evaluate(СНЯТЬ); стр.wait_for_timeout(200)
                проверить(f"{н} старый план без пометки:", стр.evaluate(ПЛАН), False)
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
    print("Чисто: этап «парное отделение» в договоре на отделку есть, только пока в расчёте есть парная или печь; "
          "план пересчитывается сам в обе стороны, остаток уходит в аванс, финальный — 50 000, правка руками живёт до "
          "смены — на 390 и 1440.")


if __name__ == "__main__":
    главная()
