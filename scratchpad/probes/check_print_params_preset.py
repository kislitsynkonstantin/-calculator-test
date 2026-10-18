#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Параметры» окна печати запоминаются в пресете.

Константин 18.10.2026, снимком меню «Параметры» (параметры проекта, суммы
разделов, изображения, ссылка): «Положение этих настроек в пресете сделай,
чтобы запоминалось. Изображения не запоминаются».

Проба держит, на заглушке базы:
  • снятые в меню «Параметры проекта», «Суммы разделов» и «Изображения»
    помечают пресет правкой, и автосохранение пишет их в снимок
    (`printDoc`): все три — выключены;
  • «Сбросить всё» возвращает все три к виду по умолчанию — галочки стоят;
  • пресет, открытый заново, возвращает все три выключенными: переменные,
    галочки меню и кнопка «В печати» карточки снимков;
  • пресет без записи `printDoc` (сохранённый до сборки) открывается со
    всеми тремя включёнными.

    python3 check_print_params_preset.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


СОСТОЯНИЕ = """() => ({ п: printShowParams, с: !printHideSectionTotals, и: printImagesEnabled,
  г: ['printParamsParamsCheck', 'printParamsHideTotalsCheck', 'printParamsImagesCheck'].map(ид => (document.getElementById(ид) || {}).style ? document.getElementById(ид).style.opacity : '?'),
  к: (document.getElementById('btnTogglePrintImages') || { style: {} }).style.opacity })"""


def прогон(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
    if стр.locator("#pcName").count():
        стр.locator("#pcName").press("Enter")
    стр.wait_for_timeout(2600)
    ид = стр.evaluate("() => activePresetId")
    if not ид:
        плохо("пресет не сохранился"); стр.close(); return

    # Меню «Параметры» в окне печати: снять все три.
    стр.evaluate("() => openPrintPreview()"); стр.wait_for_timeout(1200)
    for пункт in ["#printParamsParamsItem", "#printParamsHideTotalsItem", "#printParamsImagesItem"]:
        # Нажатие на сам пункт меню — проверяется и его onclick.
        стр.evaluate("(с) => document.querySelector(с).click()", пункт); стр.wait_for_timeout(300)
    стр.wait_for_timeout(2500)   # автосохранение — 1,2 с тишины
    снимок = стр.evaluate("(ид) => (loadAllPresets()[ид] || {}).state || {}", ид).get("printDoc")
    if снимок != {"params": False, "totals": False, "images": False}:
        плохо(f"в снимке пресета после снятия трёх галочек: {снимок!r}")

    # «Сбросить всё» — к виду по умолчанию.
    стр.evaluate("() => closePrintPreview()"); стр.wait_for_timeout(300)
    стр.evaluate("() => resetEverything()"); стр.wait_for_timeout(800)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not (с["п"] and с["с"] and с["и"]) or с["г"] != ["1", "1", "1"]:
        плохо(f"после «Сбросить всё» параметры печати не по умолчанию: {с}")

    # Пресет заново — все три выключены, и документ без сумм разделов.
    стр.evaluate("(ид) => loadPreset(ид)", ид); стр.wait_for_timeout(2500)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["п"] or с["с"] or с["и"] or с["г"] != ["0", "0", "0"] or с["к"] != "0.5":
        плохо(f"открытый заново пресет не вернул параметры печати: {с}")
    стр.evaluate("() => openPrintPreview()"); стр.wait_for_timeout(1200)
    if not стр.evaluate("() => printHideSectionTotals"):
        плохо("документ печати собирается с суммами разделов, хотя пресет их снял")

    # Пресет без записи — всё включено.
    стр.evaluate("""(ид) => { const все = loadAllPresets(); delete все[ид].state.printDoc; saveAllPresets(все); }""", ид)
    стр.evaluate("(ид) => loadPreset(ид)", ид); стр.wait_for_timeout(2500)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not (с["п"] and с["с"] and с["и"]) or с["г"] != ["1", "1", "1"]:
        плохо(f"пресет без записи параметров печати открылся не по умолчанию: {с}")
    if ошибки:
        плохо(f"ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Параметры проекта», «Суммы разделов» и «Изображения» пишутся в пресет, «Сбросить всё» "
          "возвращает их по умолчанию, пресет открывается с ними, пресет без записи — со всеми включёнными.")


if __name__ == "__main__":
    главная()
