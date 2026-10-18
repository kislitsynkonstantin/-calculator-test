#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Правка текста договора прямо в окне печати — вариант А макета contract-edit-v1.

Константин 17.10.2026, снимком макета: «Делаем — вариант А, доступна для
ролей Администратор, Редактор, Специалист».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • кнопка «Править текст» — в строке над листом (в панели окна печати она
    уводила кнопки во второй ряд), у администратора, редактора и специалиста, у
    которого договор открыт; у специалиста до согласования и у менеджера её
    нет; менеджер видит договор с правками и строку над листом;
  • в правке у каждого пункта «Изменить» и «Убрать», у изменённого — «Вернуть
    типовой»; суммы в пункте — метки, которые не правятся, и в правке они
    хранятся метками ({1}, {2}), а в печать встают значения из расчёта;
  • правка абзаца, строки списка (одну поправили, одну стёрли), убранный
    пункт: в печати его нет, номера в разделе подряд, ссылка «п. 5.6» в
    пункте о кредите стала «п. 5.5»; ссылка на убранный пункт — предупреждение
    в списке изменений;
  • печать, PDF и Word — с правками, без инструментов, зачёркиваний и черты:
    черта у изменённого пункта только на экране;
  • строка «Текст договора изменён: N пунктов · кто, роль, дата» вне правки;
  • каждая правка — строка журнала «Текст договора изменён» с пунктом, было и
    стало; «Вернуть» — тоже;
  • правки едут в пресете (collectState → restoreState), у нового проекта
    договор типовой, у договора на отделку — свои;
  • во вкладке «Проверка» — «Основной договор: изменено N пунктов — сверить с
    типовым», нажатие открывает договор в режиме правки;
  • типовой текст пункта обновился — пометка с «Оставить правку» и «Вернуть
    типовой»;
  • вид: ничего не вылезает за экран, подписи полосы читаются (от 4,5 : 1) днём
    и ночью, площадь нажатия кнопок пункта — не меньше 32 px, ряд «Изменить /
    Убрать» начинается вровень с текстом пункта.

    python3 check_contract_edit.py
