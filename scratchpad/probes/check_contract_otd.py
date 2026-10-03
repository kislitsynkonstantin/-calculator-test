#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договор подряда на внутреннюю отделку (-ОТД) — в окне печати рядом с основным.

Константин 01.10.2026 прислал шаблон «Отделка» в Word: «сделай его в таком же
шаблоне, как сделан основной договор», по макету contract-otd-v1 — «внедряй
договор отделки тоже на тестовый домен. Сюда в выпадающую вкладку подпиши:
— Основной договор — Договор на отделку».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • меню документа: «Спецификация», «Вид и план», «Основной договор»,
    «Договор на отделку», «Правила эксплуатации», «Согласие на обработку
    данных»; подпись кнопки и галочка — у открытого договора;
  • «Договор на отделку» — сам договор, а не заглушка: все 81 пункт слово в
    слово как в шаблоне (шаблон_договора_отд.json), номер с «-ОТД», этапы
    приёмки отделки (с передачи Объекта), гарантия 36 / 24 / 12 месяцев, Приложение № 3 —
    «Правила эксплуатации», платежи — из платёжного плана отделки, итог равен
    сумме строк и цене в 2.1;
  • «Основной договор» — прежний: «-КАР», строительство, 60 месяцев;
  • в строке «Состав» назван открытый договор и тогда, когда пустой раздел
    печи снят;
  • поле «Срок» у каждого договора своё: 90 и 50 по умолчанию, вписанное
    остаётся у своего договора;
  • печать договора отделки идёт (заглушки «скоро будет готов» нет), файл
    печати называется «Договор_ОТД_…»; .docx у роли с кнопкой Диска —
    «Договор подряда 11112222-ОТД.docx» с текстом отделки.

    python3 check_contract_otd.py
"""
import json, pathlib, re, sys, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЗДЕСЬ = pathlib.Path(__file__).parent
ШАБЛОН = json.loads((ЗДЕСЬ / "шаблон_договора_отд.json").read_text(encoding="utf-8"))["пункты"]
норм = lambda т: re.sub(r"\s+", " ", т.replace("ё", "е")).strip(" .")

ДОГОВОР = """() => { const к = document.querySelector('#contractPreviewDoc iframe'); if (!к) return null; const д = к.contentDocument;
  const текст = э => (э ? э.textContent : '').replace(/\\s+/g, ' ').trim(); const число = т => parseInt(String(т).replace(/\\D/g, ''), 10) || 0;
  const пункты = [...д.querySelectorAll('p.clause')].filter(п => п.querySelector('.clause-num')).map(п => [текст(п.querySelector('.clause-num')), текст(п).slice(текст(п.querySelector('.clause-num')).length).trim()]);
  const цена = д.querySelector('p.clause .placeholder');
  return { пункты, номер: текст(д.querySelector('.meta b')), гарантия: [...д.querySelectorAll('.bars .bar')].map(б => текст(б.querySelector('.l')) + ' ' + число(текст(б.querySelector('.v')))),
    этапы: [...д.querySelectorAll('ul.bullets')].map(у => [...у.children].map(текст)), приложения: [...д.querySelectorAll('ol.lettered')].pop() ? [...[...д.querySelectorAll('ol.lettered')].pop().children].map(текст) : [],
    суммы: [...д.querySelectorAll('.g1 .am .amt')].map(э => число(э.firstChild.textContent)), итог: д.querySelector('.g1 .ta .amt') ? число(д.querySelector('.g1 .ta .amt').firstChild.textContent) : null,
    цена: цена ? число(текст(цена)) : null, заглушка: getComputedStyle(document.getElementById('contractPreviewStub')).display !== 'none',
    подпись: document.getElementById('previewEntityLabel').textContent.trim(),
    галочка: [...document.querySelectorAll('#previewEntityMenu .entity-check')].filter(г => г.style.opacity === '1').map(г => г.dataset.for),
    срок: document.getElementById('contractTermInput').value,
    состав: (document.getElementById('printSectionsBar') || {}).textContent || '' }; }"""


def начать(бр, порт, ш, роль="admin"):
    # Договоры открыты администратору и редактору; менеджеру они закрыты до
    # согласования спецификации (check_contract_lock.py).
    к = бр.new_context(viewport={"width": ш, "height": 900}, accept_downloads=True)
    к.route("**/drive.google.com/**", lambda r: r.fulfill(status=200, body="drive"))
    стр = СоШрифтами(к).new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.add_init_script(f"window.__ТАБЛИЦЫ.profiles = [{{ id: 'u-проба', role: '{роль}', first_name: 'Анна', last_name: 'Соколова', app_settings: {{}} }}];")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      await loadSbProfile(); applyUiStyle('blank', false); applyTone('bmsk', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
      // В расчёте должна быть отделка, иначе её договор пустой: отмечаем первые опции разделов отделки.
      for (const к of ['interior', 'steam']) { const о = document.querySelector('[data-section="' + к + '"] .opt-item:not(.checked) .opt-check, #sec_' + к + ' .opt-item:not(.checked) .opt-check'); if (о) о.click(); }
      document.getElementById('contractNumber').value = '11112222'; openPrintPreview(); await new Promise(r => setTimeout(r, 400)); }""")
    return к, стр, ош


