#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Правила эксплуатации бани — Приложение № 3 к договору на отделку, документ окна печати.

Константин 03.10.2026, с файлом «Правила эксплуатации бани»: «сделай правила
эксплуатации в нашем шаблоне, как другие документы. Акты чуть позже сюда тоже
внедрим».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • в меню документа «Правила эксплуатации» стоит после «Договора на
    отделку»; правила — Приложение № 3 к обоим договорам (03.10.2026: «ставь
    приложение 3 Правила эксплуатации к двум договорам»): в шапке оба номера,
    в перечнях приложений обоих договоров № 3 — правила, акт площадки — № 5
    основного; один договор — один номер, ни одного — пункта нет;
  • предмет по парной: с парной — «каркасного строения с парным отделением
    (бани)», без — «каркасного строения», «Строение» вместо «бани» во всём
    тексте с согласованием рода и п. 1.7 о парной, печи и дымоходе; пп. 2.1–2.3
    без парной заменены строкой «Строение — каркасное здание по проекту,
    указанному в Договоре», раздел 2 пронумерован 2.1–2.5;
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
    if not с or с["заголовок"] != "Правила эксплуатации каркасного строения с парным отделением (бани)":
        НАХОДКИ.append(f"{н} в кадре не правила: {с and с['заголовок']}"); к.close(); return
    номер = стр.evaluate("() => getContractVarsKar(2).contractNumKar")
    номер1 = стр.evaluate("() => getContractVarsKar(1).contractNumKar")
    дата = стр.evaluate("() => getContractVarsKar(2).contractDate") or "________"
    номера = f"№\u00a0{номер1} и №\u00a0{номер}"
    if "Приложение № 3" not in с["мета"] or f"к Договорам подряда {номера}" not in с["мета"] or not номер.endswith("-ОТД") or not номер1.endswith("-КАР"):
        НАХОДКИ.append(f"{н} шапка: «{с['мета']}», ждали оба договора: {номера}")
    if [р.replace(".", ". ", 1) for р in с["разделы"]] != ШАБЛОН["разделы"] + ["10. Адреса и реквизиты"]:
        НАХОДКИ.append(f"{н} разделы: {с['разделы']}")
    ждём = [[п, т.replace("{номера}", номера).replace("{дата}", дата)] for п, т in ШАБЛОН["пункты"]]
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
    if not заг.startswith("Правила_эксплуатации_") or стр.evaluate("() => window.__h1") != "Правила эксплуатации каркасного строения с парным отделением (бани)":
        НАХОДКИ.append(f"{н} печать правил: файл «{заг}», заголовок «{стр.evaluate('() => window.__h1')}»")
    з = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).slice(window.__было).filter(е => е.event_type === 'contract_printed').map(е => (е.details || {}).rows)")
    if len(з) != 1 or not any(р["k"] == "Документ" and "Правила эксплуатации" in р["b"] for р in з[0]):
        НАХОДКИ.append(f"{н} запись журнала о печати правил: {з}")
    # Один договор — один номер в шапке; ни одного — правил нет.
    б = стр.evaluate("""() => { const было = contractsConfig; const т = () => document.querySelector('#contractPreviewDoc iframe').contentDocument;
      const видно = () => getComputedStyle(document.querySelector('#previewEntityMenu [data-entity="rules"]')).display !== 'none';
      contractsConfig = было.filter(c => c.id !== 2); setPreviewEntity('spec'); обновитьМенюДокумента();
      const один = { видно: видно() }; setPreviewEntity('rules'); один.открыто = previewEntity; один.мета = previewEntity === 'rules' ? т().querySelector('.meta').textContent.replace(/\\s+/g, ' ').trim() : '';
      contractsConfig = []; setPreviewEntity('spec'); обновитьМенюДокумента();
      const ни = { видно: видно() }; setPreviewEntity('rules'); ни.открыто = previewEntity;
      contractsConfig = было; setPreviewEntity('spec'); обновитьМенюДокумента();
      return { один, ни }; }""")
    if not б["один"]["видно"] or б["один"]["открыто"] != "rules" or f"к Договору подряда № {номер1}" not in б["один"]["мета"] or "-ОТД" in б["один"]["мета"]:
        НАХОДКИ.append(f"{н} только основной договор — правила к нему одному: {б['один']}")
    if б["ни"]["видно"] or б["ни"]["открыто"] != "spec":
        НАХОДКИ.append(f"{н} договоров нет, а правила доступны: {б['ни']}")
    # Перечень приложений: № 3 — правила в обоих договорах, акт площадки — № 5 основного.
    пр = стр.evaluate("""() => [1, 2].map(ид => [...[...new DOMParser().parseFromString(buildContractHtmlKar(getContractVarsKar(ид)), 'text/html').querySelectorAll('ol.lettered')].pop().querySelectorAll('li')].map(л => л.textContent.trim()))""")
    if пр[0] != ["Приложение № 1 (Спецификация)", "Приложение № 2 (Визуализация и планировка)", "Приложение № 3 (Правила эксплуатации)",
                 "Приложение № 4 (Акт выполненных работ)", "Приложение № 5 (Акт приема-передачи строительной площадки)."] or \
       пр[1] != ["Приложение № 1 (Спецификация)", "Приложение № 2 (Визуализация и планировка)", "Приложение № 3 (Правила эксплуатации)",
                 "Приложение № 4 (Акт выполненных работ)."]:
        НАХОДКИ.append(f"{н} перечни приложений договоров: {пр}")
    # Без парной: «каркасного строения», «Строение» вместо «бани», п. 1.7.
    стр.evaluate("""() => { OPTIONS.filter(o => o.section === 'steam' || o.section === 'stove').forEach(o => { checkedOptions[o.id] = false; });
      ['steam', 'stove'].forEach(к => { try { (getCustomOpts(к) || []).forEach(co => { co.checked = false; }); } catch (e) {} }); calc(); setPreviewEntity('rules'); }""")
    стр.wait_for_timeout(1200)
    без = стр.evaluate("""() => { const д = document.querySelector('#contractPreviewDoc iframe').contentDocument; const т = д.body.textContent.replace(/\\s+/g, ' ');
      return { h1: д.querySelector('h1').textContent.trim(), баня: (т.match(/[Бб]ан(я|и|е|ю|ей)(?![а-яё])/g) || []), п17: т.includes('1.7.Положения настоящих Правил о парном отделении, печи и дымоходе применяются, если они есть в Строении.'),
        вступление: т.includes('каркасного строения (далее – Строение)'), род: т.includes('Строение не должно оставаться') && т.includes('Строение считается введенным') && т.includes('режим его эксплуатации'),
        титул: д.title,
        // Раздел 2 без парной: пп. 2.1–2.3 заменены определением Строения, нумерация сдвинута (08.10.2026: «Да, замени»).
        р2: [...д.querySelectorAll('.clause-num')].map(н => н.textContent.trim()).filter(н => /^2\.\d+\.$/.test(н)),
        п21: т.includes('2.1.Строение — каркасное здание по проекту, указанному в Договоре.'),
        парнаяКлюч: т.includes('Ключевым функциональным элементом'), помещенияБани: т.includes('Дополнительными помещениями, в зависимости от проекта') }; }""")
    if без["h1"] != "Правила эксплуатации каркасного строения" or без["титул"] != "Правила эксплуатации каркасного строения":
        НАХОДКИ.append(f"{н} без парной заголовок «{без['h1']}», title «{без['титул']}»")
    if без["баня"] or not без["п17"] or not без["вступление"] or not без["род"]:
        НАХОДКИ.append(f"{н} без парной текст: осталось «баня» {без['баня']}, п. 1.7 {без['п17']}, вступление {без['вступление']}, согласование рода {без['род']}")
    if без["р2"] != ["2.1.", "2.2.", "2.3.", "2.4.", "2.5."] or not без["п21"] or без["парнаяКлюч"] or без["помещенияБани"]:
        НАХОДКИ.append(f"{н} без парной раздел 2: номера {без['р2']}, п. 2.1 «Строение — каркасное здание…» {без['п21']}, "
                       f"осталось о парной как ключевом элементе {без['парнаяКлюч']}, о помещениях бани {без['помещенияБани']}")
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
    print("Чисто: правила эксплуатации — Приложение № 3 к обоим договорам (оба номера в шапке, № 3 в перечнях, акт "
          "площадки — № 5 основного; один договор — один номер, ни одного — пункта нет); предмет по парной, без парной — "
          "«Строение» во всём тексте и п. 1.7; текст по файлу, реквизиты как в договоре, визуализация, «Скрыть поля», "
          "печать, журнал, замок, зазор номера — на 390 и 1440.")


if __name__ == "__main__":
    главная()
