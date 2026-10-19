#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приходный ордер: сумма платежа правится — режимом правки, как текст договора.

Константин 19.10.2026: «В приходника сделай, чтобы можно было менять сумму.
Такой же режим правок сделай, как в договоре. Сумму может менять только
Редактор, Администратор и Специалист».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • у администратора над листом ордера «Изменить сумму»; режим правки —
    полоса «Правка суммы» с «Готово» и полем у каждого отмеченного платежа;
  • набранная сумма идёт в ордер: итог в панели, сумма прописью, НДС;
    поле при наборе не теряет фокус и набранное; сумма, равная графику,
    в поле остаётся, пока его не отпустили; график платежей не меняется;
  • отпущенное поле — одна строка журнала «было → стало»;
  • после «Готово» над листом строка «Сумма в ордере изменена: № … вместо …
    по графику · кто, роль, дата»; правка переживает сохранение расчёта;
  • «Вернуть» возвращает сумму по графику, тоже строкой журнала;
  • два платежа — в основании суммы обоих с правкой;
  • роли: редактор — кнопка есть; специалист — есть, когда ордер открыт
    согласованием; менеджер после согласования видит строку о правке, но
    кнопки и полей у него нет, и режим в обход кнопки не включается;
    подписанный договор правку суммы не закрывает;
  • вёрстка на 390 и 1440: панель без прокрутки вбок, поля нажатия не меньше
    44 px.

    python3 check_cash_amount_edit.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
import check_cash_receipt as кр
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def деньги(x):
    return f"{x:,}".replace(",", " ")


ЖУРНАЛ = """() => { window.__журнал = []; const был = window.logEvent;
  window.logEvent = (т, д) => { window.__журнал.push([т, JSON.stringify(д)]); try { return был(т, д); } catch (e) {} }; }"""

ПАНЕЛЬ = """() => { const п = document.querySelector('#contractPreviewDoc .ко-панель'); if (!п || п.hidden) return null;
  const норм = т => (т || '').replace(/[\\u00a0\\u202f]/g, ' ').replace(/\\s+/g, ' ').trim();
  return { кнопка: !!п.querySelector('.ко-править'), правка: !!п.querySelector('.ко-правка'), поля: п.querySelectorAll('.ко-сум').length,
    статус: норм((п.querySelector('.ко-статус') || {}).innerText), итог: норм((п.querySelector('.ко-итог b') || {}).textContent),
    фокус: document.activeElement && document.activeElement.classList.contains('ко-сум') ? document.activeElement.value : null }; }"""


