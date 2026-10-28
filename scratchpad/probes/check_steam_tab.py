#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Технология «Парная»: расчёт по книге, правила строк и соседи без поломок.

Константин 26–27.10.2026: «Пока делаем отдельной вкладкой калькулятор парных
(как технология)… отдельная вкладка технологии никак на работу других разделов
не повлияет», и после рабочего макета steam-page-v1 — «Запускай на тестовый».

Проба держит:
  • расчёт: база 3 × 4 × 2,3 м по камню — 1 257 216 ₽, с двенадцатью опциями
    макета — 2 313 757 ₽ и разделы 1 630 643 / 539 834 / 143 280 ₽, как в книге
    «Калькулятор опций» v2.4 с ответами 26.10;
  • шкалу сборки премиальной парной: 0 опций — строки нет, 1 — 120 000 ₽,
    2 — 150 000 ₽, 5 — 240 000 ₽, строка ставится и снимается сама;
  • печи и комплектующие каталога каркаса — с его названием и ценой; вывод
    дымохода иначе — доплатой к выводу в крышу в 1 этаж; одну печь и один пол:
    вторая печь снимает первую, лиственница — плитку; подсказку по объёму;
  • панно и окно — руками с точностью до десятых, кнопками по 0,1 м²;
  • тип помещения: каркас под отделку и утепление по камню ставятся и
    снимаются сами, и база раздела меняется ровно на их цену;
  • размеры, счётчики, срок бригады вручную, «Снять базу», скидку;
  • строки как у каркаса (Константин, 27.10.2026: «Ручные/опции примечания
    не добавить. Печать неактивная. Все иконки по выделению, глаз, избранные
    должны как в каркасе работать»): подарок снимает цену с итога, выделение,
    глаз и избранное ставятся и переживают перерисовку, своя позиция идёт в
    сумму, своё примечание добавляется;
  • печать открывается без попытки сохранить пресет; на листе «Бланка» —
    помещение вместо толщины и суммы разделов парной, на других листах нет
    ни кровли, ни утепления, ни толщины;
  • то, чего у парной в этой сборке нет (платёжный план, пресет, поиск),
    отвечает словами и окна не открывает;
  • каркас и брус после парной — свои разделы, проекты и расчёт;
  • калитку: в бою пункт видит только администратор, на тесте — все;
  • вёрстку на 390 / 768 / 1440 днём и ночью: ни горизонтальной прокрутки, ни
    строки за краем, у дробного счётчика «3,75» есть поле до кнопок.

    python3 check_steam_tab.py