"""
import base64, io, os, pathlib, re, sys, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
КАДР = "document.querySelector('#contractPreviewDoc iframe').contentDocument"


def кадр(стр, js):
    return стр.evaluate("(() => { const д = " + КАДР + "; " + js + " })()")


def нажать_в_кадре(стр, действие, н):
    ок = кадр(стр, f"const к = д.querySelector('[data-pr-a=\"{действие}\"][data-n=\"{н}\"]'); if (!к) return false; к.click(); return true;")
    стр.wait_for_timeout(250)
    return ок


ПРАВИТЬ = """([н, было, стало]) => { const д = """ + КАДР + """; const р = д.querySelector('[data-pr="' + н + '"] .пр-ред');
  if (!р) return 'нет редактора';
  const обход = д.createTreeWalker(р, NodeFilter.SHOW_TEXT); let нашли = false;
  while (обход.nextNode()) { const у = обход.currentNode; if (у.textContent.includes(было)) { у.textContent = у.textContent.replace(было, стало); нашли = true; break; } }
  return нашли ? 'ок' : 'нет текста'; }"""

ПЕЧАТЬ = """() => { const д = new DOMParser().parseFromString(htmlОткрытогоДокумента(), 'text/html'); const т = э => э.textContent.replace(/\\s+/g, ' ').trim();
  const пункты = {}; д.querySelectorAll('p.clause').forEach(п => { const н = п.querySelector('.clause-num'); if (н) пункты[т(н)] = т(п).slice(т(н).length).trim(); });
  const сп23 = (() => { const п = [...д.querySelectorAll('p.clause')].find(п => т(п).startsWith('2.3.')); const с = п && п.nextElementSibling; return с && с.matches('ul') ? [...с.children].map(т) : null; })();
  return { пункты, сп23, инстр: д.querySelectorAll('.пр-инстр, del, ins, [contenteditable]').length, черта: д.querySelectorAll('p.пр-изм').length,
    сумма: String(getContractVarsKar(1).contractTotal).replace(/\\s+/g, ' ') }; }"""


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к, стр, ош = о.начать(бр, порт, ш, "admin")
    о.выбрать(стр, 1)
    кн = стр.locator(".пр-полоса .пр-править")
    if not кн.is_visible() or "Текст договора типовой" not in стр.locator(".пр-полоса").inner_text():
        НАХОДКИ.append(f"{н} у администратора над листом нет «Текст договора типовой» и «Править текст»"); к.close(); return
    кн.click(); стр.wait_for_timeout(900)
    р = кадр(стр, "return { инстр: д.querySelectorAll('.пр-инстр').length, пункты: [...д.querySelectorAll('p.clause')].filter(п => /^\\d+\\.\\d+\\.$/.test((п.querySelector('.clause-num') || {}).textContent || '')).length };")
    if р["инстр"] != р["пункты"] or р["пункты"] < 50:
        НАХОДКИ.append(f"{н} инструменты не у каждого пункта: {р}")
    if "Правка текста" not in стр.locator(".пр-полоса").inner_text() or стр.locator(".пр-полоса .пр-править").count():
        НАХОДКИ.append(f"{н} в правке нет подсказки или осталась кнопка «Править текст»")
    # 2.5 — правка абзаца.
    нажать_в_кадре(стр, "изменить", "2.5")
    if стр.evaluate(ПРАВИТЬ, ["2.5", "не более 3 рабочих дней", "не более 5 рабочих дней"]) != "ок":
        НАХОДКИ.append(f"{н} 2.5 не открылся на правку")
    нажать_в_кадре(стр, "сохранить", "2.5")
    # 2.1 — с метками сумм.
    нажать_в_кадре(стр, "изменить", "2.1")
    метки = кадр(стр, "return [...д.querySelectorAll('[data-pr=\"2.1\"] [data-ph]')].map(э => э.getAttribute('contenteditable'));")
    if метки != ["false", "false"]:
        НАХОДКИ.append(f"{н} в 2.1 метки сумм не закрыты от правки: {метки}")
    стр.evaluate(ПРАВИТЬ, ["2.1", "является твердой", "является твердой и окончательной"])
    нажать_в_кадре(стр, "сохранить", "2.1")
    # 2.3 — список: первую строку поправили, последнюю стёрли.
    нажать_в_кадре(стр, "изменить", "2.3")
    кадр(стр, "const сп = д.querySelector('ul[data-pr-ed]'); if (!сп) return; сп.children[0].textContent = 'стоимость дополнительных работ сверх Приложения № 1'; сп.lastElementChild.textContent = '';")
    нажать_в_кадре(стр, "сохранить", "2.3")
    # 5.3 убран: номера ниже сдвигаются, ссылка «п. 5.6» в пункте о кредите — на 5.5.
    нажать_в_кадре(стр, "убрать", "5.3")
    # 3.3 убран: на него ссылается 3.4 — предупреждение.
    нажать_в_кадре(стр, "убрать", "3.3")
    правки = стр.evaluate("() => JSON.parse(JSON.stringify(_правкиДоговора.kar))")
    if set(правки) != {"2.1", "2.3", "2.5", "3.3", "5.3"}:
        НАХОДКИ.append(f"{н} правки: {sorted(правки)}")
    if "{1}" not in правки.get("2.1", {}).get("части", [{}])[0].get("т", "") or "{2}" not in правки.get("2.1", {}).get("части", [{}])[0].get("т", ""):
        НАХОДКИ.append(f"{н} 2.1 сохранён без меток сумм: {правки.get('2.1')}")
    полоса = стр.locator(".пр-полоса").inner_text()
    if "На этот пункт ссылается п. 3.4" not in полоса:
        НАХОДКИ.append(f"{н} нет предупреждения о ссылке на убранный 3.3: «{полоса[:300]}»")
    if not кадр(стр, "return !!д.querySelector('[data-pr=\"2.5\"] ins') && !!д.querySelector('[data-pr=\"2.5\"] del') && д.querySelectorAll('.пр-убран').length >= 2;"):
        НАХОДКИ.append(f"{н} в правке не видно разницы у 2.5 или зачёркнутых убранных")
    стр.screenshot(path=str(СНИМКИ / f"договор-правка-{ш}.png"), full_page=False)
    # Вид полосы и инструментов.
    вид = стр.evaluate("""() => { const п = document.querySelector('.пр-полоса'), ш = innerWidth;
      const за = [...п.querySelectorAll('*')].filter(э => { const р = э.getBoundingClientRect(); return р.width && (р.right > ш + 1 || р.left < -1); }).length;
      const д = """ + КАДР + """; const кн = [...д.querySelectorAll('.пр-кн')].slice(0, 6).map(к => { const р = к.getBoundingClientRect(), б = д.defaultView.getComputedStyle(к, '::before');
        return р.height + Math.abs(parseFloat(б.top) || 0) + Math.abs(parseFloat(б.bottom) || 0); });
      // Ряд «Изменить / Убрать» начинается там же, где текст пункта (а не левее, как
      // было при отступе, посчитанном в его меньшем кегле).
      const п24 = д.querySelector('[data-pr="2.4"]'), р = д.createRange(); р.setStart(п24.querySelector('.clause-num').nextSibling, 0); р.setEnd(п24.querySelector('.clause-num').nextSibling, 1);
      const сдвиг = Math.abs(д.querySelector('.пр-инстр[data-n="2.4"] .пр-кн').getBoundingClientRect().left - р.getBoundingClientRect().left);
      return { за, кн: Math.min(...кн), сдвиг }; }""")
    if вид["за"]:
        НАХОДКИ.append(f"{н} {вид['за']} элементов полосы правки за краем экрана")
    if вид["сдвиг"] > 2:
        НАХОДКИ.append(f"{н} ряд «Изменить / Убрать» сдвинут от текста пункта на {вид['сдвиг']:.1f} px")
    if вид["кн"] < 32:
        НАХОДКИ.append(f"{н} площадь нажатия кнопок пункта {вид['кн']:.0f} px — меньше 32")
    # Готово: строка над листом, печать с правками.
    стр.locator(".пр-готово").click(); стр.wait_for_timeout(800)
    статус = стр.locator(".пр-полоса").inner_text()
    if not re.search(r"Текст договора изменён: 5 пунктов · Анна Соколова, администратор, \d\d\.\d\d\.\d{4}", статус) or "Править текст" not in статус:
        НАХОДКИ.append(f"{н} строка над листом: «{статус}»")
    if кадр(стр, "return д.querySelectorAll('.пр-инстр').length;"):
        НАХОДКИ.append(f"{н} после «Готово» инструменты остались")
    п = стр.evaluate(ПЕЧАТЬ)
    пп = п["пункты"]
    if "не более 5 рабочих дней" not in пп.get("2.5.", ""):
        НАХОДКИ.append(f"{н} в печати 2.5 без правки: «{пп.get('2.5.', '')[:90]}»")
    if "является твердой и окончательной" not in пп.get("2.1.", "") or п["сумма"] not in пп.get("2.1.", ""):
        НАХОДКИ.append(f"{н} в печати 2.1 без правки или без суммы {п['сумма']}: «{пп.get('2.1.', '')[:120]}»")
    if not п["сп23"] or len(п["сп23"]) != 3 or not п["сп23"][0].startswith("стоимость дополнительных работ сверх"):
        НАХОДКИ.append(f"{н} в печати список 2.3: {п['сп23']}")
    if "5.8." in пп or "п. 5.5" not in пп.get("5.6.", "") or "банк" not in пп.get("5.6.", ""):
        НАХОДКИ.append(f"{н} после снятия 5.3 номера или ссылка не пересчитаны: 5.6 «{пп.get('5.6.', '')[:110]}», есть 5.8 {'5.8.' in пп}")
    if "встречных обязательств" in пп.get("3.3.", "") or "3.6." in пп:
        НАХОДКИ.append(f"{н} убранный 3.3 в печати или номера раздела 3 не сдвинуты")
    if п["инстр"]:
        НАХОДКИ.append(f"{н} в печати остались инструменты, зачёркивания или поля правки: {п['инстр']}")
    # Черта у изменённого — только на экране.
    черта = стр.evaluate("""async () => { const к = document.createElement('iframe'); document.body.appendChild(к); const д = к.contentDocument; д.open(); д.write(сПалитрой(htmlОткрытогоДокумента())); д.close();
      await new Promise(r => setTimeout(r, 200)); const п = д.querySelector('p.пр-изм'); const экр = п ? к.contentWindow.getComputedStyle(п, '::before').content : null; к.remove(); return экр; }""")
    if черта in (None, "none", "normal"):
        НАХОДКИ.append(f"{н} у изменённого пункта на экране нет черты: {черта}")
    if ш == 1440:
        печать = стр.context.new_page()
        печать.set_content(стр.evaluate("() => сПалитрой(htmlОткрытогоДокумента())")); печать.emulate_media(media="print"); печать.wait_for_timeout(300)
        if печать.evaluate("() => { const п = document.querySelector('p.пр-изм'); return п ? getComputedStyle(п, '::before').content : 'нет'; }") not in ("none", "normal"):
            НАХОДКИ.append(f"{н} черта у изменённого пункта попадает в печать")
        печать.close()
        # Word.
        б64 = стр.evaluate("""async () => { const б = await договорDocx(getContractVarsKar(1)); const м = new Uint8Array(await б.arrayBuffer()); let s = '';
          for (let i = 0; i < м.length; i += 8192) s += String.fromCharCode.apply(null, м.subarray(i, i + 8192)); return btoa(s); }""")
        текст = re.sub(r"<[^>]+>", "", zipfile.ZipFile(io.BytesIO(base64.b64decode(б64))).read("word/document.xml").decode("utf8"))
        if "не более 5 рабочих дней" not in текст or "является твердой и окончательной" not in текст or "встречных обязательств" in текст:
            НАХОДКИ.append(f"{н} в Word нет правок или остался убранный пункт")
    # Журнал.
    ж = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).filter(е => е.event_type === 'contract_text_edited').map(е => (е.details || {}).rows)")
    if len(ж) != 5 or not any(р["k"] == "п. 2.5" and "3 рабочих" in р["a"] and "5 рабочих" in р["b"] for с in ж for р in с) \
            or not any(р["k"] == "п. 3.3" and р["b"] == "пункт убран" for с in ж for р in с):
        НАХОДКИ.append(f"{н} журнал правок: {len(ж)} записей, {ж[:2]}")
    if стр.evaluate("() => ({ contract_text_edited: 1 }) && (typeof EVENT_LABELS === 'undefined' ? 'нет' : '')") == "нет":
        pass
    # Проверка: пункт и переход.
    пк = стр.evaluate("() => проверкаПоЧекЛисту().замечания.filter(з => з.раздел === 'contract').map(з => [з.т, з.эл])")
    if пк != [["Основной договор: изменено 5 пунктов — сверить с типовым", "договор:1"]]:
        НАХОДКИ.append(f"{н} пункт «Проверки»: {пк}")
    стр.evaluate("() => { closePrintPreview(); кРазделуИзПроверки('contract', 'договор:1'); }"); стр.wait_for_timeout(1200)
    if not стр.evaluate("() => document.getElementById('printOverlay').style.display === 'block' && previewEntity === 'contract' && _правкаДоговора"):
        НАХОДКИ.append(f"{н} пункт «Проверки» не открыл договор в правке")
    # Из списка изменений — к пункту в листе (Константин, 18.10.2026: «по
    # нажатию на правку перекидывай на неё»): пункт встаёт в кадр экрана и
    # вспыхивает; нажатие по номеру и по отрывку — одинаково.
    ГДЕ = """(н) => { const ф = document.querySelector('#contractPreviewDoc iframe'), д = ф.contentDocument, п = д.querySelector('[data-pr="' + н + '"]');
      if (!п) return null; const ф_ = ф.getBoundingClientRect(), р = п.getBoundingClientRect(), верх = ф_.top + р.top;
      return { верх: Math.round(верх), низ: Math.round(верх + р.height), экран: innerHeight, вспышка: п.classList.contains('пр-вспышка') }; }"""
    номера = стр.evaluate("() => Object.keys(_правкиДоговора.kar).filter(н => (_типовыеПункты.kar || {})[н]).sort((а, б) => а.localeCompare(б, 'ru', { numeric: true }))")
    for н_, как in ((номера[-1], ".пр-полоса button.пр-к"), (номера[0], ".пр-полоса .пр-пункт-к")):
        стр.locator(f'{как}[data-n="{н_}"]').click(); стр.wait_for_timeout(1300)
        г = стр.evaluate(ГДЕ, н_)
        if not г or г["верх"] < 0 or г["низ"] > г["экран"] or not г["вспышка"]:
            НАХОДКИ.append(f"{н} нажатие на правку п. {н_} ({как}) не привело к пункту: {г}")
        elif н_ == номера[-1]:
            стр.screenshot(path=str(СНИМКИ / f"contract-jump-{ш}.png"))
    # Типовой текст обновился.
    стр.evaluate("() => { _правкиДоговора.kar['2.5'].база = [{ к: 'p', т: 'прежний типовой текст' }]; renderContractPreviewKarDom(); }"); стр.wait_for_timeout(500)
    if "Типовой текст пункта обновился" not in стр.locator(".пр-полоса").inner_text():
        НАХОДКИ.append(f"{н} нет пометки «типовой текст обновился»")
    стр.locator('.пр-полоса [data-pr-a="оставить"][data-n="2.5"]').click(); стр.wait_for_timeout(500)
    if "Типовой текст пункта обновился" in стр.locator(".пр-полоса").inner_text():
        НАХОДКИ.append(f"{н} «Оставить правку» не сняла пометку")
    # Вернуть типовой.
    стр.locator('.пр-полоса [data-pr-a="вернуть"][data-n="2.5"]').click(); стр.wait_for_timeout(500)
    if "2.5" in стр.evaluate("() => Object.keys(_правкиДоговора.kar)") or not стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).some(е => е.event_type === 'contract_text_edited' && ((е.details || {}).rows || []).some(р => р.k === 'п. 2.5' && р.b === 'типовой текст'))"):
        НАХОДКИ.append(f"{н} «Вернуть» не вернула 2.5 или не записала в журнал")
    # Пресет: туда и обратно; новый проект — типовой; отделка — своя.
    к2 = стр.evaluate("""() => { const с = collectState(); const было = Object.keys(с.contractTextEdits.kar).sort();
      const отд = new DOMParser().parseFromString(buildContractHtmlKar(getContractVarsKar(2)), 'text/html').querySelectorAll('p.пр-изм').length;
      selectProjectOption(1); const послеНового = Object.keys(_правкиДоговора.kar).length;
      restoreState(с); const стало = Object.keys(_правкиДоговора.kar).sort();
      return { было, послеНового, стало, отд, общий: COLLAB_REQ_KEYS.includes('contractTextEdits') }; }""")
    if к2["было"] != к2["стало"] or к2["послеНового"] or к2["отд"] or not к2["общий"] or len(к2["было"]) != 4:
        НАХОДКИ.append(f"{н} пресет и проекты: {к2}")
    # Ночь: полоса читается.
    for ночь in (False, True):
        стр.evaluate("(н) => { document.body.classList.toggle('dark', н); переключитьПравкуДоговора(true); }", ночь); стр.wait_for_timeout(400)
        кт = стр.evaluate("""() => { const ц = с => { const м = с.match(/[\\d.]+/g).map(Number); return м.slice(0, 3); };
          const я = rgb => { const к = x => { x /= 255; return x <= .03928 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; }; const [r, g, b] = rgb.map(к); return .2126 * r + .7152 * g + .0722 * b; };
          const фон = э => { while (э) { const б = getComputedStyle(э).backgroundColor; if (б && !/rgba\\(0, 0, 0, 0\\)|transparent/.test(б)) return б; э = э.parentElement; } return 'rgb(255,255,255)'; };
          const д = document.querySelector('#contractPreviewDoc iframe').contentDocument;
          return [...document.querySelectorAll('.пр-полоса .пр-баннер span, .пр-полоса .пр-пункт-в, .пр-полоса .пр-пункт-ш span, .пр-полоса .пр-низ, .пр-полоса .пр-кн, .пр-полоса .пр-пусто'), ...д.querySelectorAll('.пр-инстр .пр-кн, .пр-прим')].map(э => {
            const а = я(ц(getComputedStyle(э).color)), б = я(ц(фон(э))); return [э.className || э.tagName, ((Math.max(а, б) + .05) / (Math.min(а, б) + .05))]; }); }""")
        плохо = [(к_, round(в, 2)) for к_, в in кт if в < 4.5]
        if плохо:
            НАХОДКИ.append(f"{н}{' ночь' if ночь else ''} подписи полосы правки читаются плохо: {плохо[:4]}")
        стр.screenshot(path=str(СНИМКИ / f"договор-правка-{ш}{'-ночь' if ночь else ''}.png"))
    стр.evaluate("() => document.body.classList.remove('dark')")
    for е in [е for е in ош if "supabase.co" not in е][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {е[:160]}")
    к.close()


def роли(бр, порт):
    for роль, ждём, согл in (("editor", True, False), ("specialist", False, False), ("specialist", True, True), ("manager", False, True)):
        к, стр, ош = о.начать(бр, порт, 1440, роль)
        if согл:
            стр.evaluate("() => { window.согласованиеДействует = () => true; }")
        стр.evaluate("() => { _правкиДоговора.kar['2.5'] = { части: [{ к: 'p', т: 'Срок оплаты задатка — 5 рабочих дней.' }], база: [], кто: 'Анна Соколова', роль: 'admin', когда: new Date().toISOString() }; }")
        стр.evaluate("() => { if (договорДоступен()) выбратьДоговорОкна(1); }"); стр.wait_for_timeout(1000)
        видно = стр.locator(".пр-полоса .пр-править").count() > 0 and стр.locator(".пр-полоса .пр-править").is_visible()
        if видно != ждём:
            НАХОДКИ.append(f"[{роль}{' после согласования' if согл else ''}] кнопка «Править текст» {'есть' if видно else 'нет'}, ждали {'есть' if ждём else 'нет'}")
        if роль == "manager":
            т = стр.evaluate("() => { const п = document.querySelector('.пр-полоса'); return п && !п.hidden ? п.innerText : ''; }")
            кд = стр.evaluate("() => { const ф = document.querySelector('#contractPreviewDoc iframe'); return ф ? ф.contentDocument.body.textContent : ''; }")
            if "Текст договора изменён: 1 пункт" not in т or "Срок оплаты задатка — 5 рабочих дней" not in кд:
                НАХОДКИ.append(f"[manager] после согласования не видно договора с правкой или строки над листом: «{т[:80]}»")
            стр.evaluate("() => переключитьПравкуДоговора(true)"); стр.wait_for_timeout(300)
            if стр.evaluate("() => _правкаДоговора"):
                НАХОДКИ.append("[manager] режим правки включается в обход кнопки")
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
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: правка текста договора — кнопка у администратора, редактора и специалиста с открытым договором; "
          "абзац, метки сумм, список, снятие пункта с пересчётом номеров и ссылок, предупреждение о ссылке; печать и Word с "
          "правками и без пометок; строка над листом; журнал; пресет и новый проект; «Проверка»; «типовой обновился»; "
          "полоса в экране и читается днём и ночью — на 390 и 1440.")


if __name__ == "__main__":
    главная()
