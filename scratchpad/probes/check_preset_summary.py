#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вкладка «Сводка» в мини-окне пресета.

Константин 29.09.2026 выбрал вариант А макета preset-summary-v2 («вот этот
делаем»): итог сейчас и разница с сохранением, график итога по правкам,
«Работа с пресетом» строками с отточием, крупные правки с переходом в журнал,
кто правил и состояние. Полосы диапазона нет, «Сводка» — сразу после «Пресета».

Проба держит, со шрифтами Google из файла (подменный шрифт прячет переполнение):
  • порядок вкладок: Пресет, Сводка, Журнал, Проверка;
  • счёт по всей истории, а не по 300 последним: правок больше 300 — и все
    посчитаны, открытия и печать — отдельным счётом;
  • правки подряд за три минуты — одна ступень; нулевой итог и правка без
    сдвига итога ступенью не становятся;
  • толщина, записанная открытием пресета (тот же человек, в пределах минуты),
    не идёт ни в график, ни в счёт, ни в журнал, а настоящая смена толщины —
    идёт;
  • со скидкой под итогом стоит цена со скидкой — та же строка, что в полоске
    итога, с припиской «за наличные»; без скидки строки нет;
  • «Кто правил» появляется, когда правили двое, — «Вы» и «Имя Ф.»;
  • график ведётся клавишами и указателем, под ним встаёт правка в точке;
  • крупная правка открывает себя во вкладке «Журнал» — видимой и подсвеченной;
  • ничего не выходит за правый край мини-окна, отточие не схлопывается,
    строки крупных правок не ниже 44 px — на 360, 390 и 1440, днём и ночью.

    python3 check_preset_summary.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card_fonts as ш
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS", "/tmp"))
ЛИШНИХ = 320        # правок с нулевым итогом: счёт обязан их видеть, график — нет

# Правки: (минут от сохранения, итог, кто, вид, что). Три первые подряд за две
# минуты — одна ступень; строка с нулём и строка без сдвига ступенью не станут.
ДЕНЬ = 24 * 60
ПРАВКИ = [
    (4, 4700000, "я", "options_batch", "Метка-водосток"),
    (5, 4900000, "я", "options_batch", "Метка-вентиляция"),
    (6, 5265512, "я", "options_batch", "Метка-планкен"),
    (40, 0, "я", "options_batch", "Метка-ноль"),
    (70, 5265512, "я", "discount_changed", "Метка-скидка"),
    (ДЕНЬ + 30, 5704277, "к", "options_batch", "Метка-печь"),
    (ДЕНЬ + 90, 5543120, "к", "gift_marked", "Метка-подарок"),
    (2 * ДЕНЬ + 10, 5790456, "я", "options_batch", "Метка-фундамент"),
    (2 * ДЕНЬ + 100, 5790456, "я", "thickness_changed", "Метка-толщина"),
    (2 * ДЕНЬ + 200, 5761901, "я", "options_batch", "Метка-отливы"),
]
ТОЧЕК = 6           # сохранение + ступени: планкен, печь, подарок, фундамент, отливы

