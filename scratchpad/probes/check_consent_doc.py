#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Согласие на обработку персональных данных — отдельный документ окна печати.

Константин 02.10.2026, по отчёту о проверке договоров: «раздел с обработкой
данных вынеси в отдельный документ, прямо вкладкой (как договор, спецификация
и т. д.)», и из перечня данных — «П6 делай»: убрать то, чего компания не
собирает.

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • в обоих договорах раздела о персональных данных нет, разделы идут 1–13
    подряд, заключительные пункты — 11.1–11.8, ссылка в 11.6 ведёт на 11.4;
  • в меню документа пятым пунктом «Согласие на обработку данных»; выбор
    открывает в кадре документ «Согласие на обработку персональных данных»
    с Заказчиком и Подрядчиком, четырьмя пунктами и подписью Заказчика;
  • в перечне данных нет HTTP-заголовков, IP, cookie и уголовных
    разбирательств, номер телефона — один раз;
  • печать: файл «Согласие_ПДн_…», в журнале — «Договор отправлен на печать»
    с документом; поле «Срок» и строка «Состав» у согласия скрыты;
  • «Скрыть поля» у согласия работает и не зависит от договора (Константин,
    03.10.2026: «сделай, чтобы тут независимо от договора показывало»);
  • менеджеру пункт закрыт, как и договоры;
  • в кадре ничего не вылезает за лист, шрифты настоящие.

    python3 check_consent_doc.py
