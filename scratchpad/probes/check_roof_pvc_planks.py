#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кровля ПВХ снимает отметку с карнизной и ветровой планок.

Константин 30.09.2026, снимком раздела «Кровля»: «добавь автоматизацию: когда
кровля ПВХ, то снимается галочка с карнизной и ветровой планки». Плоской кровле
ПВХ планки не нужны.

Проба нажимает на строки так же, как менеджер, на 390 и 1440, и держит:
  • отметили «Замену плоской наплавляемой кровли на ПВХ» — планки сняты и
    закрыты замком с подсказкой, которая называет ПВХ;
  • сняли ПВХ — планки снова отмечены (они входят в базу) и открыты;
  • наплавляемая ТехноНИКОЛЬ планок не трогает — правило только о ПВХ;
  • расчёт, сохранённый с ПВХ и планками вместе, после разбора правил держит
    планки снятыми.

    python3 check_roof_pvc_planks.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

СОСТ = """() => { const л = document.getElementById('lbl_r3'), ч = document.getElementById('chk_r3');
  return { отмечена: !!checkedOptions.r3, галочка: !!(ч && ч.checked), закрыта: !!(л && л.dataset.blocked === '1'),
    подсказка: (л && л.dataset.blockedText) || '', замок: !!(л && л.querySelector('.excl-lock')), пвх: !!checkedOptions.r15 }; }"""


def нажать(стр, ид):
    стр.evaluate("(ид) => document.getElementById('lbl_' + ид).scrollIntoView({ block: 'center' })", ид)
    стр.wait_for_timeout(150)
    стр.locator(f"#lbl_{ид} .opt-check").first.click()
    стр.wait_for_timeout(450)


def прогон(бр, порт, шир, выс):
    н = f"[{шир}]"
    стр = бр.new_page(viewport={"width": шир, "height": выс})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    if not стр.locator("#lbl_r15").count() or not стр.locator("#lbl_r3").count():
        НАХОДКИ.append(f"{н} в разделе «Кровля» нет строки ПВХ или планок"); стр.close(); return
    с = стр.evaluate(СОСТ)
    if not с["отмечена"] or с["закрыта"]:
        НАХОДКИ.append(f"{н} до ПВХ планки не отмечены или закрыты: {с}")
    нажать(стр, "r15")
    с = стр.evaluate(СОСТ)
    if not с["пвх"]:
        НАХОДКИ.append(f"{н} ПВХ не отметилась нажатием: {с}")
    elif с["отмечена"] or с["галочка"] or not с["закрыта"] or not с["замок"] or "ПВХ" not in с["подсказка"]:
        НАХОДКИ.append(f"{н} ПВХ отмечена, а планки: {с}")
    нажать(стр, "r15")
    с = стр.evaluate(СОСТ)
    if с["пвх"] or not с["отмечена"] or not с["галочка"] or с["закрыта"] or с["замок"]:
        НАХОДКИ.append(f"{н} ПВХ снята, а планки не вернулись: {с}")
    if стр.locator("#lbl_r17").count():
        нажать(стр, "r17")
        с = стр.evaluate(СОСТ)
        if not с["отмечена"] or с["закрыта"]:
            НАХОДКИ.append(f"{н} наплавляемая ТехноНИКОЛЬ тронула планки: {с}")
        нажать(стр, "r17")
    с = стр.evaluate("""() => { checkedOptions.r15 = true; checkedOptions.r3 = true; applyExclusions();
      return { планки: !!checkedOptions.r3, пвх: !!checkedOptions.r15 }; }""")
    if с["планки"] or not с["пвх"]:
        НАХОДКИ.append(f"{н} расчёт с ПВХ и планками вместе после разбора правил: {с}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for шир, выс in ((1440, 900), (390, 844)):
                прогон(бр, порт, шир, выс)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: ПВХ снимает и закрывает карнизную и ветровую планки, снятая ПВХ возвращает их, наплавляемая "
          "их не трогает, сохранённый расчёт с обеими держит планки снятыми — на 1440 и 390.")


if __name__ == "__main__":
    главная()
