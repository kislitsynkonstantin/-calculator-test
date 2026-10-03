#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Правила эксплуатации бани — Приложение № 3 к договору на отделку, документ окна печати.

Константин 03.10.2026, с файлом «Правила эксплуатации бани»: «сделай правила
эксплуатации в нашем шаблоне, как другие документы. Акты чуть позже сюда тоже
внедрим».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • в меню документа «Правила эксплуатации» стоит после «Договора на
    отделку»; выбор открывает «Правила эксплуатации бани», в шапке —
    «Приложение № 3» и номер договора на отделку;
  • девять разделов и все 74 пункта и строки — слово в слово по файлу
    Константина (шаблон_правил.json), номер и дата договора подставлены;
    десятый раздел — «Адреса и реквизиты», тот же блок, что в договоре;
  • визуализация из расчёта встаёт под шапку, а планировка — нет;
  • «Скрыть поля» у правил своё: договор и согласие не задевает;
  • печать: файл «Правила_эксплуатации_…», в журнале — запись о печати
    с документом;
  • менеджеру пункт закрыт; без договора на отделку пункта нет;
  • ничего не вылезает за лист, между номером пункта и текстом не меньше
    4 px («5.1.10.» заполнял колонку целиком и стоял вплотную), шрифты настоящие.

    python3 check_rules_doc.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЗДЕСЬ = pathlib.Path(__file__).parent
ШАБЛОН = json.loads((ЗДЕСЬ / "шаблон_правил.json").read_text(encoding="utf-8"))
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ПЛАН = "/scratchpad/probes/образцы_приложения2/планировка.png"

КАДР = """() => { const к = document.querySelector('#contractPreviewDoc iframe'); if (!к) return null; const д = к.contentDocument;
  const т = э => (э ? э.textContent : '').replace(/[ \\t\\n]+/g, ' ').trim(), лист = д.querySelector('.page').getBoundingClientRect();
  const за = [...д.querySelectorAll('.page *')].filter(э => { const р = э.getBoundingClientRect(); return р.width && (р.right > лист.right + 1 || р.left < лист.left - 1); }).length;
  const ш = с => { const e = д.createElement('span'); e.style.cssText = 'font:16px ' + с + ';position:absolute;visibility:hidden;white-space:nowrap'; e.textContent = 'Правила 0123'; д.body.appendChild(e); const w = e.offsetWidth; e.remove(); return w; };
  const разделы = [...д.querySelectorAll('h2.section')].map(т);
  const пункты = [...д.querySelectorAll('p.clause, ul.bullets li')].filter(э => !э.closest('.keep')).map(э => э.tagName === 'LI' ? ['•', т(э)]
    : [т(э.querySelector('.clause-num')), т(э).slice(т(э.querySelector('.clause-num')).length).trim()]);
  const рекв = д.querySelector('.keep');
  return { заголовок: т(д.querySelector('h1')), мета: т(д.querySelector('.meta')), разделы, пункты,
    склеено: [...д.querySelectorAll('.clause-num')].filter(н => { const р = д.createRange(); р.selectNodeContents(н);
      return н.getBoundingClientRect().width - р.getBoundingClientRect().width < 4; }).map(т),
    реквизиты: рекв ? т(рекв).replace(/^\\d+\\./, '') : '', снимок: decodeURIComponent((д.querySelector('.r-fig img') || {}).src || ''), за,
    шрифт: ш('Geologica') !== ш('serif') && ш('Unbounded') !== ш('serif'),
    метка: document.getElementById('previewEntityLabel').textContent.trim(),
    галочка: [...document.querySelectorAll('#previewEntityMenu .entity-check')].filter(г => г.style.opacity === '1').map(г => г.dataset.for),
    состав: getComputedStyle(document.getElementById('printSectionsBar')).display }; }"""

РЕКВ_ДОГОВОРА = """() => { const д = new DOMParser().parseFromString(buildContractHtmlKar(getContractVarsKar(2)), 'text/html');
  return д.querySelector('.keep').textContent.replace(/[ \\t\\n]+/g, ' ').trim().replace(/^\\d+\\./, ''); }"""


def меню(стр):
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)