ПОСЕВ = """([код, правки, лишних]) => {
  const т = window.__ТАБЛИЦЫ, я = _sbUser.id, нач = Date.now() - 3 * 86400000 + 3600000;
  const в = мин => new Date(нач + мин * 60000).toISOString();
  const д = (строки) => ({ presetCode: код, preset: 'Проба', rows: строки });
  т.events = [{ id: 'ев-сохр', user_id: я, event_type: 'preset_saved', created_at: в(0), total_price: 4600000, details: д([]) }];
  правки.forEach((п, и) => т.events.push({ id: 'ев-' + и, user_id: п[2] === 'я' ? я : 'u-коллега', event_type: п[3], created_at: в(п[0]),
    total_price: п[1], details: д(п[3] === 'discount_changed' ? [{ k: 'Скидка', a: '3 %', b: '4 %' }] : [{ k: 'Добавлены', b: п[4] }]) }));
  for (let и = 0; и < лишних; и++) т.events.push({ id: 'ев-н' + и, user_id: я, event_type: 'note_edited', created_at: в(-600 - и), total_price: 0, details: д([{ k: 'Текст', b: 'заметка ' + и }]) });
  for (let и = 0; и < 20; и++) т.events.push({ id: 'ев-о' + и, user_id: я, event_type: 'preset_opened', created_at: в(100 + и), total_price: 5265512, details: д([]) });
  for (let и = 0; и < 5; и++) т.events.push({ id: 'ев-п' + и, user_id: я, event_type: 'print', created_at: в(130 + и), total_price: 5265512, details: д([]) });
  // След открытия: толщина, записанная через 6 секунд после открытия тем же
  // человеком, — не правка; в график, счёт и журнал не идёт.
  т.events.push({ id: 'ев-след', user_id: я, event_type: 'thickness_changed', created_at: new Date(нач + 105 * 60000 + 6000).toISOString(),
    total_price: 9000000, details: д([{ k: 'Толщина', a: '150 мм', b: 'Метка-след' }]) });
  // Чужой пресет — в счёт не идёт.
  т.events.push({ id: 'ев-чужой', user_id: я, event_type: 'options_batch', created_at: в(50), total_price: 9900000, details: { presetCode: '999999', rows: [{ k: 'Добавлены', b: 'Метка-чужая' }] } });
  т.profiles = (т.profiles || []).concat([{ id: 'u-коллега', first_name: 'Сергей', last_name: 'Волков', email: 'x@y' }]);
  _сводкаПресета = { код: '', данные: null, ошибка: '', грузится: false, когда: 0 };
  _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 };
}"""

СОСТОЯНИЕ = """() => { const к = document.getElementById('presetChipCard'), п = к.querySelector('#pcPane-s');
  const строки = {}; if (п) п.querySelectorAll('.sv-df > div').forEach(д => { строки[(д.querySelector('.sv-kk') || {}).textContent] = (д.querySelector('.sv-vv') || {}).textContent; });
  return { вкладки: [...к.querySelectorAll('.pc-tab')].map(т => т.childNodes[0].textContent.trim()),
    выбрана: (к.querySelector('.pc-tab[aria-selected="true"]') || {}).id || '', есть: !!п, текст: п ? п.innerText.replace(/\\s+/g, ' ') : '',
    строки, точек: (_свТочки || []).length, итоги: (_свТочки || []).map(т => т.итог), подряд: (_свТочки || []).map(т => т.событий),
    линия: !!(п && п.querySelector('.sv-ch svg path.ln')), дней: п ? п.querySelectorAll('.sv-days span').length : 0,
    кто: п ? [...п.querySelectorAll('.sv-who .sv-nb')].map(э => э.childNodes[0].textContent) : [],
    крупных: п ? п.querySelectorAll('.sv-top button').length : 0, сейчас: fmt(_currentTotal).replace(/\\s+/g, ' ') }; }"""

ВЁРСТКА = """() => { const к = document.getElementById('presetChipCard'), н = [], кк = к.getBoundingClientRect();
  const пр = кк.right - parseFloat(getComputedStyle(к).borderRightWidth) - 2, лв = кк.left + 2;
  const виден = э => { const r = э.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const имя = э => (э.className && э.className.baseVal !== undefined ? э.className.baseVal : э.className) || э.tagName;
  к.querySelectorAll('.pc-tabs .pc-tab, #pcPane-s *').forEach(э => {
    if (!виден(э) || э.closest('svg') && э.tagName !== 'svg') return;
    const r = э.getBoundingClientRect();
    if (r.right > пр + .5) н.push(имя(э) + ' «' + (э.textContent || '').trim().slice(0, 30) + '» за правым краем на ' + Math.round(r.right - пр) + ' px');
    if (r.left < лв - .5) н.push(имя(э) + ' за левым краем на ' + Math.round(лв - r.left) + ' px');
  });
  к.querySelectorAll('#pcPane-s .sv-df > div').forEach(д => { const т = д.querySelector('.sv-dots'); if (т && т.getBoundingClientRect().width < 10) н.push('отточие у «' + д.querySelector('.sv-kk').textContent + '» схлопнулось'); });
  к.querySelectorAll('#pcPane-s .sv-top button').forEach(б => { if (б.getBoundingClientRect().height < 44) н.push('крупная правка ниже 44 px: ' + Math.round(б.getBoundingClientRect().height)); });
  const в = к.querySelector('#pcPane-s .sv-rd .w'); if (в && в.scrollWidth > в.clientWidth + 1 && getComputedStyle(в).textOverflow !== 'ellipsis') н.push('строка под графиком обрезана без многоточия');
  const п = к.querySelector('#pcPane-s'); if (п && п.scrollWidth > п.clientWidth + 1) н.push('панель сводки ходит вбок: ' + (п.scrollWidth - п.clientWidth) + ' px');
  return н; }"""

