#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Имя файла при «Сохранить как PDF» начинается с типа документа.

Константин 06.10.2026, снимком окна «Сохранить как» в Яндекс Браузере: договор
предлагался к сохранению под именем «Спецификация — Каркасные бани». «Когда
сохраняешь документ — пиши в названии тот тип документа, который выбран. Если
Договор — то пишет договор. Просто часто никто не смотрит и потом получаем с
неверными названиями».

Chrome и Яндекс Браузер берут имя файла из заголовка того документа, который
печатают, а при печати скрытого кадра — из заголовка самой страницы. Проба
печатает каждый документ окна печати и смотрит заголовок в ту минуту, когда
вызывается печать:
  • спецификация, «Вид и план», платёжный план и сравнение комплектаций
    открываются своим окном — его заголовок начинается с типа документа и
    содержит фамилию Заказчика;
  • основной договор, договор на отделку, правила эксплуатации и согласие
    печатаются кадром — в минуту печати заголовок самой страницы равен имени
    документа («Договор_КАР_…», «Договор_ОТД_…», «Правила_эксплуатации_…»,
    «Согласие_ПДн_…»), а после печати возвращается прежний.

    python3 check_print_titles.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ФАМИЛИЯ = "Петров"

# Кадр печати договора: печать подменяется записью заголовка страницы в эту минуту.
ЛОВУШКА = """() => { window.__заголовки = []; window.__стр = document.title;
  new MutationObserver(сп => сп.forEach(з => з.addedNodes.forEach(у => {
    if (у.id === 'contractPrintFrame') { try { у.contentWindow.print = () => window.__заголовки.push(document.title); } catch (e) {} }
  }))).observe(document.body, { childList: true }); }"""


def окно(к, стр, вызов, имя, начало):
    try:
        with к.expect_page(timeout=15000) as об:
            стр.evaluate(вызов)
        п = об.value
        п.wait_for_timeout(1200)
        з = п.title()
        п.close()
    except Exception as е:
        НАХОДКИ.append(f"[{имя}] окно печати не открылось: {str(е).splitlines()[0][:120]}")
        return
    if not з.startswith(начало) or ФАМИЛИЯ not in з:
        НАХОДКИ.append(f"[{имя}] имя файла «{з}» — ждали начало «{начало}» и фамилию Заказчика")


def кадр(стр, сущность, ид, имя, начало):
    стр.evaluate("""async ([с, ид]) => { window.__заголовки = [];
      if (ид) { printActiveContractId = ид; const c = contractsConfig.find(x => x.id === ид); if (c) printActiveSections = new Set(c.sections); }
      setPreviewEntity(с); await new Promise(r => setTimeout(r, 700)); printFromPreview(); }""", [сущность, ид])
    стр.wait_for_timeout(5000)
    р = стр.evaluate("() => ({ з: window.__заголовки.slice(), сейчас: document.title, было: window.__стр })")
    if not р["з"]:
        НАХОДКИ.append(f"[{имя}] печать не вызвана")
        return
    if not р["з"][0].startswith(начало):
        НАХОДКИ.append(f"[{имя}] в минуту печати заголовок страницы «{р['з'][0]}» — ждали «{начало}…»")
    # После печати (afterprint) прежний заголовок возвращается.
    стр.evaluate("() => { const к = document.getElementById('contractPrintFrame'); if (к) к.contentWindow.dispatchEvent(new Event('afterprint')); window.dispatchEvent(new Event('afterprint')); }")
    стр.wait_for_timeout(200)
    if стр.evaluate("() => document.title") != р["было"]:
        НАХОДКИ.append(f"[{имя}] после печати заголовок страницы не вернулся: «{стр.evaluate('() => document.title')}»")


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            к, стр, ош = о.начать(бр, порт, 1440, "admin")
            стр.evaluate(f"() => {{ const п = document.getElementById('clientName'); п.value = '{ФАМИЛИЯ} Иван Иванович'; п.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
            стр.evaluate(ЛОВУШКА)
            окно(к, стр, "async () => { setPreviewEntity('spec'); await new Promise(r => setTimeout(r, 500)); printFromPreview(); }", "спецификация", "Спецификация_")
            окно(к, стр, "async () => { setPreviewEntity('appx'); await new Promise(r => setTimeout(r, 900)); printFromPreview(); }", "вид и план", "Вид_и_план_")
            окно(к, стр, "() => printPaymentPlan()", "платёжный план", "Платёжный_план_")
            окно(к, стр, "() => printKompl()", "комплектации", "Комплектации_")
            кадр(стр, "contract", 1, "основной договор", "Договор_КАР_")
            кадр(стр, "contract", 2, "договор на отделку", "Договор_ОТД_")
            кадр(стр, "rules", None, "правила", "Правила_эксплуатации_")
            кадр(стр, "consent", None, "согласие", "Согласие_ПДн_")
            for е in ош[:3]:
                НАХОДКИ.append(f"ошибка страницы: {е[:160]}")
            к.close(); бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: имя файла при сохранении в PDF начинается с типа документа — спецификация, «Вид и план», платёжный "
          "план, комплектации своим окном; оба договора, правила и согласие — заголовком страницы на время печати, "
          "после печати прежний заголовок возвращается.")


if __name__ == "__main__":
    главная()