def на_ордер(стр):
    стр.evaluate("() => { document.getElementById('managerName').value = 'Петров Иван Сергеевич'; document.getElementById('clientName').value = 'Соколов Андрей Викторович';"
                 " const ч = document.getElementById('cashDiscountCheck'); ч.checked = true; ч.dispatchEvent(new Event('change', { bubbles: true })); calc(); }")
    стр.wait_for_timeout(300)
    стр.evaluate("() => выбратьОрдер()"); стр.wait_for_timeout(1200)


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к, стр, ош = о.начать(бр, порт, ш, "admin")
    на_ордер(стр)
    if стр.evaluate("() => previewEntity") != "cash":
        плохо(f"{н} ордер не открылся"); к.close(); return
    стр.evaluate(ЖУРНАЛ)
    граф = стр.evaluate("() => getContractVarsKar(1).paymentRows.map(р => р.amount)")
    п = стр.evaluate(ПАНЕЛЬ)
    if not п or not п["кнопка"] or п["правка"]:
        плохо(f"{н} у администратора нет «Изменить сумму» над ордером: {п}"); к.close(); return
    стр.locator("#contractPreviewDoc .ко-править").click(); стр.wait_for_timeout(400)
    п = стр.evaluate(ПАНЕЛЬ)
    if not п["правка"] or п["поля"] != 1:
        плохо(f"{н} режим правки суммы: {п}")
    поле = стр.locator("#koSum-1")
    поле.click()
    поле.press_sequentially("300000", delay=40); стр.wait_for_timeout(500)
    п = стр.evaluate(ПАНЕЛЬ)
    if п["фокус"] != "300000":
        плохо(f"{н} поле суммы при наборе потеряло фокус или набранное: {п['фокус']!r}")
    л = стр.evaluate(кр.ЛИСТ)["текст"]
    коп = round(300000 * 5 / 105 * 100)
    ндс = f"НДС 5 % — {деньги(коп // 100)} руб. {коп % 100:02d} коп."
    прописью = стр.evaluate("() => суммаПрописью(300000)")
    if прописью not in л or ндс not in л or деньги(300000) not in п["итог"]:
        плохо(f"{н} сумма 300 000 не дошла до ордера: итог {п['итог']}, прописью {прописью in л}, НДС {ндс in л}")
    if стр.evaluate("() => getContractVarsKar(1).paymentRows.map(р => р.amount)") != граф:
        плохо(f"{н} правка суммы ордера поменяла график платежей")
    стр.screenshot(path=str(СНИМКИ / f"cash-amount-edit-{ш}.png"))
    for т in стр.evaluate(кр.ВЁРСТКА):
        плохо(f"{н} панель в правке: {т}")
    поле.press("Tab"); стр.wait_for_timeout(300)
    ж = стр.evaluate("() => window.__журнал.filter(з => з[0] === 'cash_amount_edited')")
    if len(ж) != 1 or деньги(граф[0]) not in ж[0][1].replace(" ", " ").replace(" ", " ") or "300" not in ж[0][1]:
        плохо(f"{н} журнал правки суммы: {ж}")
    # Сумма, равная графику, остаётся в поле, пока его не отпустили.
    поле.click(); поле.fill("")
    поле.press_sequentially(str(граф[0]), delay=20); стр.wait_for_timeout(300)
    if стр.evaluate(ПАНЕЛЬ)["фокус"] != str(граф[0]):
        плохо(f"{н} сумма, равная графику, пропала из поля при наборе")
    поле.fill(""); поле.press_sequentially("300000", delay=20); поле.press("Tab"); стр.wait_for_timeout(300)
    стр.locator("#contractPreviewDoc .ко-правка .пр-готово").click(); стр.wait_for_timeout(400)
    п = стр.evaluate(ПАНЕЛЬ)
    if п["правка"] or f"№ 1 — {деньги(300000)}" not in п["статус"] or f"вместо {деньги(граф[0])}" not in п["статус"] or "Анна Соколова" not in п["статус"]:
        плохо(f"{н} строка о правке над ордером: «{п['статус']}»")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"cash-amount-status-{ш}.png"))
    # Сохранение расчёта.
    сх = стр.evaluate("() => { const с = JSON.parse(JSON.stringify(ордерДляСохранения())); _ордер.суммы = {}; ордерИзСохранённого(с); return суммаПлатежаОрдера(getContractVarsKar(1).paymentRows[0]); }")
    if сх != 300000:
        плохо(f"{н} правка суммы не пережила сохранение: {сх}")
    # Два платежа.
    if len(граф) > 1:
        стр.evaluate("() => { _ордер.отмечены[1] = [1, 2]; refreshContractPreview(); }"); стр.wait_for_timeout(800)
        л = стр.evaluate(кр.ЛИСТ)["текст"]
        ждали = f"платежи № 1 ({деньги(300000)} руб.) и № 2 ({деньги(граф[1])} руб.)"
        if ждали not in л:
            и = л.find("платежи")
            плохо(f"{н} два платежа с правкой: ждали «{ждали}», на листе {л[и:и + 80]!r}")
        стр.evaluate("() => { _ордер.отмечены[1] = [1]; refreshContractPreview(); }"); стр.wait_for_timeout(800)
    # Вернуть.
    стр.locator("#contractPreviewDoc .ко-править").click(); стр.wait_for_timeout(300)
    стр.locator('#contractPreviewDoc .ко-правка [data-ko-a="вернуть"]').click(); стр.wait_for_timeout(600)
    л = стр.evaluate(кр.ЛИСТ)["текст"]
    ж = стр.evaluate("() => window.__журнал.filter(з => з[0] === 'cash_amount_edited').length")
    if стр.evaluate("() => суммаПрописью(getContractVarsKar(1).paymentRows[0].amount)") not in л or ж != 2:
        плохо(f"{н} «Вернуть» не вернул сумму по графику или не записал журнал: записей {ж}")
    for е in [е for е in ош if "supabase.co" not in е][:3]:
        плохо(f"{н} ошибка страницы: {е[:160]}")
    к.close()


def роли(бр, порт):
    for роль, ждём, согл, подписан in (("editor", True, False, False), ("specialist", True, True, False),
                                         ("manager", False, True, False), ("admin", True, False, True)):
        н = f"[{роль}{' после согласования' if согл else ''}{' подписан' if подписан else ''}]"
        к, стр, ош = о.начать(бр, порт, 1440, роль)
        if согл:
            стр.evaluate("() => { window.согласованиеДействует = () => true; }")
        if подписан:
            стр.evaluate("() => { window.договорПодписан = () => true; }")
        стр.evaluate("() => { _ордер.суммы = { 1: { 1: { сумма: 250000, кто: 'Анна Соколова', роль: 'editor', когда: new Date().toISOString() } } }; }")
        на_ордер(стр)
        if стр.evaluate("() => previewEntity") != "cash":
            плохо(f"{н} ордер не открылся"); к.close(); continue
        п = стр.evaluate(ПАНЕЛЬ)
        if п["кнопка"] != ждём:
            плохо(f"{н} кнопка «Изменить сумму» {'есть' if п['кнопка'] else 'нет'}, ждали {'есть' if ждём else 'нет'}")
        if f"№ 1 — {деньги(250000)}" not in п["статус"]:
            плохо(f"{н} не видно строки о правке суммы: «{п['статус']}»")
        if роль == "manager":
            стр.evaluate("() => { _правкаОрдера = true; refreshContractPreview(); }"); стр.wait_for_timeout(600)
            if стр.evaluate(ПАНЕЛЬ)["поля"]:
                плохо(f"{н} режим правки суммы включается в обход кнопки")
        к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            роли(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: сумма приходного ордера правится режимом правки — у администратора, редактора и специалиста с открытым "
          "ордером; сумма идёт в итог, прописью и НДС, график не меняется; журнал «было → стало»; строка о правке над "
          "листом; «Вернуть»; сохранение; менеджер видит правку, но не правит; на 390 и 1440.")


if __name__ == "__main__":
    главная()