def выбрать(стр, ид):
    if not стр.evaluate("() => document.getElementById('previewEntityMenu').style.display !== 'none'"):
        стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
    пункт = стр.locator(f'#previewEntityMenu [data-contract="{ид}"]')
    if not пункт.count():
        НАХОДКИ.append(f"в меню документа нет пункта договора {ид}")
        raise SystemExit(НАХОДКИ and print("НАХОДКИ:\n" + "\n".join("  ✗ " + н for н in НАХОДКИ)) or 1)
    пункт.click(); стр.wait_for_timeout(1200)


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                к, стр, ош = начать(бр, порт, ш)
                стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
                меню = стр.evaluate("() => [...document.querySelectorAll('#previewEntityMenu [data-entity]')].filter(б => б.offsetParent).map(б => б.querySelector('span:not(.entity-check):not(.ent-name)').textContent.trim())")
                if меню != ["Спецификация", "Вид и план", "Основной договор", "Договор на отделку", "Правила эксплуатации", "Согласие на обработку данных"]:
                    НАХОДКИ.append(f"{н} меню документа: {меню}")
                # Договор на отделку
                выбрать(стр, 2)
                о = стр.evaluate(ДОГОВОР)
                if not о or о["заглушка"]:
                    НАХОДКИ.append(f"{н} вместо договора отделки — заглушка или пусто: {о and о['заглушка']}"); к.close(); continue
                if о["подпись"] != "Договор на отделку" or о["галочка"] != ["contract-2"]:
                    НАХОДКИ.append(f"{н} подпись кнопки «{о['подпись']}», галочка {о['галочка']}")
                пол = {н_: т for н_, т in о["пункты"]}
                if [н_ for н_, _ in о["пункты"]] != [н_ for н_, _ in ШАБЛОН]:
                    НАХОДКИ.append(f"{н} номера пунктов не как в шаблоне: {len(о['пункты'])} против {len(ШАБЛОН)}")
                for н_, т in ШАБЛОН:
                    а, б = норм(пол.get(н_, "")), норм(т)
                    if н_ == "2.1.":
                        а, б = re.sub(r"[\d\s]+рублей", " рублей", а), re.sub(r"[\d\s]+рублей", " рублей", б)
                    if н_ == "3.2.":
                        а = а.replace(о["срок"], "50")
                    if а != б:
                        НАХОДКИ.append(f"{н} пункт {н_} не как в шаблоне: «{а[:120]}» против «{б[:120]}»"); break
                if "11112222-ОТД" not in о["номер"]:
                    НАХОДКИ.append(f"{н} номер договора отделки: «{о['номер']}»")
                if о["гарантия"] != ["Инженерные системы 36", "Плиточные работы 24", "Отделочные работы 12"]:
                    НАХОДКИ.append(f"{н} гарантия договора отделки: {о['гарантия']}")
                if not any(э and э[0] == "передача Объекта для отделки" and "работы по внутренней отделке" in э for э in о["этапы"]):
                    НАХОДКИ.append(f"{н} этапы приёмки не отделки: {о['этапы']}")
                if not о["приложения"] or "Правила эксплуатации" not in о["приложения"][2]:
                    НАХОДКИ.append(f"{н} Приложение № 3: {о['приложения']}")
                if not о["суммы"] or о["итог"] != sum(о["суммы"]) or о["цена"] != о["итог"]:
                    НАХОДКИ.append(f"{н} платежи отделки: строки {о['суммы']}, итог {о['итог']}, цена в 2.1 {о['цена']}")
                if not re.search(r"Отделка|Договор на отделку", о["состав"]):
                    НАХОДКИ.append(f"{н} в строке «Состав» не назван договор отделки: «{о['состав'][:120]}»")
                if о["срок"] != "50":
                    НАХОДКИ.append(f"{н} срок договора отделки по умолчанию {о['срок']}, ждали 50")
                стр.fill("#contractTermInput", "45"); стр.wait_for_timeout(500)
                # Основной договор
                выбрать(стр, 1)
                к_ = стр.evaluate(ДОГОВОР)
                if к_["подпись"] != "Основной договор" or к_["галочка"] != ["contract-1"] or "11112222-КАР" not in к_["номер"] or к_["срок"] != "90":
                    НАХОДКИ.append(f"{н} основной договор: подпись «{к_['подпись']}», галочка {к_['галочка']}, номер «{к_['номер']}», срок {к_['срок']}")
                if not any("по строительству" in т for _, т in к_["пункты"]) or к_["гарантия"][0] != "Конструктив объекта 60":
                    НАХОДКИ.append(f"{н} основной договор не прежний: гарантия {к_['гарантия']}")
                выбрать(стр, 2)
                о2 = стр.evaluate(ДОГОВОР)
                if о2["срок"] != "45" or "не позднее 45 рабочих дней" not in dict(о2["пункты"]).get("3.2.", ""):
                    НАХОДКИ.append(f"{н} вписанный срок отделки не сохранился: поле {о2['срок']}, пункт «{dict(о2['пункты']).get('3.2.', '')}»")
                # Печать договора отделки
                стр.evaluate("() => { window.__печать = 0; }")
                стр.evaluate("""() => { const был = HTMLIFrameElement.prototype.focus; printContractKar(); }""")
                стр.wait_for_timeout(1500)
                имя = стр.evaluate("() => { const к = document.getElementById('contractPrintFrame'); return к ? к.contentDocument.title : null; }")
                if not имя or not имя.startswith("Договор_ОТД_11112222"):
                    НАХОДКИ.append(f"{н} печать договора отделки: имя «{имя}»")
                for о_ in [о_ for о_ in ош if "supabase.co" not in о_][:3]:
                    НАХОДКИ.append(f"{н} ошибка страницы: {о_[:160]}")
                if ш == 1440:
                    стр.screenshot(path=str(м.СНИМКИ / "contract-otd-1440.png"))
                к.close()
            # Word у роли с кнопкой Диска
            к, стр, ош = начать(бр, порт, 1440, "admin")
            выбрать(стр, 2)
            with к.expect_page(), стр.expect_download(timeout=30000) as з:
                стр.click("#contractDriveBtn")
            if з.value.suggested_filename != "Договор подряда 11112222-ОТД.docx":
                НАХОДКИ.append(f"Word: имя файла «{з.value.suggested_filename}»")
            путь = ЗДЕСЬ / "_договор_отд.docx"; з.value.save_as(str(путь))
            текст = re.sub(r"<[^>]+>", "", zipfile.ZipFile(путь).read("word/document.xml").decode("utf-8"))
            путь.unlink(missing_ok=True)
            for нужно in ("по внутренней отделке", "Правила эксплуатации", "оплата в день подписания Акта окончательной приемки выполненных работ"):
                if нужно not in текст:
                    НАХОДКИ.append(f"Word: в договоре отделки нет «{нужно}»")
            к.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в окне печати «Основной договор» и «Договор на отделку»; договор отделки — по шаблону слово в слово, "
          "с «-ОТД», своими платежами, гарантией 36 / 24 / 12 и своим сроком; печать и Word — его, на 390 и 1440.")


if __name__ == "__main__":
    главная()