ЧТЕНИЕ = "() => (document.querySelector('#pcPane-s .sv-rd') || {}).innerText || ''"


def прогон(бр, порт, шир, выс, ночь):
    н = f"[{шир}{' ночь' if ночь else ''}]"
    стр, ошибки = ш.начать(бр, порт, шир, выс, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        НАХОДКИ.append(f"{н} пресету не выдан код — проверять нечего"); стр.close(); return
    стр.evaluate(ПОСЕВ, [код, [list(п) for п in ПРАВКИ], ЛИШНИХ])
    м_открыть = lambda: (стр.locator("#presetChip .pc-body").click() if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')") else None)
    м_открыть(); стр.wait_for_timeout(350)
    if not стр.locator("#pcTab-s").count():
        НАХОДКИ.append(f"{н} вкладки «Сводка» нет"); стр.close(); return
    стр.locator("#pcTab-s").click(); стр.wait_for_timeout(900)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["вкладки"] != ["Пресет", "Сводка", "Журнал", "Проверка"]:
        НАХОДКИ.append(f"{н} порядок вкладок: {с['вкладки']}")
    if "итог сейчас" not in с["текст"].lower() or с["сейчас"] not in с["текст"]:
        НАХОДКИ.append(f"{н} нет итога сейчас ({с['сейчас']}): {с['текст'][:100]}")
    правок = len(ПРАВКИ) + ЛИШНИХ
    if с["строки"].get("Правок") != str(правок):
        НАХОДКИ.append(f"{н} «Правок» {с['строки'].get('Правок')}, ждали {правок} — счёт не по всей истории")
    if с["строки"].get("Открыт") != "20 раз" or с["строки"].get("Напечатан") != "5 раз":
        НАХОДКИ.append(f"{н} открыт/напечатан: {с['строки'].get('Открыт')} / {с['строки'].get('Напечатан')}")
    if not (с["строки"].get("В работе") or "").startswith(("3 дня", "4 дня")):
        НАХОДКИ.append(f"{н} «В работе»: {с['строки'].get('В работе')}")
    if с["строки"].get("Ссылка клиенту") != "не выдавалась":
        НАХОДКИ.append(f"{н} «Ссылка клиенту»: {с['строки'].get('Ссылка клиенту')}")
    for к in ("Скидка", "Подарком", "Публикация"):
        if not с["строки"].get(к):
            НАХОДКИ.append(f"{н} в «Состоянии» нет строки «{к}»")
    if с["точек"] != ТОЧЕК or 0 in с["итоги"] or 9900000 in с["итоги"] or 9000000 in с["итоги"]:
        НАХОДКИ.append(f"{н} ступени графика: {с['итоги']} — ждали {ТОЧЕК} точек без нуля, чужого пресета и следа открытия")
    if len(с["подряд"]) > 1 and с["подряд"][1] != 3:
        НАХОДКИ.append(f"{н} три правки за две минуты не свелись в одну ступень: {с['подряд']}")
    if not с["линия"] or с["дней"] < 2:
        НАХОДКИ.append(f"{н} график не нарисован: линия {с['линия']}, подписей дней {с['дней']}")
    if sorted(с["кто"]) != sorted(["Вы", "Сергей В."]):
        НАХОДКИ.append(f"{н} «Кто правил»: {с['кто']}")
    if с["крупных"] != 3:
        НАХОДКИ.append(f"{н} крупных правок {с['крупных']}, ждали три")
    # Цена со скидкой под итогом — та же, что в полоске итога; без скидки строки нет.
    ск = стр.evaluate("""async () => { const без = !!document.querySelector('#pcPane-s .sv-disc');
      const п = document.getElementById('discountPctInput'), н = document.getElementById('cashDiscountCheck');
      п.value = '2.5'; if (н) н.checked = true; calc(); await new Promise(r => setTimeout(r, 300));
      заполнитьКарточкуЗначка(); await new Promise(r => setTimeout(r, 100));
      const э = document.querySelector('#pcPane-s .sv-disc');
      return { без, строка: э ? э.textContent.replace(/\\s+/g, ' ').trim() : '', полоска: (document.getElementById('tsDisc') || {}).textContent || '' }; }""")
    полоска = ск["полоска"].replace("\xa0", " ").strip()
    if ск["без"] or not полоска or ск["строка"] != (полоска + " за наличные").replace("\xa0", " "):
        НАХОДКИ.append(f"{н} цена со скидкой под итогом: без скидки {'есть' if ск['без'] else 'нет'}, строка «{ск['строка']}», в полоске итога «{полоска}»")
    for т in стр.evaluate(ВЁРСТКА):
        НАХОДКИ.append(f"{н} {т}")
    стр.screenshot(path=str(СНИМКИ / f"summary-{шир}{'-n' if ночь else ''}.png"))
    # Двузначное число замечаний: вкладка «Проверка» с ним не уходит за край ряда.
    за = стр.evaluate("""() => { const был = проверкаПоЧекЛисту;
      window.проверкаПоЧекЛисту = () => ({ замечания: Array.from({ length: 12 }, () => ({ раздел: 'roof', т: 'проба', стоп: false, эл: '' })), вопросы: [] });
      заполнитьКарточкуЗначка(); const к = document.getElementById('presetChipCard'), р = к.querySelector('.pc-tabs').getBoundingClientRect();
      const вк = [...к.querySelectorAll('.pc-tab')], п = вк.map(т => т.getBoundingClientRect());
      // Сжатая вкладка остаётся в ряду, но текст в ней переносится или вылезает.
      // Меряется сам текст, а не scrollWidth: невидимое поле нажатия вкладки шире её и дало бы ложную находку.
      const сжата = вк.filter(т => { const д = document.createRange(); д.selectNodeContents(т); const пр = [...д.getClientRects()].filter(x => x.width > 0);
        const в = т.getBoundingClientRect(); const верх = пр.map(x => x.top); return Math.max(...верх) - Math.min(...верх) > 8 || пр.some(x => x.right > в.right + 1 || x.left < в.left - 1); }).map(т => т.textContent.trim());
      window.проверкаПоЧекЛисту = был; заполнитьКарточкуЗначка();
      return { за: Math.round(Math.max(...п.map(x => x.right)) - р.right), зазор: Math.round(Math.min(...п.slice(1).map((x, и) => x.left - п[и].right))), сжата }; }""")
    if за["за"] > 0 or за["зазор"] < 8 or за["сжата"]:
        НАХОДКИ.append(f"{н} вкладки при 12 замечаниях: за краем на {за['за']} px, наименьший зазор {за['зазор']} px, сжаты {за['сжата']}")
    # ── график ведётся клавишами и указателем ──
    гр = стр.locator("#pcPane-s .sv-ch")
    if гр.count():
        гр.focus(); стр.keyboard.press("Home"); стр.wait_for_timeout(100)
        первое = стр.evaluate(ЧТЕНИЕ)
        стр.keyboard.press("ArrowRight"); стр.wait_for_timeout(100)
        второе = стр.evaluate(ЧТЕНИЕ)
        if "Сохранён в пресет" not in первое or "Метка-планкен" not in второе or "3 правки" in второе:
            НАХОДКИ.append(f"{н} клавиши по графику: «{первое[:60]}» → «{второе[:60]}»")
        if not стр.evaluate("() => document.activeElement && document.activeElement.classList.contains('sv-ch')"):
            НАХОДКИ.append(f"{н} стрелка увела фокус с графика — сработало переключение вкладок")
        б = гр.bounding_box()
        стр.mouse.move(б["x"] + б["width"] - 2, б["y"] + б["height"] / 2); стр.wait_for_timeout(100)
        if "последняя правка" not in стр.evaluate(ЧТЕНИЕ):
            НАХОДКИ.append(f"{н} указатель у правого края не показал последнюю правку")
        стр.mouse.move(б["x"] + 3, б["y"] + б["height"] / 2); стр.wait_for_timeout(100)
        if "Сохранён в пресет" not in стр.evaluate(ЧТЕНИЕ):
            НАХОДКИ.append(f"{н} указатель у левого края не показал сохранение")
    # ── плашка под графиком открывает свою правку в журнале ──
    # Нажатие по графику закрепляет точку: мышь, уходящая к плашке, её не сбрасывает.
    if гр.count():
        б = гр.bounding_box()
        x2 = стр.evaluate("(W) => 6 + 2 * (W - 12) / (_свТочки.length - 1)", б["width"])
        стр.mouse.click(б["x"] + x2, б["y"] + б["height"] / 2); стр.wait_for_timeout(120)
        рд = стр.locator("#pcPane-s .sv-rd")
        рб = рд.bounding_box()
        стр.mouse.move(рб["x"] + рб["width"] / 2, рб["y"] + рб["height"] / 2, steps=6); стр.wait_for_timeout(150)
        до = стр.evaluate(ЧТЕНИЕ)
        if "Метка-печь" not in до:
            НАХОДКИ.append(f"{н} точка, закреплённая нажатием, сбросилась, пока мышь шла к плашке: «{до[:60]}»")
        ид = рд.get_attribute("data-ev")
        if рб["height"] < 44:
            НАХОДКИ.append(f"{н} плашка под графиком ниже 44 px: {рб['height']:.0f}")
        рд.click(); стр.wait_for_timeout(900)
        ж = стр.evaluate("""(ид) => { const к = document.getElementById('presetChipCard'), л = к.querySelector('.pc-lg-sc');
          const с = л && [...л.querySelectorAll('li[data-ev]')].find(x => x.getAttribute('data-ev') === ид);
          const в = (к.querySelector('.pc-tab[aria-selected="true"]') || {}).id;
          if (!с) return { выбрана: в };
          const r = с.getBoundingClientRect(), рл = л.getBoundingClientRect();
          return { выбрана: в, есть: true, видна: r.top >= рл.top - 1 && r.bottom <= рл.bottom + 1, свет: с.classList.contains('pc-lg-flash'), текст: с.innerText.slice(0, 80) }; }""", ид)
        if ж.get("выбрана") != "pcTab-l" or not ж.get("есть") or not ж.get("видна") or not ж.get("свет") or "Метка-печь" not in (ж.get("текст") or ""):
            НАХОДКИ.append(f"{н} плашка под графиком не открыла свою правку в журнале: {ж}")
        стр.locator("#pcTab-s").click(); стр.wait_for_timeout(500)
    # ── крупная правка открывает себя в журнале ──
    перв = стр.locator("#pcPane-s .sv-top button").first
    if перв.count():
        ид = перв.get_attribute("data-ev")
        перв.click(); стр.wait_for_timeout(900)
        ж = стр.evaluate("""(ид) => { const к = document.getElementById('presetChipCard'), л = к.querySelector('.pc-lg-sc');
          const с = л && [...л.querySelectorAll('li[data-ev]')].find(x => x.getAttribute('data-ev') === ид);
          if (!с) return { выбрана: (к.querySelector('.pc-tab[aria-selected="true"]') || {}).id };
          const r = с.getBoundingClientRect(), рл = л.getBoundingClientRect();
          return { выбрана: (к.querySelector('.pc-tab[aria-selected="true"]') || {}).id, есть: true,
                   видна: r.top >= рл.top - 1 && r.bottom <= рл.bottom + 1, свет: с.classList.contains('pc-lg-flash') }; }""", ид)
        if ж.get("выбрана") != "pcTab-l" or not ж.get("есть") or not ж.get("видна") or not ж.get("свет"):
            НАХОДКИ.append(f"{н} переход из крупной правки в журнал: {ж}")
        т = стр.evaluate("() => (document.querySelector('#presetChipCard .pc-lg') || {}).innerText || ''")
        if "Метка-след" in т or "Метка-толщина" not in т:
            НАХОДКИ.append(f"{н} журнал: след открытия {'виден' if 'Метка-след' in т else 'скрыт'}, настоящая смена толщины {'видна' if 'Метка-толщина' in т else 'пропала'}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for шир, выс, ночь in ((1440, 900, False), (390, 844, False), (360, 740, False), (320, 640, False), (390, 844, True)):
                прогон(бр, порт, шир, выс, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: «Сводка» стоит второй вкладкой, считает правки по всей истории, сводит правки подряд в ступень, "
          "ведётся клавишами и указателем, ведёт в журнал крупную правку и правку из плашки под графиком, точка, закреплённая нажатием, не сбрасывается — и не выходит за край — на 1440, 390, 360 и 320, днём и ночью; вкладки держатся и при двузначном числе замечаний.")


if __name__ == "__main__":
    главная()