"""
import pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
НАХОДКИ = []
# Печь макета — Ялта 35 в камне: она стоит в строке печи по умолчанию.
МАКЕТ = ['olha', 'polkiOlha', 'podsv', 'spinki', 'parya', 'panno', 'okno', 'maslo', 'nastil', 'pech', 'talk', 'econ']

ЧИСЛА = """() => {
  const ч = ид => Number(((document.getElementById(ид) || {}).textContent || '').replace(/\\D/g, '')) || 0;
  return {
    тех: currentTech, итог: ч('totalDisplay'), спец: ч('discountDisplay'),
    разделы: ['par_st', 'par_pech', 'par_log'].map(к => ч('sec_total_' + к)),
    премиум: ч('optprice_par_premium'),
    премиумВкл: !!document.getElementById('lbl_par_premium')?.classList.contains('active'),
    строк: document.querySelectorAll('[id^="lbl_par_"]').length,
    база: парБазы(парГеом()), вкл: [...ПАР.вкл].sort(),
  };
}"""


def плохо(т):
    НАХОДКИ.append(т)


def открыть(бр, порт, ш, ночь=False):
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    if ночь:
        стр.evaluate("() => { if (!document.body.classList.contains('dark')) toggleDarkMode(); }")
    return стр, ош


# Цены печей каталога каркаса — как в базе на 27.10.2026: в заглушке базы у строк
# каркаса только названия, а парная берёт печи и комплектующие из его каталога.
ЦЕНЫ_ПЕЧЕЙ = {"st6": 97700, "st7": 114200, "st8": 123620, "st9": 141300, "st13": 13431, "st14": 45256,
              "st16": 58700, "st17": 73300, "st18": 64400, "st19": 43000, "st21": 129700, "st22": 159900,
              "st23": 156000, "st24": 192200, "st25": 76000, "st26": 24000, "st27": 15850, "st28": 32550,
              "st29": 16900, "st30": 25350, "st31": 8450, "st32": 33450, "st33": 37650, "st34": 229000}


def в_парную(стр, образец=True):
    стр.evaluate("ц => FRAME_OPTIONS.forEach(о => { if (о.id in ц) о.price = ц[о.id]; })", ЦЕНЫ_ПЕЧЕЙ)
    # Суммы проб сверены с книгой на её образце 3 × 4 × 2,3 м. С 28.10.2026
    # калькулятор начинает с 3 × 2 × 2,3 — проба подменяет начало на образец, а
    # настоящее начало держит отдельная проверка в расчёт().
    if образец:
        стр.evaluate("""() => { if (!window.__парНачало) { window.__парНачало = парНачало;
          window.парНачало = () => Object.assign(window.__парНачало(), { W: 4 }); } }""")
    стр.evaluate("""async () => { window.IS_TEST_DOMAIN = true; applySteamGate();
      selectTech('Парная'); await new Promise(r => setTimeout(r, 500)); }""")


def расчёт(бр, порт):
    стр, ош = открыть(бр, порт, 1440)
    # Калитка: в бою — только администратор, на тесте — все.
    калитка = стр.evaluate("""() => {
      const было = [window.IS_TEST_DOMAIN, window._sbProfile];
      const пункт = () => document.querySelector('#techSelectDropdown [data-tech="steam"]').style.display
        + (/>Парная</.test(рядФильтраТехнологий('my', [])) ? '' : '|без чипа');
      window.IS_TEST_DOMAIN = false; window._sbProfile = { role: 'manager' }; applySteamGate();
      const менеджер = пункт();
      window._sbProfile = { role: 'admin' }; applySteamGate();
      const админ = пункт();
      window.IS_TEST_DOMAIN = true; window._sbProfile = { role: 'manager' }; applySteamGate();
      const тест = пункт();
      [window.IS_TEST_DOMAIN, window._sbProfile] = было;
      return { менеджер, админ, тест };
    }""")
    if калитка != {"менеджер": "none|без чипа", "админ": "", "тест": ""}:
        плохо(f"калитка парной: {калитка} — ждали скрыто у менеджера в бою (и пункт, и чип «Парная» "
              "в фильтре пресетов), видно у администратора и на тесте")
    # Поле называется «Расчёт» (Константин, 27.10.2026, со снимком поля).
    подпись = стр.evaluate("() => document.querySelector('#techSelectWrap').parentElement.querySelector('label').textContent.trim()")
    if подпись != "Расчёт":
        плохо(f"поле выбора расчёта подписано «{подпись}», а должно «Расчёт»")

    в_парную(стр)
    # Настоящее начало парной — 3 × 2 × 2,3 м (Константин, 28.10.2026: «В парной
    # по умолчанию такие размеры парной ставь, когда Сбросить все нажимаю»).
    начало = стр.evaluate("() => { const н = window.__парНачало(); return [н.L, н.W, н.H, н.вкл.size]; }")
    if начало != [3, 2, 2.3, 0]:
        плохо(f"начало парной {начало} — ждали 3 × 2 × 2,3 м без опций")
    ч = стр.evaluate(ЧИСЛА)
    # 39 своих строк (печь — одна строка) и 13 из каталога каркаса: 4 портала,
    # 3 дымохода, 3 вывода иначе, 3 кассеты и пароиспаритель.
    if ч["тех"] != "steam" or ч["строк"] != 52:
        плохо(f"после выбора «Парная»: технология {ч['тех']}, строк парной {ч['строк']} — ждали 52")
        стр.close()
        return ош
    if ч["итог"] != 1257216:
        плохо(f"база парной 3 × 4 × 2,3 м по камню: {ч['итог']} ₽, ждали 1 257 216 ₽")
    заголовки = стр.evaluate("""() => [document.getElementById('techTitle').textContent,
      document.getElementById('projectCardTitle').textContent, document.getElementById('techSelectLabel').textContent,
      getComputedStyle(document.getElementById('projectSelectWrap')).display === 'none' || !document.getElementById('projectSelectWrap').offsetParent,
      !!document.getElementById('steamRoomWrap').offsetParent]""")
    рядом = стр.evaluate("""() => { const п = document.querySelector('#techField > label').getBoundingClientRect();
      const т = document.getElementById('techSelectTrigger'), тр = т.getBoundingClientRect();
      const р = document.createRange(); р.selectNodeContents(document.getElementById('techSelectLabel'));
      return [Math.round(тр.left - п.right), Math.round(р.getBoundingClientRect().left - тр.left), document.body.classList.contains('ui-blank')]; }""")
    # Константин, 27.10.2026, снимком: «Тут поставь ближе к полю выбора. Для кого это расстояние».
    if рядом[2] and (рядом[0] > 20 or рядом[1] > 4):
        плохо(f"поле «Расчёт»: от подписи до поля {рядом[0]} px, текст от края линии {рядом[1]} px")
    # Карточка — «Параметры парной» (Константин, 27.10.2026, снимком карточки).
    if заголовки != ["Парное отделение", "Параметры парной", "Парная", True, True]:
        плохо(f"шапка и карточка парной: {заголовки}")

    стр.evaluate("ид => ид.forEach(к => document.getElementById('lbl_par_' + к).click())", МАКЕТ)
    ч = стр.evaluate(ЧИСЛА)
    if ч["итог"] != 2313757 or ч["разделы"] != [1630643, 539834, 143280]:
        плохо(f"двенадцать опций макета: итог {ч['итог']}, разделы {ч['разделы']} — ждали 2 313 757 и 1 630 643 / 539 834 / 143 280")
    if ч["премиум"] != 210000 or not ч["премиумВкл"]:
        плохо(f"сборка премиальной при четырёх опциях: {ч['премиум']} ₽, отмечена {ч['премиумВкл']} — ждали 210 000 ₽")

    # Шкала: снимаем всё и добавляем премиальные по одной.
    стр.evaluate("() => { resetCheckedOptions(); }")
    ч = стр.evaluate(ЧИСЛА)
    if ч["вкл"] or ч["премиумВкл"] or ч["итог"] != 1257216:
        плохо(f"«Сбросить выбор опций»: отмечено {ч['вкл']}, итог {ч['итог']}")
    ждём = {1: 120000, 2: 150000, 3: 180000, 4: 210000, 5: 240000}
    for n, к in enumerate(['podsv', 'parya', 'panno', 'okno', 'zvezd'], 1):
        стр.evaluate("к => document.getElementById('lbl_par_' + к).click()", к)
        ч = стр.evaluate(ЧИСЛА)
        if ч["премиум"] != ждём[n] or not ч["премиумВкл"]:
            плохо(f"шкала сборки: {n} опц. — {ч['премиум']} ₽ (отмечена {ч['премиумВкл']}), ждали {ждём[n]}")
    стр.evaluate("() => document.getElementById('lbl_par_premium').click()")
    if not стр.evaluate(ЧИСЛА)["премиумВкл"]:
        плохо("сборку премиальной снимает нажатие — она должна держаться шкалой")
    стр.evaluate("() => { resetCheckedOptions(); }")

    # Печи — каталогом книги (лист «Печи»), выбором в карточке помещения
    # (Константин, 27.10.2026: «И где выбор печей? Там в таблице их много было»).
    в = стр.evaluate("""() => {
      const опции = [...document.querySelectorAll('#steamStoveDropdown .custom-select-option')];
      return { всего: опции.length, первая: опции[0] && опции[0].dataset.stove,
               ряд: (document.querySelector('#steamStoveDropdown .cs-sortrow .cs-sortcap, #steamStoveDropdown .cs-sortrow .custom-select-deselect') || {}).textContent?.trim(),
               группы: [...document.querySelectorAll('#steamStoveDropdown .cso-group')].map(г => г.textContent.trim()),
               подходят: опции.filter(о => о.querySelector('.cso-fit')).map(о => о.dataset.stove),
               ярлык: document.getElementById('steamStoveLabel').textContent };
    }""")
    # «Без печи» отдельной строкой нет: снять выбор — в строке порядка, как у
    # проектов (Константин, 27.10.2026: «Снять выбор с печи сделай также напротив
    # иконок сортировки, как в технологиях»); пока печь не выбрана — подпись.
    if в["всего"] != 47 or в["первая"] != "feringer-uyut-18-topka-vnutri-parnoy" or в["ряд"] != "Порядок списка":
        плохо(f"список печей: {в['всего']} пунктов, первый «{в['первая']}», строка порядка «{в['ряд']}» — ждали 47 моделей книги без «Без печи» и подпись «Порядок списка»")
    if в["группы"] != ["Ферингер", "ИзиСтим", "ГРОМ", "Другие", "Монтаж печи заказчика"]:
        плохо(f"группы списка печей: {в['группы']}")
    if в["ярлык"] != "Без печи" or "grom-40-p2-pech-komplekt" not in в["подходят"] or "izistim-yalta-35-v-kamne" in в["подходят"] or "feringer-malyutka" in в["подходят"]:
        плохо(f"поле «Печь» до выбора: «{в['ярлык']}», подходят к 35,9 м³ (парная 27,6 м³ + 30 %): {в['подходят'][:6]}…")

    # Переключатель «Подходят к парной» и строка «Порядок списка» (Константин,
    # 27.10.2026: «нужен фильтр по „Подходит“ (как в каркасе фильтр по
    # комплектациям)… добавь порядок списка иконками, как в других расчётах»).
    СПИСОК = """() => { const д = document.getElementById('steamStoveDropdown');
      const ид = [...д.querySelectorAll('.custom-select-option[data-stove]')].map(о => о.dataset.stove).filter(х => х && х !== 'pech-zakazchika');
      const м = ид.map(х => ПАР_ПЕЧИ.find(п => п.id === х));
      const г = парГеом();
      return { ид, цены: м.map(парЦенаМодели), от: м.map(п => п.от), подходят: м.map(п => г.печь >= п.от && г.печь <= п.до),
        все: ПАР_ПЕЧИ.filter(п => п.id !== 'pech-zakazchika' && г.печь >= п.от && г.печь <= п.до).length,
        группы: [...д.querySelectorAll('.cso-group')].map(х => х.textContent.trim()),
        крайние: [д.querySelector('.custom-select-option[data-stove]')?.dataset.stove, [...д.querySelectorAll('.custom-select-option[data-stove]')].pop()?.dataset.stove],
        вкл: !!д.querySelector('.kit-ready-toggle .krt-switch.on'), надпись: (д.querySelector('.krt-label')?.textContent || '').replace(/\\u00a0/g, ' '),
        пусто: д.querySelector('.cso-empty')?.textContent.trim() || '', открыт: document.getElementById('steamStoveWrap').classList.contains('open'),
        значки: [...д.querySelectorAll('.cs-sbtn')].map(б => б.dataset.sort + (б.classList.contains('on') ? '*' : '') + (б.classList.contains('desc') ? 'v' : '')),
        подпись: д.querySelector('.cs-sortname.show')?.textContent || '' }; }"""
    стр.evaluate("() => { appSettings.stoveSort = 'default'; appSettings.stoveSortDesc = false; парнаяПечьОткрыть(); }")
    с = стр.evaluate(СПИСОК)
    if с["значки"] != ["volume", "price", "default*"] or с["надпись"] != "Подходят к парной · 35,9 м³" or с["вкл"]:
        плохо(f"шапка списка печей: значки {с['значки']}, переключатель «{с['надпись']}» включён {с['вкл']}")
    стр.evaluate("() => document.querySelector('#steamStoveDropdown .kit-ready-toggle').click()")
    с = стр.evaluate(СПИСОК)
    if not (с["вкл"] and с["открыт"] and all(с["подходят"]) and len(с["ид"]) == с["все"] > 0 and с["крайние"][1] == "pech-zakazchika" and с["крайние"][0] != ""):
        плохо(f"«Подходят к парной»: включён {с['вкл']}, список открыт {с['открыт']}, моделей {len(с['ид'])} из {с['все']} подходящих, "
              f"все подходят {all(с['подходят'])}, первый и последний пункт {с['крайние']}")
    # Ни одна печь не рассчитана на 108 м³ + 30 % = 140,4 м³ — список говорит об этом словами.
    стр.evaluate("() => { window._размеры = [ПАР.L, ПАР.W, ПАР.H]; ПАР.L = 6; ПАР.W = 6; ПАР.H = 3; calc(); }")
    с = стр.evaluate(СПИСОК)
    if с["ид"] or с["пусто"] != "Нет печей на 140,4 м³":
        плохо(f"«Подходят к парной» при 108 м³: моделей {len(с['ид'])}, пустое состояние «{с['пусто']}»")
    стр.evaluate("() => { [ПАР.L, ПАР.W, ПАР.H] = window._размеры; calc(); document.querySelector('#steamStoveDropdown .kit-ready-toggle').click(); }")
    if len(стр.evaluate(СПИСОК)["ид"]) != 46:
        плохо("переключатель «Подходят к парной» не вернул весь список")
    # Порядки: по цене, по объёму, повторное нажатие разворачивает.
    for код, ключ, подпись, вниз in (("price", "цены", "Сначала дешевле", False), ("price", "цены", "Сначала дороже", True),
                                    ("volume", "от", "По объёму: с маленьких парных", False)):
        стр.evaluate("к => document.querySelector('#steamStoveDropdown .cs-sbtn[data-sort=\"' + к + '\"]').click()", код)
        с = стр.evaluate(СПИСОК)
        ряд = с[ключ]
        верно = ряд == sorted(ряд, reverse=вниз)
        if not верно or с["группы"] != ["Монтаж печи заказчика"] or not с["открыт"] or с["подпись"] != подпись or len(с["ид"]) != 46:
            плохо(f"порядок «{подпись}»: по порядку {верно}, группы {с['группы']}, список открыт {с['открыт']}, подпись «{с['подпись']}», моделей {len(с['ид'])}")
    if стр.evaluate("() => [appSettings.stoveSort, appSettings.stoveSortDesc]") != ["volume", False]:
        плохо("порядок печей не записан в настройки аккаунта")
    стр.evaluate("() => document.querySelector('#steamStoveDropdown .cs-sbtn[data-sort=\"default\"]').click()")
    с = стр.evaluate(СПИСОК)
    if с["группы"] != ["Ферингер", "ИзиСтим", "ГРОМ", "Другие", "Монтаж печи заказчика"] or с["значки"] != ["volume", "price", "default*"]:
        плохо(f"«Как в книге» не вернул группы: {с['группы']}, значки {с['значки']}")
    # Поиск — первой строкой раскрытого списка (вариант Б макета stove-search-v1,
    # Константин, 27.10.2026: «Этот вариант давай»): по словам, в другой
    # раскладке, с подсветкой; поле не теряет курсор при наборе; Enter берёт
    # первую найденную, Escape закрывает; новое открытие — с пустым поиском.
    ПОИСК = """() => { const д = document.getElementById('steamStoveDropdown'), п = document.getElementById('steamStoveSearch');
      const о = [...д.querySelectorAll('.cso-body .custom-select-option[data-stove]')];
      return { есть: !!п, значение: п ? п.value : null, фокус: document.activeElement === п,
        имена: о.map(х => х.querySelector('.cso-name').firstChild ? х.querySelector('.cso-name').childNodes : []).length,
        ид: о.map(х => х.dataset.stove), названия: о.map(х => ПАР_ПЕЧИ.find(м => м.id === х.dataset.stove).имя.toLowerCase()),
        метки: д.querySelectorAll('.cso-body mark.cso-hit').length,
        пусто: д.querySelector('.cso-empty')?.textContent.trim() || '', открыт: document.getElementById('steamStoveWrap').classList.contains('open') }; }"""
    с = стр.evaluate(ПОИСК)
    if not (с["есть"] and с["значение"] == "" and с["фокус"]):
        плохо(f"поиск печи при открытии: поле есть {с['есть']}, значение «{с['значение']}», курсор в нём {с['фокус']}")
    стр.fill('#steamStoveSearch', 'ялта')
    с = стр.evaluate(ПОИСК)
    ялта = с["ид"]
    if not (ялта and all('ялта' in н for н in с["названия"]) and с["метки"] == len(ялта) and с["фокус"] and с["значение"] == "ялта" and с["открыт"]):
        плохо(f"поиск «ялта»: найдено {len(ялта)}, все с «ялта» {all('ялта' in н for н in с['названия'])}, подсветок {с['метки']}, курсор {с['фокус']}, список открыт {с['открыт']}")
    стр.fill('#steamStoveSearch', 'zknf')
    if стр.evaluate(ПОИСК)["ид"] != ялта:
        плохо("поиск в другой раскладке: «zknf» нашёл не то же, что «ялта»")
    стр.fill('#steamStoveSearch', 'гром 40')
    с = стр.evaluate(ПОИСК)
    if not (с["ид"] and all('гром' in н and '40' in н for н in с["названия"])):
        плохо(f"поиск «гром 40»: {с['названия'][:4]}")
    первая = с["ид"][0] if с["ид"] else None
    стр.fill('#steamStoveSearch', 'щщщ')
    с = стр.evaluate(ПОИСК)
    if с["ид"] or с["пусто"] != "Ничего не нашлось по «щщщ»":
        плохо(f"поиск без находок: {len(с['ид'])} печей, пустое состояние «{с['пусто']}»")
    # Строки поиска и порядка стоят на месте, пока список прокручивается.
    стр.fill('#steamStoveSearch', '')
    в = стр.evaluate("""() => { const д = document.getElementById('steamStoveDropdown'); д.scrollTop = д.scrollHeight;
      const р = д.getBoundingClientRect(), п = д.querySelector('.cso-search').getBoundingClientRect(), с = д.querySelector('.cs-sortrow').getBoundingClientRect();
      return [Math.round(п.top - р.top), Math.round(с.top - п.bottom), д.scrollTop > 100]; }""")
    if not (в[2] and abs(в[0]) <= 2 and abs(в[1]) <= 2):
        плохо(f"прокрученный список печей: строка поиска от верха {в[0]} px, строка порядка от поиска {в[1]} px, прокручен {в[2]}")
    стр.fill('#steamStoveSearch', 'гром 40')
    стр.press('#steamStoveSearch', 'Enter')
    в = стр.evaluate("() => [ПАР.печь, ПАР.вкл.has('pech'), document.getElementById('steamStoveWrap').classList.contains('open')]")
    if в != [первая, True, False]:
        плохо(f"Enter в поиске: печь {в[0]} (ждали первую найденную {первая}), отмечена {в[1]}, список открыт {в[2]}")
    стр.evaluate("() => парнаяПечьОткрыть()")
    с = стр.evaluate(ПОИСК)
    снять = стр.evaluate("() => (document.querySelector('#steamStoveDropdown .cs-sortrow .custom-select-deselect') || {}).textContent?.trim()")
    if с["значение"] != "" or len(с["ид"]) != 47 or снять != "Снять выбор":
        плохо(f"повторное открытие: поиск «{с['значение']}», пунктов {len(с['ид'])}, строка порядка «{снять}» — ждали пустой поиск, весь список и «Снять выбор»")
    стр.press('#steamStoveSearch', 'Escape')
    if стр.evaluate("() => document.getElementById('steamStoveWrap').classList.contains('open')"):
        плохо("Escape в поиске печи не закрыл список")
    стр.evaluate("() => document.body.click()")
    # Цены книги: цена с сайта × наценка, до рубля.
    for ид, цена, камни in (("izistim-yalta-35-v-kamne", 208425, 80), ("grom-40-p2-pech-komplekt", 249690, 120),
                            ("feringer-optima", 64400, 80), ("grom-50-p2-uragan", 359415, 180)):
        стр.evaluate("ид => { document.getElementById('steamStoveTrigger').click(); document.querySelector('#steamStoveDropdown [data-stove=\"' + ид + '\"]').click(); }", ид)
        в = стр.evaluate("""() => [Number(document.getElementById('optprice_par_pech').textContent.replace(/\\D/g, '')), ПАР.kamni,
          document.getElementById('lbl_par_pech').classList.contains('active'), document.getElementById('name_par_pech').textContent,
          document.getElementById('steamStoveWrap').classList.contains('open'), document.getElementById('steamStoveLabel').textContent]""")
        if в[0] != цена or в[1] != камни or not в[2] or в[4]:
            плохо(f"печь {ид}: цена {в[0]} (книга {цена}), камни {в[1]} (книга {камни}), строка отмечена {в[2]}, список открыт {в[4]}")
        if not в[3].startswith("Печь — ") or в[3][7:] != в[5]:
            плохо(f"печь {ид}: строка «{в[3]}», поле «{в[5]}»")
    # «Снять выбор» в строке порядка снимает строку печи, нажатие по строке возвращает последнюю модель.
    стр.evaluate("() => { document.getElementById('steamStoveTrigger').click(); document.querySelector('#steamStoveDropdown .cs-sortrow .custom-select-deselect').click(); }")
    if стр.evaluate("() => [ПАР.вкл.has('pech'), document.getElementById('steamStoveLabel').textContent]") != [False, "Без печи"]:
        плохо("«Снять выбор» не сняло строку печи")
    стр.evaluate("() => document.getElementById('lbl_par_pech').click()")
    if стр.evaluate("() => [ПАР.вкл.has('pech'), ПАР.печь]") != [True, "grom-50-p2-uragan"]:
        плохо("нажатие по строке печи не вернуло последнюю модель")
    # «Выбрать» у строки раскрывает список в карточке.
    стр.evaluate("() => document.querySelector('#lbl_par_pech .par-pick').click()")
    if not стр.evaluate("() => document.getElementById('steamStoveWrap').classList.contains('open')"):
        плохо("«Выбрать» у строки печи не раскрыл список печей")
    стр.evaluate("() => { document.body.click(); ПАР.печь = 'izistim-yalta-35-v-kamne'; ПАР.kamni = 80; resetCheckedOptions(); }")
    # Другой вывод дымохода — доплатой к выводу в крышу в 1 этаж, один из трёх.
    if стр.evaluate("() => Number(document.getElementById('optprice_par_st7').textContent.replace(/\\D/g, ''))") != 114200 - 97700:
        плохо("вывод дымохода в 2 этажа — не доплата к выводу в 1 этаж (16 500 ₽)")
    # С 28.10.2026 исключения — как у каркаса: вторая позиция группы закрыта
    # замком и на нажатие объясняет, кто её закрыл (Константин: «Добавь
    # автоматизацию в парную… когда пол и пол, то есть смысла исключения поставить»).
    ЗАМОК = """к => { const л = document.getElementById('lbl_par_' + к);
      return { закрыта: л.dataset.blocked === '1', замок: !!л.querySelector('.excl-lock'), кто: л.dataset.blockedBy, текст: л.dataset.blockedText }; }"""
    стр.evaluate("() => ['st7', 'st8'].forEach(к => document.getElementById('lbl_par_' + к).click())")
    стр.wait_for_timeout(800)
    з = стр.evaluate(ЗАМОК, "st8")
    if стр.evaluate(ЧИСЛА)["вкл"] != ["st7"] or not з["закрыта"] or not з["замок"] or з["кто"] != "par_st7" or "вывод дымохода один" not in з["текст"]:
        плохо(f"выводы дымохода: отмечено {стр.evaluate(ЧИСЛА)['вкл']}, второй — {з}; ждали первый отмеченным, второй под замком")
    if not стр.evaluate("() => { const т = document.getElementById('exclTooltip'); return !!т && т.style.display !== 'none' && /Недоступно/.test(т.textContent); }"):
        плохо("нажатие по закрытому выводу дымохода не показало, кто его закрыл")
    стр.evaluate("() => { resetCheckedOptions(); }")
    if стр.evaluate(ЗАМОК, "st8")["закрыта"]:
        плохо("после сброса вывод дымохода остался под замком")
    # Один пол; подсказка печи по объёму.
    стр.evaluate("() => ['pech', 'polList', 'plitka'].forEach(к => document.getElementById('lbl_par_' + к).click())")
    if стр.evaluate(ЧИСЛА)["вкл"] != ["pech", "polList"] or not стр.evaluate(ЗАМОК, "plitka")["закрыта"]:
        плохо(f"печь и пол: отмечено {стр.evaluate(ЧИСЛА)['вкл']} — ждали печь и лиственницу, плитку под замком")
    # Портал один, дымоход один, экономайзер один.
    стр.evaluate("() => ['talk', 'st14', 'st26', 'st27', 'econ'].forEach(к => document.getElementById('lbl_par_' + к).click())")
    вкл = стр.evaluate(ЧИСЛА)["вкл"]
    if not {"talk", "st26", "econ"} <= set(вкл) or {"st14", "st27"} & set(вкл) or not all(стр.evaluate(ЗАМОК, к)["закрыта"] for к in ("st14", "st13", "st32", "st27", "st28")):
        плохо(f"портал, дымоход и экономайзер: отмечено {вкл}")
    стр.evaluate("() => ['talk', 'st26', 'econ'].forEach(к => ПАР.вкл.delete(к))")
    # Ферингер: печь ставит три кассеты и пароиспаритель, печь другой марки их снимает и закрывает.
    стр.evaluate("() => парнаяПечь('feringer-malyutka')")
    if not {"st30", "st31"} <= set(стр.evaluate(ЧИСЛА)["вкл"]) or not стр.evaluate(ЗАМОК, "st29")["закрыта"]:
        плохо(f"печь Ферингер не поставила кассеты и пароиспаритель: {стр.evaluate(ЧИСЛА)['вкл']}")
    стр.evaluate("() => парнаяПечь('grom-40-p2-pech-komplekt')")
    вкл = стр.evaluate(ЧИСЛА)["вкл"]
    з = стр.evaluate(ЗАМОК, "st31")
    if {"st30", "st31"} & set(вкл) or not з["закрыта"] or з["кто"] != "par_pech" or "только к печи ферингер" not in з["текст"].lower():
        плохо(f"печь ГРОМ после Ферингера: отмечено {вкл}, пароиспаритель {з}")
    стр.evaluate("() => { ПАР.вкл.delete('polList'); ПАР.печь = 'izistim-yalta-35-v-kamne'; calc(); }")
    # Печь подбирается на объём парной + 30 % (Анатолий, 27.10.2026: «Запас 30%
    # по печи»): 27,6 м³ → 35,9 м³ — это в 25–35 м³ ГРОМ 40; Малютке (8–18 м³) и
    # Ялте 35 самой книги (25–35 м³) такая парная велика: обе «мала».
    ПОЧЕМУ = "() => document.getElementById('why_par_pech').textContent"
    почему = []
    for ид in ('grom-40-p2-pech-komplekt', 'feringer-malyutka', 'izistim-yalta-35-v-kamne'):
        стр.evaluate("ид => парнаяПечь(ид)", ид)
        почему.append(стр.evaluate(ПОЧЕМУ))
    if почему != ["подходит: нужна на 35,9 м³", "мала: нужна на 35,9 м³", "мала: нужна на 35,9 м³"]:
        плохо(f"подсказка печи по объёму: {почему} — ждали ГРОМ 40 «подходит», Малютку и Ялту 35 «мала» на 35,9 м³")
    стр.evaluate("() => { ПАР.L = 4; calc(); }")
    почему = стр.evaluate("() => [document.getElementById('why_par_pech').textContent, document.getElementById('why_par_pech').classList.contains('warn')]")
    if почему != ["мала: нужна на 47,8 м³", True]:
        плохо(f"печь для парной 36,8 м³: {почему} — ждали «мала: нужна на 47,8 м³» с тревогой")
    # Маленькой парной 30 % меньше 5 м³ — запас 5 м³ (чек-лист П-ПС-8-1;
    # Константин, 27.10.2026: «одно правило везде… с запасом не меньше 5 м³»):
    # 2 × 2 × 2 м = 8 м³ → 13 м³, а не 10,4.
    стр.evaluate("() => { ПАР.L = 2; ПАР.W = 2; ПАР.H = 2; calc(); }")
    if стр.evaluate("() => парГеом().печь") != 13:
        плохо(f"парная 8 м³: объём для печи {стр.evaluate('() => парГеом().печь')} — ждали 13 м³ (запас не меньше 5 м³)")
    стр.evaluate("() => { ПАР.L = 3; ПАР.W = 4; ПАР.H = 2.3; resetCheckedOptions(); }")
    # Панорамное окно («каждый метр квадратный +4 куба, с округлением в большую
    # сторону»): у Ялты 40 (28–40 м³) окно 1 м² → 39,9 м³ — ещё подходит;
    # 1,1 м² считается за 2 м² → 43,9 м³ — мала; снятое окно объём не прибавляет.
    ОКНО = """() => [document.getElementById('why_par_pech').textContent, парГеом().печь,
      [...document.querySelectorAll('#steamInfo .info-chip')].map(ч => (ч.querySelector('.ic-k') || {}).textContent + ' ' + (ч.querySelector('strong') || {}).textContent).find(т => т.startsWith('Объём для печи'))]"""
    стр.evaluate("() => { парнаяПечь('izistim-yalta-40-2024-aisi-430'); ПАР.okno = 1; document.getElementById('lbl_par_okno').click(); }")
    о1 = стр.evaluate(ОКНО)
    стр.evaluate("() => { ПАР.okno = 1.1; calc(); }")
    о2 = стр.evaluate(ОКНО)
    стр.evaluate("() => document.getElementById('lbl_par_okno').click()")
    о3 = стр.evaluate(ОКНО)
    if (о1, о2, о3) != (["подходит: нужна на 39,9 м³", 39.9, "Объём для печи 39,9 м³"], ["мала: нужна на 43,9 м³", 43.9, "Объём для печи 43,9 м³"],
                        ["подходит: нужна на 35,9 м³", 35.9, "Объём для печи 35,9 м³"]):
        плохо(f"окно и объём для печи: окно 1 м² {о1}, 1,1 м² {о2}, снято {о3} — ждали 39,9 / 43,9 / 35,9 м³")
    стр.evaluate("() => парнаяПечь('izistim-yalta-35-v-kamne')")
    стр.evaluate("() => { ПАР.okno = 1; resetCheckedOptions(); }")

    # Тип помещения.
    база0 = стр.evaluate(ЧИСЛА)["база"]["par_st"]
    for тип, каркас, утепл, разница in (("frame", False, False, (3041.66 + 2108.85) * 44.2),
                                         ("log", True, False, 2108.85 * 44.2),
                                         ("stone", True, True, 0)):
        стр.evaluate("т => { document.getElementById('steamRoomTrigger').click(); document.querySelector('#steamRoomDropdown [data-room=\"' + т + '\"]').click(); }", тип)
        в = стр.evaluate("""() => [document.getElementById('lbl_par_karkas').classList.contains('active'),
          document.getElementById('lbl_par_utepl').classList.contains('active'), парБазы(парГеом()).par_st,
          document.getElementById('steamRoomLabel').textContent, document.getElementById('steamRoomWrap').classList.contains('open')]""")
        if (в[0], в[1]) != (каркас, утепл):
            плохо(f"тип «{тип}»: каркас {в[0]}, утепление {в[1]} — ждали {каркас}, {утепл}")
        if abs((база0 - в[2]) - разница) > 0.01:
            плохо(f"тип «{тип}»: база раздела меньше на {база0 - в[2]:.2f}, ждали {разница:.2f}")
        if в[4]:
            плохо(f"тип «{тип}»: список типов остался открытым")

    # Размеры, счётчики, бригада.
    стр.evaluate("() => { const и = document.getElementById('pardim_L'); и.focus(); и.value = '3,6'; и.dispatchEvent(new Event('input')); и.blur(); }")
    # Поля размеров — в карточке помещения, а не в строке раздела
    # (Константин, 27.10.2026, снимками: «вот это перенеси, вот тут чтобы задавать»).
    в = стр.evaluate("""() => [ПАР.L, document.getElementById('name_par_dims').textContent,
      document.getElementById('pardim_L').value, (document.querySelector('#steamInfo .info-chip strong') || {}).textContent,
      !!document.getElementById('pardim_L').closest('#steamRoomCard'), !!document.querySelector('#lbl_par_dims input:not([type=checkbox])')]""")
    if в[0] != 3.6 or "3,6 × 4 × 2,3 м" not in в[1] or в[2] != "3,6" or в[3] != "33,12 м³":
        плохо(f"длина 3,6 м: {в[:4]} — ждали объём 33,12 м³ первым в карточке")
    if not в[4] or в[5]:
        плохо(f"поля размеров: в карточке помещения {в[4]}, в строке раздела {в[5]}")
    стр.evaluate("() => { const и = document.getElementById('pardim_L'); и.focus(); и.value = '0,2'; и.dispatchEvent(new Event('input')); и.blur(); }")
    if стр.evaluate("() => [ПАР.L, document.getElementById('pardim_L').value]") != [3.6, "3,6"]:
        плохо("неверная длина 0,2 м не вернулась к последней верной")
    стр.evaluate("() => { const и = document.getElementById('pardim_L'); и.value = '3'; и.dispatchEvent(new Event('input')); и.blur(); }")
    стр.evaluate("() => document.querySelector('#lbl_par_polki .opt-qty-btn:last-child').click()")
    if стр.evaluate("() => [ПАР.polki, document.getElementById('qtyval_par_polki').value]") != [4, "4"]:
        плохо(f"счётчик полков +0,25: {стр.evaluate('() => ПАР.polki')}")
    стр.evaluate("() => document.querySelector('#lbl_par_polki .opt-qty-btn').click()")
    дни = стр.evaluate("() => [парДниАвто(парГеом()), document.getElementById('qtyval_par_brig').value]")
    # ⌈44,2 / 3,5 + 3,75 / 1,5 + 4⌉ = ⌈19,13⌉ = 20 — те же 20 дней дают 143 280 ₽ логистики книги.
    if дни != [20, "20"]:
        плохо(f"срок бригады по расчёту: {дни} — ждали 20 дней")
    стр.evaluate("() => document.querySelector('#lbl_par_brig .opt-qty-btn:last-child').click()")
    if стр.evaluate("() => [ПАР.brig, document.getElementById('calc_par_brig').textContent.startsWith('срок вписан вручную')]") != [21, True]:
        плохо("срок бригады вручную: счётчик или подпись не поменялись")

    # Панно и окно — руками с точностью до десятых (пересылкой 27.10.2026:
    # «Базово 1 м2, но в ручную менять с точностью до десятых»).
    стр.fill('#qtyval_par_panno', '1,23')
    стр.press('#qtyval_par_panno', 'Enter')
    в = стр.evaluate("""() => [ПАР.panno, document.getElementById('qtyval_par_panno').value,
      Number(document.getElementById('optprice_par_panno').textContent.replace(/\\D/g, '')),
      Math.round((1.2 * 35000 + 15000) / 0.7 * ПАР_К)]""")
    if в[0] != 1.2 or в[1] != "1,2" or в[2] != в[3]:
        плохо(f"панно 1,23 м² руками: {в} — ждали 1,2 м² и цену от площади")
    стр.click('#lbl_par_okno .opt-qty-btn:last-child')
    if стр.evaluate("() => [ПАР.okno, document.getElementById('qtyval_par_okno').value]") != [1.1, "1,1"]:
        плохо("окно: кнопка «+» не прибавила 0,1 м²")
    стр.fill('#qtyval_par_okno', 'abc')
    стр.press('#qtyval_par_okno', 'Enter')
    if стр.evaluate("() => [ПАР.okno, document.getElementById('qtyval_par_okno').value]") != [1.1, "1,1"]:
        плохо("окно: неверный ввод не вернулся к прежнему")
    стр.evaluate("() => { ПАР.panno = 1; ПАР.okno = 1; calc(); }")

    # Снять базу раздела.
    до = стр.evaluate(ЧИСЛА)
    стр.evaluate("() => document.getElementById('sec_base_par_log').click()")
    после = стр.evaluate(ЧИСЛА)
    кн = стр.evaluate("() => document.getElementById('sec_base_par_log').textContent")
    if после["итог"] != до["итог"] - round(до["база"]["par_log"]) and abs(после["итог"] - (до["итог"] - до["база"]["par_log"])) > 1:
        плохо(f"«Снять базу» логистики: итог {после['итог']}, ждали {до['итог']} − {до['база']['par_log']:.0f}")
    if кн != "Добавить базу" or стр.evaluate("() => document.getElementById('lbl_par_dost').classList.contains('active')"):
        плохо(f"после «Снять базу»: кнопка «{кн}», строки базы остались отмеченными")
    стр.evaluate("() => document.getElementById('sec_base_par_log').click()")

    # Скидка.
    стр.evaluate("() => { const п = document.getElementById('discountPctInput'); п.value = 10; п.dispatchEvent(new Event('input')); }")
    ч = стр.evaluate(ЧИСЛА)
    if abs(ч["спец"] - round(ч["итог"] * 0.9)) > 1:
        плохо(f"скидка 10 %: спец. цена {ч['спец']} при итоге {ч['итог']}")
    стр.evaluate("() => { const п = document.getElementById('discountPctInput'); п.value = 0; п.dispatchEvent(new Event('input')); }")

    # Боковая панель — разделы парной; «Сбросить всё» — расчёт парной заново.
    панель = стр.evaluate("""() => [...document.querySelectorAll('#sideNavInner .nav-section .sn-nm')].map(э => э.textContent)""")
    if панель != ["Парное отделение", "Печь и комплектующие", "Дополнительные опции"]:
        плохо(f"боковая панель у парной: {панель}")
    стр.evaluate("() => { ПАР.L = 4; ПАР.комн = 'log'; ПАР.вкл.add('olha'); calc(); resetEverything(); }")
    в = стр.evaluate("() => [ПАР.L, ПАР.комн, [...ПАР.вкл], Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, '')), currentTech]")
    if в != [3, "stone", [], 1257216, "steam"]:
        плохо(f"«Сбросить всё» у парной: {в} — ждали 3 м, камень, без опций, 1 257 216 ₽")

    # Строки как у каркаса: подарок, выделение, глаз, избранное, свои позиции и примечания.
    стр.evaluate("ид => ид.forEach(к => document.getElementById('lbl_par_' + к).click())", МАКЕТ)
    итог = "() => Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, ''))"
    до = стр.evaluate(итог)
    стр.click('#gift_par_spinki', force=True)
    в = стр.evaluate("() => [giftedOpts.has('par_spinki'), !!document.querySelector('#lbl_par_spinki .opt-gift-badge'),"
                     " document.getElementById('optprice_par_spinki').classList.contains('gifted')]")
    if стр.evaluate(итог) != до - 14169 or в != [True, True, True]:
        плохо(f"подарок у спинок: итог {стр.evaluate(итог)} при {до}, отметки {в} — ждали минус 14 169 ₽ и знак «В подарок»")
    for к in ('hl', 'eye', 'star'):
        стр.click(f'#{к}_par_okno', force=True)
    в = стр.evaluate("() => [highlightedOpts.has('par_okno'), printPriceVisible.has('par_okno'), starredOpts.has('par_okno'), ПАР.вкл.has('okno')]")
    if в != [True, True, True, True]:
        плохо(f"выделение, глаз и избранное у окна: {в} — и строка не должна сниматься нажатием по кнопкам")
    стр.click('#addBtn_par_st')
    стр.fill('#addName_par_st', 'Полка-лежак из кедра')
    стр.fill('#addPrice_par_st', '45000')
    стр.click('#addForm_par_st .btn-confirm-add')
    стр.click('#addNoteBtn_par_pech')
    стр.fill('#noteText_par_pech', 'Дымоход до 6 м входит в расчёт')
    стр.click('#addNoteForm_par_pech .btn-confirm-add')
    в = стр.evaluate("() => [getCustomOpts('par_st').length, getCustomNotes('par_pech').length]")
    if в != [1, 1] or стр.evaluate(итог) != до - 14169 + 45000:
        плохо(f"своя позиция и примечание: {в}, итог {стр.evaluate(итог)} — ждали по одной и +45 000 ₽")
    стр.evaluate("() => { renderOptionSections(); calc(); }")
    в = стр.evaluate("() => [document.getElementById('lbl_par_okno').classList.contains('highlighted'),"
                     " document.getElementById('star_par_okno').classList.contains('starred'),"
                     " document.getElementById('eye_par_okno').classList.contains('active'),"
                     " !!document.querySelector('#lbl_par_spinki .opt-gift-badge'),"
                     " document.querySelectorAll('#list_par_st [data-custom-id]').length,"
                     " document.querySelectorAll('#notesArea_par_pech .note-item').length]")
    if в != [True, True, True, True, 1, 1]:
        плохо(f"после перерисовки разделов отметки, своя позиция и примечание: {в}")
    стр.evaluate("() => { ПАР.podsv = 1; calc(); }")
    if стр.evaluate("() => document.getElementById('unit_par_podsv').textContent") != "уровень":
        плохо("подсветка полков на одном уровне: подпись счётчика не «уровень»")
    стр.evaluate("() => { ПАР.podsv = 2; calc(); }")

    # Печать: открывается, лист — с помещением и суммами парной. Несохранённый
    # расчёт печать сохраняет пресетом, как у каркаса, — сообщение об этом законно.
    в = стр.evaluate("""async () => {
      const т = []; const было = window.showToast; window.showToast = с => т.push(String(с));
      try {
        openPrintPreview(); await new Promise(r => setTimeout(r, 900));
        setPrintStyle('blank'); await new Promise(r => setTimeout(r, 600));
      } finally { window.showToast = было; }
      return { тосты: т, открыта: document.getElementById('printOverlay').style.display,
               лист: document.getElementById('printDoc').innerText };
    }""")
    лист = в["лист"]
    разделы = стр.evaluate("() => ['par_st', 'par_pech', 'par_log'].map(к => document.getElementById('sec_total_' + к).textContent.replace(/\\s₽$/, ''))")
    if в["открыта"] != "block" or any("следующей сборке" in т for т in в["тосты"]):
        плохо(f"окно печати парной: показ {в['открыта']}, сообщения {в['тосты']}")
    for нужно in ["ПОМЕЩЕНИЕ", "Камень, 3 × 4 × 2,3 м", "Парная 3 × 4 × 2,3 м", "Полка-лежак из кедра",
                  "Полки из осины, 2 яруса — 3,75 м²", "Дымоход до 6 м входит в расчёт"] + разделы:
        if нужно not in лист:
            плохо(f"лист «Бланка» у парной: нет «{нужно}»")
    for стиль in ("architect", "cards", "luxury", "classic"):
        т = стр.evaluate("с => { setPrintStyle(с); return new Promise(r => setTimeout(() => r(document.getElementById('printDoc').innerText), 600)); }", стиль)
        # Подпись стоит отдельной строкой; «Утепление базальтом…» — строка позиции, её не трогаем.
        if re.search(r"(^|\n)\s*(Кровля|КРОВЛЯ|Утепление|УТЕПЛЕНИЕ|Толщина:?)\s*(\n|$)", т) or "Толщина:" in т:
            плохо(f"лист «{стиль}» у парной печатает кровлю, утепление или толщину")
    стр.evaluate("() => { setPrintStyle('blank'); closePrintPreview(); }")
    стр.evaluate("() => resetEverything()")

    # Платёжный план парной (Константин, 27.10.2026: «аванс 60%, финал 50 тысяч
    # (также все копейки сюда +/-5 тыс.), остаток в середину этап перед началом
    # работ»): один договор -ПАР на три раздела; на 2 313 757 ₽ — задаток
    # 1 390 000, перед началом работ 875 000, финальный 48 757.
    стр.evaluate("ид => ид.forEach(к => document.getElementById('lbl_par_' + к).click())", МАКЕТ)
    ПЛАН = """() => { const к = getPPContracts(), с = ppState[к[0].id] || {};
      return { договоры: к.map(д => д.code + ':' + д.sections.join('+')), этапы: к[0].payments.map(р => р.label),
               суммы: с.amounts, финал: с.finalAmt, итог: ppGetTotal(к[0]),
               окно: document.getElementById('paymentPlanOverlay').style.display,
               кнопка: getComputedStyle(document.getElementById('paymentPlanBtn')).pointerEvents }; }"""
    стр.evaluate("() => openPaymentPlan()")
    план = стр.evaluate(ПЛАН)
    ждём = {"договоры": ["ПАР:par_st+par_pech+par_log"], "этапы": ["Задаток по договору", "Перед началом работ", "Финальный платёж"],
            "суммы": [1390000, 875000], "финал": 48757, "итог": 2313757, "окно": "block", "кнопка": "auto"}
    if план != ждём:
        плохо(f"платёжный план парной: {план} — ждали {ждём}")
    стр.evaluate("() => closePaymentPlan()")
    # План идёт за ценой: «звёздное небо» +53 135 ₽ и сборка премиальной +30 000 ₽ → 2 396 892 ₽.
    стр.evaluate("() => document.getElementById('lbl_par_zvezd').click()")
    план = стр.evaluate(ПЛАН)
    if (план["суммы"], план["финал"], план["итог"]) != ([1440000, 910000], 46892, 2396892):
        плохо(f"платёжный план после «звёздного неба»: {план['суммы']}, финальный {план['финал']}, итог {план['итог']} — "
              "ждали 1 440 000 / 910 000 / 46 892 при 2 396 892 ₽")
    стр.evaluate("() => resetEverything()")

    # Строки базы снимаются, под замком — нет (Константин, 27.10.2026: «То, что
    # включено в базу, сделай возможность снимать галочку… возле них поставь где-то
    # замок, чтобы было понятно, что это опция не снимается»).
    БАЗА = "() => Math.round(парБазы(парГеом()).par_st)"
    до = стр.evaluate(БАЗА)
    стр.evaluate("() => document.getElementById('lbl_par_door').click()")
    в = стр.evaluate("""() => [document.getElementById('chk_par_door').checked, document.getElementById('lbl_par_door').classList.contains('active'),
      document.getElementById('incl_par_door').textContent.replace(/\u00a0/g, ' '), ПАР.снятыСтроки.has('door')]""")
    if стр.evaluate(БАЗА) != до - 39192 or в != [False, False, "Снято с базы · −39 192 ₽", True]:
        плохо(f"снятие двери с базы: база {стр.evaluate(БАЗА)} при {до}, строка {в} — ждали минус 39 192 ₽")
    стр.evaluate("() => document.getElementById('lbl_par_door').click()")
    if стр.evaluate(БАЗА) != до or not стр.evaluate("() => document.getElementById('chk_par_door').checked"):
        плохо("повторное нажатие не вернуло дверь в базу")
    замки = стр.evaluate("() => ['dims','karkas','obr','utepl','par','osina','polki','door','plaf','vent','klap','prop','ust','dym','mineri','kamni','list','pusk','dost','brig','nakl','uborka'].filter(к => document.querySelector('#lbl_par_' + к + ' .par-lock'))")
    if замки != ["dims", "karkas", "obr", "utepl", "par", "osina"]:
        плохо(f"замки у строк базы: {замки} — ждали у самого отделения, каркаса, утепления и трёх строк отделки за м²")
    в = стр.evaluate("""() => { const т = []; const было = window.showToast; window.showToast = с => т.push(String(с));
      try { document.getElementById('lbl_par_obr').click(); } finally { window.showToast = было; }
      return [т, ПАР.снятыСтроки.has('obr'), document.getElementById('chk_par_obr').checked]; }""")
    if not (в[0] and "не снимается" in в[0][0]) or в[1] or not в[2]:
        плохо(f"строка под замком (обрешётка): сообщения {в[0]}, снята {в[1]}, отмечена {в[2]}")
    # Каждая снимаемая строка уносит свою часть, и все вместе — всю базу, кроме строк под замком.
    в = стр.evaluate("""() => { const к = ['polki','door','plaf','vent','klap','prop','ust','dym','mineri','kamni','list','pusk','dost','brig','nakl','uborka'];
      const б0 = парБазы(парГеом()); к.forEach(х => document.getElementById('lbl_par_' + х).click());
      const б1 = парБазы(парГеом()); const печь = Math.round(б1.par_pech), доп = Math.round(б1.par_log);
      const отд = Math.round(б1.par_st); const г = парГеом();
      const ждём = Math.round(23143 + (9116.98 + 3041.66 + 2108.85) * г.отд);
      к.forEach(х => document.getElementById('lbl_par_' + х).click());
      return [печь, доп, отд, ждём, Math.round(парБазы(парГеом()).par_st) === Math.round(б0.par_st)]; }""")
    if в[0] != 0 or в[1] != 0 or в[2] != в[3] or not в[4]:
        плохо(f"все снимаемые строки базы сняты: печь {в[0]}, доп. опции {в[1]}, парное {в[2]} (ждали {в[3]}), вернулись {в[4]}")
    # Раздел 3 — «Дополнительные опции» (Константин, 27.10.2026).
    if стр.evaluate("() => SECTIONS.find(с => с.key === 'par_log').name") != "3. Дополнительные опции":
        плохо("раздел 3 парной не называется «Дополнительные опции»")

    # Пресет парной (Константин, 27.10.2026: «По парной не предлагает сохранить
    # пресет… И в целом нет такой кнопки сохранить пресет»): кнопка в карточке,
    # напоминание внизу, и сохранённый расчёт открывается тем же до рубля.
    # Значок стоит position:fixed, а у такого offsetParent всегда null: видимость
    # меряется нарисованной рамкой, прозрачностью и тем, что лежит в его центре.
    стр.wait_for_timeout(700)
    в = стр.evaluate("""() => { const з = document.getElementById('presetChip');
      const р = з && з.getBoundingClientRect(), с = з && getComputedStyle(з);
      const виден = !!р && р.width > 20 && р.height > 16 && с.display !== 'none' && с.visibility !== 'hidden'
        && +с.opacity > .9 && !з.classList.contains('pc-hide')
        && з.contains(document.elementFromPoint(р.left + р.width / 2, р.top + р.height / 2));
      return [!!document.querySelector('#steamInfo .btn-save-preset'), надоНапомнитьСохранить(),
              виден && /Не сохран/.test(з.textContent),
              з && [з.className, з.textContent.trim().slice(0, 30), с.opacity, Math.round(р.width), Math.round(р.top)]]; }""")
    if в[:3] != [True, True, True]:
        плохо(f"парная без пресета: кнопка «Сохранить пресет» в карточке {в[0]}, напоминание {в[1]}, значок «Не сохранён» виден {в[2]} — {в[3]}")
    стр.evaluate("ид => ид.forEach(к => document.getElementById('lbl_par_' + к).click())", МАКЕТ)
    стр.evaluate("""() => { парнаяТип('log'); ПАР.L = 3.4; парнаяПечь('grom-40-p2-pech-komplekt'); ПАР.brig = 24;
      document.getElementById('lbl_par_vent').click(); document.getElementById('clientName').value = 'Проба Парная';
      calc(); }""")
    стр.click('#gift_par_spinki', force=True)
    стр.click('#hl_par_okno', force=True)
    стр.click('#addBtn_par_log')
    стр.fill('#addName_par_log', 'Вывоз мусора')
    стр.fill('#addPrice_par_log', '12000')
    стр.click('#addForm_par_log .btn-confirm-add')
    стр.click('#discSumLab'); стр.fill('#discountSavedInput', '50000')
    стр.evaluate("() => { document.getElementById('discountSavedInput').blur(); document.getElementById('cashDiscountCheck').click(); }")
    ОТПЕЧАТОК = """() => ({ итог: Math.round(_currentTotal), разделы: ['par_st','par_pech','par_log'].map(к => Math.round(_secTotalsCache[к])),
      спец: Math.round(window._итогСоСкидкой), вкл: [...ПАР.вкл].sort(), снято: [...ПАР.снятыСтроки], комн: ПАР.комн, L: ПАР.L, печь: ПАР.печь,
      бригада: ПАР.brig, подарки: [...giftedOpts], выделено: [...highlightedOpts], свои: getCustomOpts('par_log').map(о => о.name + ':' + о.price),
      клиент: document.getElementById('clientName').value, наличные: document.getElementById('cashDiscountCheck').checked,
      план: (() => { const к = getPPContracts()[0]; const с = ppState[к.id]; return [к.code, ...(с.amounts || []), с.finalAmt]; })() })"""
    было = стр.evaluate(ОТПЕЧАТОК)
    ид = стр.evaluate("""async () => { const st = collectState(); await сохранитьНовыйПресет('Проба парной', 'Проба парной', st);
      const все = loadAllPresets(); return Object.keys(все).find(к => все[к].name === 'Проба парной'); }""")
    if not ид:
        плохо("пресет парной не сохранился")
    else:
        стр.evaluate("async () => { resetEverything(); selectTech('Каркас'); await new Promise(r => setTimeout(r, 900)); }")
        стр.evaluate("ид => loadPreset(ид)", ид)
        стр.wait_for_timeout(2600)
        стало = стр.evaluate(ОТПЕЧАТОК)
        тех = стр.evaluate("() => [currentTech, document.getElementById('techSelectLabel').textContent, customProjects.some(п => /Парная/.test(п[0]))]")
        if стало != было or тех != ["steam", "Парная", False]:
            плохо(f"пресет парной открылся не тем: было {было}, стало {стало}, технология {тех}")
        if стр.evaluate("() => техПресета(loadAllPresets()[%r])" % ид) != "steam":
            плохо("сохранённый пресет парной не помечен технологией «Парная»")
    стр.evaluate("() => resetEverything()")

    # Поиск по опциям у парной есть с 28.10.2026 (подробно — check_steam_search.py).
    стр.evaluate("() => { openOptSearch(); }")
    if not стр.evaluate("() => getComputedStyle(document.getElementById('optSearchOverlay')).display !== 'none'"):
        плохо("поиск по опциям у парной не открылся")
    стр.evaluate("() => closeOptSearch()")

    # Соседи: каркас и брус после парной.
    стр.evaluate("async () => { selectTech('Каркас'); await new Promise(r => setTimeout(r, 900)); selectProjectOption(0); }")
    стр.wait_for_timeout(600)
    к = стр.evaluate("""() => ({ тех: currentTech, разделов: SECTIONS.length, ключи: SECTIONS.map(с => с.key).join(','),
      итог: Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, '')),
      строк: document.querySelectorAll('#optionSections .opt-item').length, парных: document.querySelectorAll('[id^="lbl_par_"]').length,
      проект: !!document.getElementById('projectSelectWrap').offsetParent, карточка: !!document.getElementById('steamRoomWrap').offsetParent,
      заголовок: document.getElementById('projectCardTitle').textContent })""")
    к["позицийПарной"] = стр.evaluate("() => OPTIONS.filter(о => о.парная).length")
    # Договоры — снова каркаса, и в память браузера состав парной не лёг.
    к["договоры"] = стр.evaluate("() => getPPContracts().map(д => д.code).join(',') + '|' + /par_/.test(localStorage.getItem('contractsConfig_v1') || '')")
    if к["тех"] != "frame" or к["разделов"] != 12 or "par_" in к["ключи"] or к["парных"] or not к["итог"] or к["позицийПарной"] \
            or not к["проект"] or к["карточка"] or к["заголовок"] != "Выбор проекта" or к["договоры"] != "КАР,ОТД|false":
        плохо(f"каркас после парной: {к}")
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); }")
    стр.wait_for_timeout(600)
    б = стр.evaluate("() => ({ тех: currentTech, итог: Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, '')), парных: document.querySelectorAll('[id^=\"lbl_par_\"]').length })")
    if б["тех"] != "glulam" or not б["итог"] or б["парных"]:
        плохо(f"брус после парной: {б}")
    # Снова парная — расчёт начат заново.
    в_парную(стр)
    ч = стр.evaluate(ЧИСЛА)
    if ч["итог"] != 1257216 or ч["вкл"]:
        плохо(f"повторный вход в парную: итог {ч['итог']}, отмечено {ч['вкл']} — ждали чистую базу")
    стр.close()
    return ош


ВЁРСТКА = """() => {
  const ш = document.documentElement.clientWidth, н = [];
  if (document.documentElement.scrollWidth > ш + 1) н.push('горизонтальная прокрутка ' + document.documentElement.scrollWidth + ' > ' + ш);
  document.querySelectorAll('#projectCard, #optionSections .opt-item, #optionSections .section-header, #breakdownTable .bd-row, #steamInfo .info-chip').forEach(э => {
    if (!э.offsetParent) return;
    const р = э.getBoundingClientRect();
    if (р.right > ш + 1 || р.left < -1) н.push('за краем: ' + (э.id || э.className) + ' ' + Math.round(р.left) + '…' + Math.round(р.right));
  });
  // Поле между числом счётчика и кнопками: «3,75» не должно касаться минуса.
  document.querySelectorAll('#optionSections .opt-qty-stepper').forEach(с => {
    const [м, п] = с.querySelectorAll('.opt-qty-btn'), в = с.querySelector('.opt-qty-val');
    let р;
    if (в.tagName === 'INPUT') {
      const с2 = getComputedStyle(в), к2 = document.createElement('canvas').getContext('2d');
      к2.font = с2.font; const ш2 = к2.measureText(в.value).width, б = в.getBoundingClientRect();
      const прав = с2.textAlign === 'center' ? (б.left + б.right + ш2) / 2 : б.right - parseFloat(с2.paddingRight);
      р = { left: прав - ш2, right: прав };
    } else { const т = document.createRange(); т.selectNodeContents(в); р = т.getBoundingClientRect(); }
    const з = Math.min(р.left - м.getBoundingClientRect().right, п.getBoundingClientRect().left - р.right);
    if (з < 4) н.push('счётчик ' + с.closest('.opt-item').id + ': до кнопки ' + з.toFixed(1) + ' px');
    // И обратное: число не висит в пустой клетке между кнопками (Константин,
    // 27.10.2026, снимком счётчиков парной: «Тут что за пробелы»).
    const пусто = Math.max(р.left - м.getBoundingClientRect().right, п.getBoundingClientRect().left - р.right);
    if (пусто > 10) н.push('счётчик ' + с.closest('.opt-item').id + ': между числом и кнопкой ' + пусто.toFixed(1) + ' px пустоты');
  });
  // Поля размеров — в карточке, не за её краем, высотой под палец, и число
  // в поле видно целиком.
  const карт = document.getElementById('steamRoomCard').getBoundingClientRect();
  document.querySelectorAll('#steamRoomCard .steam-dim').forEach(и => {
    const р = и.getBoundingClientRect();
    if (р.right > карт.right + 1 || р.left < карт.left - 1) н.push('поле размера ' + и.dataset.dim + ' за карточкой');
    if (р.height < 36) н.push('поле размера ' + и.dataset.dim + ' ' + р.height + ' px');
    const с = getComputedStyle(и), к = document.createElement('canvas').getContext('2d');
    к.font = с.font;
    if (к.measureText(и.value).width > р.width - parseFloat(с.paddingLeft) - parseFloat(с.paddingRight) + 0.5)
      н.push('поле размера ' + и.dataset.dim + ': число не помещается');
  });
  // «Выбрать» у строки печи: поле нажатия не меньше 32 px.
  document.querySelectorAll('.par-pick').forEach(к => {
    const р = к.getBoundingClientRect(), д = getComputedStyle(к, '::before');
    const в = р.height - parseFloat(д.top) - parseFloat(д.bottom);
    if (в < 32) н.push('«Выбрать» у печи: поле нажатия ' + Math.round(в) + ' px');
  });
  return н;
}"""


def вёрстка(бр, порт):
    кадры = []
    for ш in (390, 768, 1440):
        for ночь in (False, True):
            стр, ош = открыть(бр, порт, ш, ночь)
            в_парную(стр)
            стр.evaluate("ид => ид.forEach(к => document.getElementById('lbl_par_' + к).click())", МАКЕТ)
            # Ширина счётчиков считается в ch настоящего шрифта: мерить до того,
            # как Geologica легла, — мерить подменный. 27.10.2026 кадр 390 ночью
            # однажды снялся раньше шрифта и дал «пустоту» 10 px, которой нет.
            лёг = стр.evaluate("""async () => { await document.fonts.ready;
              for (let i = 0; i < 30; i++) {
                if ([...document.fonts].some(ф => /Geologica/.test(ф.family) && ф.status === 'loaded')) return true;
                await new Promise(r => setTimeout(r, 100)); }
              return false; }""")
            if not лёг:
                плохо(f"{ш} {'ночь' if ночь else 'день'}: Geologica не загрузилась — вёрстка мерилась бы подменным шрифтом")
            for н in стр.evaluate(ВЁРСТКА):
                плохо(f"{ш} {'ночь' if ночь else 'день'}: {н}")
            if ош:
                плохо(f"{ш}: ошибки страницы {ош[:2]}")
            кадры.append((ш, ночь))
            стр.close()
    return кадры


def main():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            ош = расчёт(бр, порт)
            if ош:
                плохо(f"ошибки страницы: {ош[:3]}")
            кадры = вёрстка(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print(f"Чисто: парная считает по книге (база 1 257 216 ₽, двенадцать опций — 2 313 757 ₽), шкала сборки "
          f"120 000 → 240 000 ₽, одна печь и один пол, тип помещения, размеры, счётчики, база и скидка; "
          f"печать работает, платёжный план 60 % / остаток / финальный до 50 000 ₽ и идёт за ценой; строки базы снимаются, "
          f"под замком — нет; пресет сохраняется и открывается тем же до рубля; печь подбирается на объём парной + 30 % "
          f"и 4 м³ за начатый м² окна, список печей фильтруется «Подходят к парной» и ставится по объёму, цене и книге; "
          f"каркас и брус после парной свои; вёрстка — {len(кадры)} кадров.")


if __name__ == "__main__":
    main()
