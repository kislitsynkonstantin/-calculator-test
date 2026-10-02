#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договоры менеджеру видны, но закрыты до согласования спецификации.

Константин 02.10.2026: «закрой сразу для менеджеров доступ к кнопкам договора:
он должен кнопки видеть, но они у него будут неактивные. Потом внедрим модуль
согласования спецификации и после этого будет открываться договор менеджеру».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • менеджер: в меню документа оба пункта договора на месте, приглушены, под
    названием строка «После согласования спецификации»; нажатие договор не
    открывает — окно остаётся на спецификации; печать из окна договор не
    печатает; кнопки договора («Скрыть поля», «Google Диск», «Срок») не видны;
  • администратор: пункты обычные, строки нет, договор открывается;
  • у закрытого пункта площадь нажатия не меньше 44 px, строка не обрезана и
    не выходит за меню, меню не выходит за экран.

    python3 check_contract_lock.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

МЕНЮ = """() => { const меню = document.getElementById('previewEntityMenu'), мр = меню.getBoundingClientRect();
  return [...меню.querySelectorAll('[data-contract]')].filter(к => getComputedStyle(к).display !== 'none').map(к => {
    const р = к.getBoundingClientRect(), стр = к.querySelector('.ent-lock'), сп = стр ? стр.getBoundingClientRect() : null;
    const имя = к.querySelector('.ent-name > span');
    return { ид: к.dataset.contract, закрыт: к.classList.contains('ent-locked'), выс: р.height,
      строка: стр && getComputedStyle(стр).display !== 'none' ? стр.textContent.trim() : '',
      обрезана: стр ? стр.scrollWidth > стр.clientWidth + 1 : false,
      внутри: !сп || сп.width === 0 || (сп.left >= мр.left - 1 && сп.right <= мр.right + 1),
      прозр: имя ? parseFloat(getComputedStyle(имя).opacity) : 1,
      меню: { л: мр.left, п: мр.right }, экран: innerWidth }; }); }"""
КНОПКИ = """() => ['contractHlToggleBtn', 'contractDriveBtn', 'contractTermWrap'].filter(и => { const э = document.getElementById(и); return э && getComputedStyle(э).display !== 'none'; })"""


def прогон(бр, порт, ш, стиль, роль):
    н = f"[{ш} {стиль} {роль}]"
    к, стр, ош = о.начать(бр, порт, ш, роль)
    стр.evaluate("(с) => applyUiStyle(с, false)", стиль)
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(250)
    пункты = стр.evaluate(МЕНЮ)
    if len(пункты) < 2:
        НАХОДКИ.append(f"{н} в меню документа пунктов договора: {len(пункты)}, ждали два")
    for п in пункты:
        и = f"{н} пункт договора {п['ид']}:"
        if роль == "manager":
            if not п["закрыт"] or п["строка"] != "После согласования спецификации":
                НАХОДКИ.append(f"{и} у менеджера не закрыт: {п}")
            if п["прозр"] > 0.6:
                НАХОДКИ.append(f"{и} закрытый пункт не приглушён (прозрачность {п['прозр']})")
            if п["обрезана"] or not п["внутри"]:
                НАХОДКИ.append(f"{и} строка «После согласования» обрезана или за краем меню: {п}")
        else:
            if п["закрыт"] or п["строка"]:
                НАХОДКИ.append(f"{и} у администратора закрыт: {п}")
        if стиль == "blank" and п["выс"] < 44:
            НАХОДКИ.append(f"{и} высота пункта {п['выс']:.0f} px, меньше 44")
        if п["меню"]["л"] < 0 or п["меню"]["п"] > п["экран"]:
            НАХОДКИ.append(f"{и} меню за краем экрана: {п['меню']}")
    if роль == "manager" and ш in (390, 1440) and стиль == "blank":
        стр.screenshot(path=str(м.СНИМКИ / f"contract-lock-{ш}.png"))
    стр.locator('#previewEntityMenu [data-contract="1"]').click(force=(роль == "manager")); стр.wait_for_timeout(1000)
    сущ = стр.evaluate("() => previewEntity")
    кнопки = стр.evaluate(КНОПКИ)
    if роль == "manager":
        if сущ != "spec":
            НАХОДКИ.append(f"{н} нажатие на закрытый пункт открыло «{сущ}»")
        стр.evaluate("() => { setPreviewEntity('contract'); }"); стр.wait_for_timeout(300)
        if стр.evaluate("() => previewEntity") != "spec":
            НАХОДКИ.append(f"{н} договор открылся в обход меню")
        if кнопки:
            НАХОДКИ.append(f"{н} у менеджера видны кнопки договора: {кнопки}")
        стр.evaluate("() => { window.__печатьДоговора = 0; const был = printContractKar; window.printContractKar = function () { window.__печатьДоговора++; }; previewEntity = 'contract'; printFromPreview(); previewEntity = 'spec'; window.printContractKar = был; }")
        if стр.evaluate("() => window.__печатьДоговора"):
            НАХОДКИ.append(f"{н} печать из окна напечатала договор менеджеру")
    else:
        if сущ != "contract":
            НАХОДКИ.append(f"{н} администратору договор не открылся: «{сущ}»")
        if "contractTermWrap" not in кнопки:
            НАХОДКИ.append(f"{н} у администратора нет поля «Срок» в договоре: {кнопки}")
    for е in [е for е in ош if "supabase.co" not in е][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {е[:160]}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for стиль in ("blank",):
                    for роль in ("manager", "admin"):
                        прогон(бр, порт, ш, стиль, роль)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: менеджер видит оба пункта договора приглушёнными со строкой «После согласования спецификации», "
          "договор не открывается ни из меню, ни в обход, не печатается; у администратора открывается — "
          "на 390 и 1440.")


if __name__ == "__main__":
    главная()