def прогон(бр, порт, ш, роль):
    н = f"[{ш} {роль}]"
    к, стр, ош = о.начать(бр, порт, ш, роль)
    if роль == "manager":
        меню(стр)
        пункт = стр.locator('#previewEntityMenu [data-entity="rules"]')
        if not пункт.count() or "ent-locked" not in (пункт.get_attribute("class") or ""):
            НАХОДКИ.append(f"{н} пункт правил у менеджера не закрыт")
        пункт.click(force=True); стр.wait_for_timeout(500)
        if стр.evaluate("() => previewEntity") != "spec":
            НАХОДКИ.append(f"{н} менеджеру открылись правила")
        к.close(); return
    меню(стр)
    порядок = [т.split("\n")[0].strip() for т in стр.locator("#previewEntityMenu button").all_inner_texts()]
    if порядок[3:6] != ["Договор на отделку", "Правила эксплуатации", "Согласие на обработку данных"]:
        НАХОДКИ.append(f"{н} порядок меню: {порядок}")
    стр.locator('#previewEntityMenu [data-entity="rules"]').click(); стр.wait_for_timeout(1500)
    с = стр.evaluate(КАДР)
    if not с or с["заголовок"] != "Правила эксплуатации бани":
        НАХОДКИ.append(f"{н} в кадре не правила: {с and с['заголовок']}"); к.close(); return
    номер = стр.evaluate("() => getContractVarsKar(2).contractNumKar")
    дата = стр.evaluate("() => getContractVarsKar(2).contractDate") or "________"
    if "Приложение № 3" not in с["мета"] or номер not in с["мета"] or not номер.endswith("-ОТД"):
        НАХОДКИ.append(f"{н} шапка: «{с['мета']}», номер договора {номер}")
    if [р.replace(".", ". ", 1) for р in с["разделы"]] != ШАБЛОН["разделы"] + ["10. Адреса и реквизиты"]:
        НАХОДКИ.append(f"{н} разделы: {с['разделы']}")
    ждём = [[п, т.replace("{номер}", номер).replace("{дата}", дата)] for п, т in ШАБЛОН["пункты"]]
    if с["пункты"] != ждём:
        разн = [(i, а, б) for i, (а, б) in enumerate(zip(с["пункты"], ждём)) if а != б][:3]
        НАХОДКИ.append(f"{н} текст правил расходится с файлом: пунктов {len(с['пункты'])} из {len(ждём)}; {разн}")
    if с["реквизиты"] != стр.evaluate(РЕКВ_ДОГОВОРА):
        НАХОДКИ.append(f"{н} реквизиты правил не те, что в договоре")
    if с["метка"] != "Правила эксплуатации" or с["галочка"] != ["rules"] or с["состав"] != "none":
        НАХОДКИ.append(f"{н} кнопка «{с['метка']}», галочка {с['галочка']}, «Состав» {с['состав']}")
    if с["снимок"]:
        НАХОДКИ.append(f"{н} снимков в расчёте нет, а в правилах картинка {с['снимок'][:60]}")
    if с["за"]:
        НАХОДКИ.append(f"{н} в кадре правил {с['за']} элементов за краем листа")
    if с["склеено"]:
        НАХОДКИ.append(f"{н} номер пункта вплотную к тексту (зазор меньше 4 px): {с['склеено']}")
    if not с["шрифт"]:
        НАХОДКИ.append(f"{н} шрифт правил не лёг")
    # Визуализация: планировка добавлена первой — под шапку встаёт визуализация.
    стр.evaluate("async (s) => { canvasAddImage(s[0]); canvasAddImage(s[1]); await new Promise(r => setTimeout(r, 400)); renderPreviewEntity(); await new Promise(r => setTimeout(r, 1500)); }", [ПЛАН, ВИЗ])
    с2 = стр.evaluate(КАДР)
    if "визуализация.jpg" not in с2["снимок"]:
        НАХОДКИ.append(f"{н} под шапкой правил не визуализация: «{с2['снимок'][-60:]}»")
    if с2["за"]:
        НАХОДКИ.append(f"{н} со снимком в кадре {с2['за']} элементов за краем листа")
    стр.screenshot(path=str(м.СНИМКИ / f"rules-{ш}.png"))
    # «Скрыть поля» — своё у правил.
    СОСТ = """() => ({ скрыты: !!(document.querySelector('#contractPreviewDoc iframe') || {}).contentDocument?.body.classList.contains('hl-off'),
      кнопка: document.getElementById('contractHlToggleLabel').textContent.trim(), док: previewEntity })"""
    стр.locator("#contractHlToggleBtn").click(); стр.wait_for_timeout(600)
    п1 = стр.evaluate(СОСТ)
    меню(стр); стр.locator('#previewEntityMenu [data-contract="2"]').click(); стр.wait_for_timeout(1200)
    п2 = стр.evaluate(СОСТ)
    меню(стр); стр.locator('#previewEntityMenu [data-entity="consent"]').click(); стр.wait_for_timeout(1200)
    п3 = стр.evaluate(СОСТ)
    меню(стр); стр.locator('#previewEntityMenu [data-entity="rules"]').click(); стр.wait_for_timeout(1200)
    п4 = стр.evaluate(СОСТ)
    if not (п1["скрыты"] and п1["кнопка"] == "Показать поля"):
        НАХОДКИ.append(f"{н} «Скрыть поля» у правил не сработала: {п1}")
    if п2["скрыты"] or п3["скрыты"]:
        НАХОДКИ.append(f"{н} поля правил скрыли — у договора или согласия тоже скрыты: {п2} {п3}")
    if not (п4["скрыты"] and п4["кнопка"] == "Показать поля"):
        НАХОДКИ.append(f"{н} вернулись к правилам — поля снова видны: {п4}")
    стр.locator("#contractHlToggleBtn").click(); стр.wait_for_timeout(600)
    # Печать и журнал.
    стр.evaluate("""() => { window.__было = (window.__ТАБЛИЦЫ.events || []).length; window.__заголовок = null;
      new MutationObserver(() => { const ф = document.getElementById('contractPrintFrame'); if (ф && !ф.__пойман) { ф.__пойман = true; ф.contentWindow.print = () => { window.__заголовок = ф.contentDocument.title; window.__h1 = ф.contentDocument.querySelector('h1').textContent; }; } }).observe(document.body, { childList: true });
      printFromPreview(); }""")
    for _ in range(40):
        стр.wait_for_timeout(200)
        if стр.evaluate("() => window.__заголовок"): break
    заг = стр.evaluate("() => window.__заголовок") or ""
    if not заг.startswith("Правила_эксплуатации_") or стр.evaluate("() => window.__h1") != "Правила эксплуатации бани":
        НАХОДКИ.append(f"{н} печать правил: файл «{заг}», заголовок «{стр.evaluate('() => window.__h1')}»")
    з = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).slice(window.__было).filter(е => е.event_type === 'contract_printed').map(е => (е.details || {}).rows)")
    if len(з) != 1 or not any(р["k"] == "Документ" and "Правила эксплуатации" in р["b"] for р in з[0]):
        НАХОДКИ.append(f"{н} запись журнала о печати правил: {з}")
    # Без договора на отделку правил нет.
    б = стр.evaluate("""() => { const было = contractsConfig; contractsConfig = contractsConfig.filter(c => c.id !== 2);
      setPreviewEntity('spec'); обновитьМенюДокумента();
      const видно = getComputedStyle(document.querySelector('#previewEntityMenu [data-entity="rules"]')).display !== 'none';
      setPreviewEntity('rules'); const открыто = previewEntity; contractsConfig = было; setPreviewEntity('spec');
      return { видно, открыто }; }""")
    if б["видно"] or б["открыто"] != "spec":
        НАХОДКИ.append(f"{н} без договора на отделку правила доступны: {б}")
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
    print("Чисто: «Правила эксплуатации бани» — документ окна печати после договора на отделку: Приложение № 3 с его "
          "номером, девять разделов слово в слово по файлу, реквизиты как в договоре, визуализация под шапкой; "
          "«Скрыть поля» своё; печать «Правила_эксплуатации_…» с записью в журнале; менеджеру закрыто, без договора "
          "на отделку пункта нет — на 390 и 1440.")


if __name__ == "__main__":
    главная()
