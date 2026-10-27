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
  • одну печь и один пол: вторая печь снимает первую, лиственница — плитку;
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
МАКЕТ = ['olha', 'polkiOlha', 'podsv', 'spinki', 'parya', 'panno', 'okno', 'maslo', 'nastil', 'yalta', 'talk', 'econ']

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


def в_парную(стр):
    стр.evaluate("""async () => { window.IS_TEST_DOMAIN = true; applySteamGate();
      selectTech('Парная'); await new Promise(r => setTimeout(r, 500)); }""")


def расчёт(бр, порт):
    стр, ош = открыть(бр, порт, 1440)
    # Калитка: в бою — только администратор, на тесте — все.
    калитка = стр.evaluate("""() => {
      const было = [window.IS_TEST_DOMAIN, window._sbProfile];
      const пункт = () => document.querySelector('#techSelectDropdown [data-tech="steam"]').style.display;
      window.IS_TEST_DOMAIN = false; window._sbProfile = { role: 'manager' }; applySteamGate();
      const менеджер = пункт();
      window._sbProfile = { role: 'admin' }; applySteamGate();
      const админ = пункт();
      window.IS_TEST_DOMAIN = true; window._sbProfile = { role: 'manager' }; applySteamGate();
      const тест = пункт();
      [window.IS_TEST_DOMAIN, window._sbProfile] = было;
      return { менеджер, админ, тест };
    }""")
    if калитка != {"менеджер": "none", "админ": "", "тест": ""}:
        плохо(f"калитка парной: {калитка} — ждали скрыто у менеджера в бою, видно у администратора и на тесте")

    в_парную(стр)
    ч = стр.evaluate(ЧИСЛА)
    if ч["тех"] != "steam" or ч["строк"] != 40:
        плохо(f"после выбора «Парная»: технология {ч['тех']}, строк парной {ч['строк']} — ждали 40")
        стр.close()
        return ош
    if ч["итог"] != 1257216:
        плохо(f"база парной 3 × 4 × 2,3 м по камню: {ч['итог']} ₽, ждали 1 257 216 ₽")
    заголовки = стр.evaluate("""() => [document.getElementById('techTitle').textContent,
      document.getElementById('projectCardTitle').textContent, document.getElementById('techSelectLabel').textContent,
      getComputedStyle(document.getElementById('projectSelectWrap')).display === 'none' || !document.getElementById('projectSelectWrap').offsetParent,
      !!document.getElementById('steamRoomWrap').offsetParent]""")
    if заголовки != ["Парное отделение", "Парная в доме заказчика", "Парная", True, True]:
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

    # Одна печь, один пол.
    стр.evaluate("() => ['yalta', 'optima', 'polList', 'plitka'].forEach(к => document.getElementById('lbl_par_' + к).click())")
    if стр.evaluate(ЧИСЛА)["вкл"] != ["optima", "plitka"]:
        плохо(f"печь и пол: отмечено {стр.evaluate(ЧИСЛА)['вкл']} — ждали одну печь (Оптима) и плитку")
    почему = стр.evaluate("() => [document.getElementById('why_par_yalta').textContent, document.getElementById('why_par_optima').textContent]")
    # 27,6 м³ входит и в 25–35 м³ Ялты, и в 16–28 м³ Оптимы.
    if почему != ["подходит: парная 27,6 м³", "подходит: парная 27,6 м³"]:
        плохо(f"подсказка печей по объёму: {почему}")
    стр.evaluate("() => { ПАР.L = 4; calc(); }")
    почему = стр.evaluate("() => [document.getElementById('why_par_yalta').textContent, document.getElementById('why_par_yalta').classList.contains('warn')]")
    if почему != ["мала: парная 36,8 м³", True]:
        плохо(f"печь для парной 36,8 м³: {почему} — ждали «мала» с тревогой")
    стр.evaluate("() => { ПАР.L = 3; resetCheckedOptions(); }")

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
    в = стр.evaluate("""() => [ПАР.L, document.getElementById('name_par_dims').textContent,
      document.getElementById('pardim_L').value, (document.querySelector('#steamInfo .info-chip strong') || {}).textContent]""")
    if в[0] != 3.6 or "3,6 × 4 × 2,3 м" not in в[1] or в[2] != "3,6":
        плохо(f"длина 3,6 м: {в}")
    стр.evaluate("() => { const и = document.getElementById('pardim_L'); и.focus(); и.value = '0,2'; и.dispatchEvent(new Event('input')); и.blur(); }")
    if стр.evaluate("() => [ПАР.L, document.getElementById('pardim_L').value]") != [3.6, "3,6"]:
        плохо("неверная длина 0,2 м не вернулась к последней верной")
    стр.evaluate("() => { const и = document.getElementById('pardim_L'); и.value = '3'; и.dispatchEvent(new Event('input')); и.blur(); }")
    стр.evaluate("() => document.querySelector('#lbl_par_polki .opt-qty-btn:last-child').click()")
    if стр.evaluate("() => [ПАР.polki, document.getElementById('qtyval_par_polki').textContent]") != [4, "4"]:
        плохо(f"счётчик полков +0,25: {стр.evaluate('() => ПАР.polki')}")
    стр.evaluate("() => document.querySelector('#lbl_par_polki .opt-qty-btn').click()")
    дни = стр.evaluate("() => [парДниАвто(парГеом()), document.getElementById('qtyval_par_brig').textContent]")
    # ⌈44,2 / 3,5 + 3,75 / 1,5 + 4⌉ = ⌈19,13⌉ = 20 — те же 20 дней дают 143 280 ₽ логистики книги.
    if дни != [20, "20"]:
        плохо(f"срок бригады по расчёту: {дни} — ждали 20 дней")
    стр.evaluate("() => document.querySelector('#lbl_par_brig .opt-qty-btn:last-child').click()")
    if стр.evaluate("() => [ПАР.brig, document.getElementById('calc_par_brig').textContent.startsWith('срок вписан вручную')]") != [21, True]:
        плохо("срок бригады вручную: счётчик или подпись не поменялись")

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
    if панель != ["Парное отделение", "Печь и комплектующие", "Логистика"]:
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

    # Печать: открывается, пресет не сохраняет, лист — с помещением и суммами парной.
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
    if в["открыта"] != "block" or в["тосты"]:
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

    # Чего у парной нет — словами, без окон.
    for вызов, окно in (("openPaymentPlan()", "paymentPlanOverlay"),
                        ("savePreset()", "presetNameOverlay"), ("openOptSearch()", "optSearchOverlay")):
        в = стр.evaluate("""([вызов, окно]) => { const т = []; const было = window.showToast;
          window.showToast = с => т.push(String(с)); try { eval(вызов); } finally { window.showToast = было; }
          const о = document.getElementById(окно); return [т, !!(о && о.style.display && о.style.display !== 'none')]; }""", [вызов, окно])
        if not any("следующей сборке" in т for т in в[0]) or в[1]:
            плохо(f"{вызов} у парной: сообщения {в[0]}, окно открыто {в[1]}")

    # Соседи: каркас и брус после парной.
    стр.evaluate("async () => { selectTech('Каркас'); await new Promise(r => setTimeout(r, 900)); selectProjectOption(0); }")
    стр.wait_for_timeout(600)
    к = стр.evaluate("""() => ({ тех: currentTech, разделов: SECTIONS.length, ключи: SECTIONS.map(с => с.key).join(','),
      итог: Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, '')),
      строк: document.querySelectorAll('#optionSections .opt-item').length, парных: document.querySelectorAll('[id^="lbl_par_"]').length,
      проект: !!document.getElementById('projectSelectWrap').offsetParent, карточка: !!document.getElementById('steamRoomWrap').offsetParent,
      заголовок: document.getElementById('projectCardTitle').textContent })""")
    к["позицийПарной"] = стр.evaluate("() => OPTIONS.filter(о => о.парная).length")
    if к["тех"] != "frame" or к["разделов"] != 12 or "par_" in к["ключи"] or к["парных"] or not к["итог"] or к["позицийПарной"] \
            or not к["проект"] or к["карточка"] or к["заголовок"] != "Выбор проекта":
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
    const т = document.createRange(); т.selectNodeContents(в); const р = т.getBoundingClientRect();
    const з = Math.min(р.left - м.getBoundingClientRect().right, п.getBoundingClientRect().left - р.right);
    if (з < 4) н.push('счётчик ' + с.closest('.opt-item').id + ': до кнопки ' + з.toFixed(1) + ' px');
  });
  // Поля размеров — внутри строки, не меньше 28 px в высоту.
  document.querySelectorAll('.dim-in').forEach(и => {
    const р = и.getBoundingClientRect(), с = и.closest('.opt-item').getBoundingClientRect();
    if (р.right > с.right + 1) н.push('поле размера ' + и.dataset.dim + ' за строкой');
    if (р.height < 28) н.push('поле размера ' + и.dataset.dim + ' ' + р.height + ' px');
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
          f"печать работает, план и пресет отвечают словами; каркас и брус после парной свои; вёрстка — {len(кадры)} кадров.")


if __name__ == "__main__":
    main()
