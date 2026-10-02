#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договор и этапы оплаты — в журнале пресета.

Константин 02.10.2026: «в историю пресета также внедри отправку договора на
печать и прочие действия по нему: изменили этапы оплат с деталями и тд».

Проба на 390 и 1440 делает действия руками там, где они делаются в окне, и
держит, что каждое легло одной записью с подробностями:
  • сумма этапа, доля этапа, сумма финального платежа — «название этапа:
    было → стало», договор — объектом записи; уход из поля без правки — ни
    одной записи;
  • добавлен, удалён этап, распределено заново, сброшено, переименование;
  • печать договора — «Договор отправлен на печать» с названием договора,
    номером, суммой и сроком; выгрузка в Word — «Договор выгружен в Word» с
    именем файла; срок — «Срок работ по договору изменён», 90 → 60;
  • все новые виды подписаны и попадают в журнал мини-окна; строка под
    действием в мини-окне называет суть, а не пуста;
  • менеджер печатью из окна договор не печатает и записи не оставляет.

    python3 check_contract_journal.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []

НОВЫЕ = "() => (window.__ТАБЛИЦЫ.events || []).slice(window.__было || 0).map(е => ({ вид: е.event_type, obj: (е.details || {}).obj, rows: (е.details || {}).rows || [], код: (е.details || {}).presetCode }))"
ОТМЕТКА = "() => { window.__было = (window.__ТАБЛИЦЫ.events || []).length; }"


def записи(стр, н, что, вид, ждём=1):
    з = [е for е in стр.evaluate(НОВЫЕ) if е["вид"] == вид]
    if len(з) != ждём:
        НАХОДКИ.append(f"{н} {что}: записей «{вид}» {len(з)}, ждали {ждём}: {стр.evaluate(НОВЫЕ)}")
    стр.evaluate(ОТМЕТКА)
    return з