"""
import pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

СОГЛАСИЕ = """() => { const к = document.querySelector('#contractPreviewDoc iframe'); if (!к) return null; const д = к.contentDocument;
  const т = э => (э ? э.textContent : '').replace(/\\s+/g, ' ').trim(), лист = д.querySelector('.page').getBoundingClientRect();
  const за = [...д.querySelectorAll('.page *')].filter(э => { const р = э.getBoundingClientRect(); return р.width && (р.right > лист.right + 1 || р.left < лист.left - 1); }).length;
  const ш = с => { const e = д.createElement('span'); e.style.cssText = 'font:16px ' + с + ';position:absolute;visibility:hidden;white-space:nowrap'; e.textContent = 'Согласие 0123'; д.body.appendChild(e); const w = e.offsetWidth; e.remove(); return w; };
  return { заголовок: т(д.querySelector('h1')), стороны: [...д.querySelectorAll('.v1-party .ey')].map(т), пункты: [...д.querySelectorAll('p.clause .clause-num')].map(т),
    перечень: [...д.querySelectorAll('ul.bullets li')].map(т), подпись: [...д.querySelectorAll('.v1-sign .who span:last-child')].map(т), за,
    шрифт: ш('Geologica') !== ш('serif') && ш('Unbounded') !== ш('serif'),
    метка: document.getElementById('previewEntityLabel').textContent.trim(),
    галочка: [...document.querySelectorAll('#previewEntityMenu .entity-check')].filter(г => г.style.opacity === '1').map(г => г.dataset.for),
    срок: getComputedStyle(document.getElementById('contractTermWrap')).display, состав: getComputedStyle(document.getElementById('printSectionsBar')).display }; }"""

ДОГОВОР = """(ид) => { const д = new DOMParser().parseFromString(buildContractHtmlKar(getContractVarsKar(ид)), 'text/html');
  const т = э => (э ? э.textContent : '').replace(/\\s+/g, ' ').trim();
  return { разделы: [...д.querySelectorAll('h2.section')].map(т), пункты: [...д.querySelectorAll('.clause-num')].map(т),
    текст: т(д.body) }; }"""


def договоры(стр, н):
    for ид, имя in ((1, "основной"), (2, "на отделку")):
        д = стр.evaluate(ДОГОВОР, ид)
        номера = [int(re.match(r"\d+", р).group()) for р in д["разделы"]]
        if номера != list(range(1, 14)):
            НАХОДКИ.append(f"{н} {имя}: разделы {номера}")
        if any("персональных данных" in р for р in д["разделы"]) or "Принимая условия настоящего Договора" in д["текст"]:
            НАХОДКИ.append(f"{н} {имя}: в договоре остался раздел о персональных данных")
        закл = [п for п in д["пункты"] if п.startswith("11.")]
        if закл != [f"11.{i}." for i in range(1, 9)]:
            НАХОДКИ.append(f"{н} {имя}: заключительные пункты {закл}")
        if "указанным в п. 11.4" not in д["текст"] or "п. 12." in д["текст"]:
            НАХОДКИ.append(f"{н} {имя}: ссылка в 11.6 не на 11.4 или осталась ссылка на раздел 12")


def прогон(бр, порт, ш, роль):
    н = f"[{ш} {роль}]"
    к, стр, ош = о.начать(бр, порт, ш, роль)
    if роль == "manager":
        стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
        пункт = стр.locator('#previewEntityMenu [data-entity="consent"]')
        if not пункт.count() or "ent-locked" not in (пункт.get_attribute("class") or ""):
            НАХОДКИ.append(f"{н} пункт согласия у менеджера не закрыт")
        пункт.click(force=True); стр.wait_for_timeout(500)
        if стр.evaluate("() => previewEntity") != "spec":
            НАХОДКИ.append(f"{н} менеджеру открылось согласие")
        к.close(); return
    договоры(стр, н)
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
    стр.locator('#previewEntityMenu [data-entity="consent"]').click(); стр.wait_for_timeout(1500)
    с = стр.evaluate(СОГЛАСИЕ)
    if not с or с["заголовок"] != "Согласие на обработку персональных данных":
        НАХОДКИ.append(f"{н} в кадре не согласие: {с and с['заголовок']}"); к.close(); return
    if с["пункты"] != ["1.", "2.", "3.", "4."] or len(с["стороны"]) != 2 or с["подпись"] != ["дата", "подпись"]:
        НАХОДКИ.append(f"{н} состав согласия: пункты {с['пункты']}, стороны {с['стороны']}, подпись {с['подпись']}")
    весь = " ".join(с["перечень"])
    for лишнее in ("HTTP", "IP-адрес", "cookie", "уголовн"):
        if лишнее in весь:
            НАХОДКИ.append(f"{н} в перечне данных осталось «{лишнее}»")
    if весь.count("номер телефона") != 1:
        НАХОДКИ.append(f"{н} «номер телефона» в перечне {весь.count('номер телефона')} раз")
    if с["метка"] != "Согласие на обработку данных" or с["галочка"] != ["consent"]:
        НАХОДКИ.append(f"{н} подпись кнопки «{с['метка']}», галочка {с['галочка']}")
    if с["срок"] != "none" or с["состав"] != "none":
        НАХОДКИ.append(f"{н} у согласия видны «Срок» ({с['срок']}) или «Состав» ({с['состав']})")
    if с["за"]:
        НАХОДКИ.append(f"{н} в кадре согласия {с['за']} элементов за краем листа")
    if not с["шрифт"]:
        НАХОДКИ.append(f"{н} шрифт согласия не лёг")
    стр.screenshot(path=str(м.СНИМКИ / f"consent-{ш}.png"))
    # «Скрыть поля» у согласия — своё, от договора не зависит.
    СОСТ = """() => ({ скрыты: !!(document.querySelector('#contractPreviewDoc iframe') || {}).contentDocument?.body.classList.contains('hl-off'),
      кнопка: document.getElementById('contractHlToggleLabel').textContent.trim(), док: previewEntity })"""
    стр.locator("#contractHlToggleBtn").click(); стр.wait_for_timeout(600)
    п1 = стр.evaluate(СОСТ)
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
    стр.locator('#previewEntityMenu [data-contract="1"]').click(); стр.wait_for_timeout(1200)
    п2 = стр.evaluate(СОСТ)
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
    стр.locator('#previewEntityMenu [data-entity="consent"]').click(); стр.wait_for_timeout(1200)
    п3 = стр.evaluate(СОСТ)
    if not (п1["скрыты"] and п1["кнопка"] == "Показать поля"):
        НАХОДКИ.append(f"{н} «Скрыть поля» у согласия не сработала: {п1}")
    if п2["скрыты"] or п2["кнопка"] != "Скрыть поля":
        НАХОДКИ.append(f"{н} поля согласия скрыли — и у договора скрыты: {п2}")
    if not (п3["скрыты"] and п3["кнопка"] == "Показать поля"):
        НАХОДКИ.append(f"{н} вернулись к согласию — поля снова видны: {п3}")
    стр.locator("#contractHlToggleBtn").click(); стр.wait_for_timeout(600)
    # Печать и журнал.
    стр.evaluate("""() => { window.__было = (window.__ТАБЛИЦЫ.events || []).length; window.__заголовок = null;
      new MutationObserver(() => { const ф = document.getElementById('contractPrintFrame'); if (ф && !ф.__пойман) { ф.__пойман = true; ф.contentWindow.print = () => { window.__заголовок = ф.contentDocument.title; }; } }).observe(document.body, { childList: true });
      printFromPreview(); }""")
    for _ in range(40):
        стр.wait_for_timeout(200)
        if стр.evaluate("() => window.__заголовок"): break
    заг = стр.evaluate("() => window.__заголовок") or ""
    if not заг.startswith("Согласие_ПДн_"):
        НАХОДКИ.append(f"{н} файл печати согласия: «{заг}»")
    з = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).slice(window.__было).filter(е => е.event_type === 'contract_printed').map(е => (е.details || {}).rows)")
    if len(з) != 1 or not any(р["k"] == "Документ" and "Согласие" in р["b"] for р in з[0]):
        НАХОДКИ.append(f"{н} запись журнала о печати согласия: {з}")
    for е in [е for е in ош if "supabase.co" not in е][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {е[:160]}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for роль in ("admin", "manager"):
                    прогон(бр, порт, ш, роль)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: раздела о персональных данных в договорах нет, разделы 1–13 подряд; согласие — отдельный документ "
          "окна печати: свой заголовок, стороны, четыре пункта, подпись Заказчика, перечень без лишних данных, печать "
          "«Согласие_ПДн_…» с записью в журнале; менеджеру закрыто — на 390 и 1440.")


if __name__ == "__main__":
    главная()
