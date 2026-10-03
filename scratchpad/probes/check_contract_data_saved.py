#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Данные для договора» сохраняются в пресет и переживают перезагрузку.

Константин 03.10.2026, снимком окна «Данные для договора»: «я вот тут заполнил
данные в пресет. Перезагрузил, а они не сохранились». Поля окна писались только
в память браузера и пресет правкой не помечали: автосохранение не запускалось,
а при перезагрузке пресет раскладывал свою старую копию полей поверх
вписанного.

Проба на 390 и 1440: свой пресет открыт, в окне «Данные для договора» вписаны
адрес регистрации, дата выдачи паспорта (поле даты), кем выдан и адрес участка
— без нажатия «Сохранить» и после него; через автосохранение все поля в
пресете, и раскладка пресета (то, что делает перезагрузка) их возвращает.
Очистка полей так же доходит до пресета.

    python3 check_contract_data_saved.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ПОЛЯ = {"cdRegAddress": "123456, г. Москва, ул. Пробная, д. 1", "cdPassportIssuer": "ОВД Пробного района",
        "cdPlotAddress": "Московская область, д. Проба", "cdPassportDate": "2015-06-01"}

ПРЕСЕТ = """(ид) => { const п = loadAllPresets()[activePresetId]; return п && п.state ? (п.state.contractData || {})[ид] : '—нет пресета—'; }"""


def прогон(бр, порт, ш, сохранить):
    н = f"[{ш} {'«Сохранить»' if сохранить else 'без «Сохранить»'}]"
    стр, ош = к.начать(СоШрифтами(бр), порт, ш, 900, False)
    if not стр.evaluate("() => activePresetId"):
        НАХОДКИ.append(f"{н} пресет не сохранился"); стр.close(); return
    стр.evaluate("() => openContractDataModal()"); стр.wait_for_timeout(300)
    for ид, зн in ПОЛЯ.items():
        поле = стр.locator("#" + ид)
        if ид == "cdPassportDate":
            поле.fill(зн); поле.dispatch_event("change")
        else:
            поле.fill(зн)
    if сохранить:
        стр.locator("#contractDataOverlay button", has_text="Сохранить").click()
    else:
        стр.evaluate("() => closeContractDataModal()")
    стр.wait_for_timeout(2600)   # автосохранение пресета — через 1,2 с после правки
    for ид, зн in ПОЛЯ.items():
        if стр.evaluate(ПРЕСЕТ, ид) != зн:
            НАХОДКИ.append(f"{н} в пресете «{ид}» = «{стр.evaluate(ПРЕСЕТ, ид)}», ждали «{зн}»")
    # Перезагрузка открывает пресет заново и раскладывает его состояние —
    # то же делаем здесь: сперва очищаем поля, потом раскладываем пресет.
    стр.evaluate("() => { ['cdRegAddress','cdPassportIssuer','cdPlotAddress','cdPassportDate'].forEach(и => { document.getElementById(и).value = ''; }); restoreState(loadAllPresets()[activePresetId].state); }")
    стр.wait_for_timeout(800)
    for ид, зн in ПОЛЯ.items():
        есть = стр.evaluate("(ид) => (document.getElementById(ид) || {}).value", ид)
        if есть != зн:
            НАХОДКИ.append(f"{н} после раскладки пресета «{ид}» = «{есть}», ждали «{зн}»")
    # Очистка тоже доходит до пресета.
    if сохранить:
        стр.evaluate("() => clearContractData()"); стр.wait_for_timeout(2600)
        if стр.evaluate(ПРЕСЕТ, "cdRegAddress"):
            НАХОДКИ.append(f"{н} поля очистили, а в пресете осталось «{стр.evaluate(ПРЕСЕТ, 'cdRegAddress')}»")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for сохранить in (False, True):
                    прогон(бр, порт, ш, сохранить)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: «Данные для договора» уходят в пресет и сами (без «Сохранить»), и с ним, переживают перезагрузку; "
          "очистка тоже доходит до пресета — на 390 и 1440.")


if __name__ == "__main__":
    главная()