def поле(стр, селектор, значение):
    п = стр.locator(селектор).first
    п.click(); п.fill(значение); п.press("Tab"); стр.wait_for_timeout(250)


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    стр, ош = к.начать(СоШрифтами(бр), порт, ш, 900, False)
    стр.evaluate("() => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'admin' }); document.getElementById('contractNumber').value = '11112222'; calc(); }")
    стр.evaluate("() => { openPaymentPlan(); }"); стр.wait_for_timeout(500)
    стр.evaluate(ОТМЕТКА)
    # Сумма этапа.
    было = стр.evaluate("() => ppState[1].amounts[0]")
    поле(стр, "#pprow_1_0 .pp-amt", str(было + 7000))
    з = записи(стр, н, "сумма этапа", "payment_plan_changed")
    if з:
        р = з[0]["rows"][0] if з[0]["rows"] else {}
        if р.get("k") != "Аванс по договору" or "₽" not in р.get("b", "") or р.get("a", "").replace(" ", " ").replace(" ", "")[:3] != str(было)[:3]:
            НАХОДКИ.append(f"{н} строка суммы этапа: {з[0]}")
        if з[0]["obj"] != "Основной договор":
            НАХОДКИ.append(f"{н} договор в записи суммы этапа: {з[0]['obj']}")
        if not з[0]["код"]:
            НАХОДКИ.append(f"{н} запись этапа без кода пресета — в журнал мини-окна не попадёт")
    # Уход из поля без правки.
    стр.locator("#pprow_1_0 .pp-amt").first.click(); стр.locator("#pprow_1_0 .pp-amt").first.press("Tab"); стр.wait_for_timeout(200)
    записи(стр, н, "уход из поля без правки", "payment_plan_changed", 0)
    # Доля этапа.
    поле(стр, "#pprow_1_2 .pp-pct", "38")
    з = записи(стр, н, "доля этапа", "payment_plan_changed")
    if з and not (з[0]["rows"] and з[0]["rows"][0]["b"] == "38 %"):
        НАХОДКИ.append(f"{н} строка доли этапа: {з[0]}")
    # Финальный платёж отделки.
    поле(стр, ".pp-contract:nth-of-type(2) .pp-final .pp-amt", "60000")
    з = записи(стр, н, "финальный платёж", "payment_plan_changed")
    if з and not (з[0]["rows"] and з[0]["rows"][0]["k"] == "Финальный платёж" and з[0]["obj"] == "Договор на отделку"):
        НАХОДКИ.append(f"{н} строка финального платежа: {з[0]}")
    # Добавить, удалить, распределить, сбросить, переименовать.
    for что, код, ключ in (("добавлен этап", "ppAddStage(2)", "Добавлен этап"),
                           ("удалён этап", "ppRemoveStage(2, ppState[2].amounts.length - 1)", "Удалён этап"),
                           ("распределено", "ppDistribute(1)", "Этапы распределены заново"),
                           ("сброшено", "ppReset(2)", "Этапы сброшены")):
        стр.evaluate(f"() => {{ {код}; }}"); стр.wait_for_timeout(150)
        з = записи(стр, н, что, "payment_plan_changed")
        if з and not (з[0]["rows"] and з[0]["rows"][0]["k"] == ключ):
            НАХОДКИ.append(f"{н} {что}: {з[0]}")
    стр.evaluate("() => { ppDistribute(2); }"); стр.evaluate(ОТМЕТКА)
    стр.locator("#pprow_1_2 .pp-label").dblclick(); стр.wait_for_timeout(200)
    стр.locator("#ppLabelInput_1_2").fill("По завершении каркаса"); стр.locator("#ppLabelInput_1_2").press("Enter")
    стр.locator("#ppSubInput_1_2").press("Enter"); стр.wait_for_timeout(400)
    з = записи(стр, н, "переименование", "payment_plan_changed")
    if з and not any(р["k"] == "Название этапа" and р["b"] == "По завершении каркаса" for р in з[0]["rows"]):
        НАХОДКИ.append(f"{н} переименование этапа: {з[0]}")
    стр.evaluate("() => { const о = document.getElementById('paymentPlanOverlay'); if (typeof closePaymentPlan === 'function') closePaymentPlan(); else о.style.display = 'none'; }")
    # Окно печати: договор на отделку, срок, печать, Word.
    стр.evaluate("() => { openPrintPreview(); }"); стр.wait_for_timeout(500)
    стр.evaluate(ОТМЕТКА)
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
    стр.locator('#previewEntityMenu [data-contract="2"]').click(); стр.wait_for_timeout(1000)
    поле(стр, "#contractTermInput", "60")
    з = записи(стр, н, "срок договора", "contract_term_changed")
    if з and not (з[0]["rows"] and з[0]["rows"][0]["a"] == "50 раб. дн." and з[0]["rows"][0]["b"] == "60 раб. дн." and "отделку" in з[0]["rows"][0]["k"]):
        НАХОДКИ.append(f"{н} строка срока: {з[0]}")
    стр.evaluate("() => { window.__печать = 0; const был = printContractKar; window.printContractKar = function () { window.__печать++; }; printFromPreview(); window.printContractKar = был; }")
    з = записи(стр, н, "печать договора", "contract_printed")
    if з:
        р = {х["k"]: х["b"] for х in з[0]["rows"]}
        if р.get("Договор") != "Договор на отделку" or not р.get("Номер", "").endswith("-ОТД") or "₽" not in р.get("Сумма", "") or р.get("Срок") != "60 раб. дн.":
            НАХОДКИ.append(f"{н} подробности печати договора: {р}")
    стр.evaluate("""async () => { window.open = () => null; window.договорDocx = async () => new Blob(['x']); await договорНаДиск(); }""")
    стр.wait_for_timeout(300)
    з = записи(стр, н, "выгрузка в Word", "contract_exported")
    if з and not any(х["k"] == "Файл" and х["b"].endswith("-ОТД.docx") for х in з[0]["rows"]):
        НАХОДКИ.append(f"{н} подробности выгрузки: {з[0]['rows']}")
    # Подписи и мини-окно.
    виды = ["contract_printed", "contract_exported", "contract_term_changed", "payment_plan_changed"]
    без = стр.evaluate("(в) => в.filter(х => !AL_ВСЕ_ВИДЫ[х] || видыЖурналаПресета().indexOf(х) === -1)", виды)
    if без:
        НАХОДКИ.append(f"{н} виды без подписи или вне журнала мини-окна: {без}")
    все = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).filter(е => ['contract_printed','contract_exported','contract_term_changed','payment_plan_changed'].includes(е.event_type))")
    стр.evaluate("() => закрытьПечать && закрытьПечать()") if стр.evaluate("() => typeof закрытьПечать === 'function'") else стр.evaluate("() => { try { closePrintPreview(); } catch (e) {} }")
    к.открыть(стр); стр.wait_for_timeout(300)
    стр.evaluate("""(все) => { const о = пресетКарточки(), д = Date.now();
      const события = все.map((е, и) => Object.assign({}, е, { id: 'е' + и, user_id: _sbUser && _sbUser.id, created_at: new Date(д - (все.length - и) * 60000).toISOString() })).reverse();
      _журналПресета = { код: о.код, события, ошибка: '', грузится: false, когда: Date.now() };
      _пкВкладка = 'l'; заполнитьКарточкуЗначка(); }""", все)
    стр.wait_for_timeout(300)
    строки = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-lg > li:not(.pc-lg-day)')].map(л => ({ что: (л.querySelector('.pc-lg-w') || {}).textContent || '', под: (л.querySelector('.pc-lg-d') || {}).textContent || '' }))")
    for ждём in ("Договор отправлен на печать", "Договор выгружен в Word", "Срок работ по договору изменён", "Платёжный план изменён"):
        if not any(ждём in с["что"] for с in строки):
            НАХОДКИ.append(f"{н} в журнале мини-окна нет «{ждём}»")
    пустые = [с["что"] for с in строки if not с["под"].strip()]
    if пустые:
        НАХОДКИ.append(f"{н} в журнале мини-окна строки без подробности: {пустые[:3]}")
    if ш == 390:
        стр.screenshot(path=str(м.СНИМКИ / "contract-journal-390.png"))
    # Менеджер: печать из окна не печатает договор и не пишет.
    стр.evaluate("() => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'manager' }); }")
    стр.evaluate(ОТМЕТКА)
    стр.evaluate("() => { previewEntity = 'contract'; window.printContractKar = function () {}; printFromPreview(); previewEntity = 'spec'; }")
    записи(стр, н, "печать менеджером", "contract_printed", 0)
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: правки этапов (сумма, доля, финальный, добавить, удалить, распределить, сбросить, переименовать), "
          "печать договора, выгрузка в Word и срок ложатся в журнал пресета по одной записи с подробностями и видны "
          "в журнале мини-окна; менеджер договор не печатает — на 390 и 1440.")


if __name__ == "__main__":
    главная()
