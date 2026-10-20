#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Доска пресетов — кнопка в шапке и окно с четырьмя столбцами.

Константин 20.10.2026, со снимком макета kanban-v2: «Вот тут ещё слева добавь
«На согласовании», чтобы в отдельную колонку попадали пресеты, которые
отправили на согласование. Чтобы был к ним быстрый доступ. И всё супер,
внедряй макет»; «Все видят всех карточки, как в СРМ. И есть кнопка «Мои»,
запоминать выбор»; «Нереализовано и подписано владелец пресета, редактор и
администратор».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • кнопка доски стоит между колокольчиком и «Пресетами»; число на ней —
    карточки, ждущие того, кто смотрит: проверяющему — расчёт, где его место
    не согласовано, владельцу — возвращённый и изменённый после согласования;
  • столбцы по порядку: «На согласовании», «Договор согласован», «Договор
    подписан», «Не реализовано»; каждая карточка — в своём; метки «Возвращён
    с правками», «Ждёт повторного согласования», причина, приходные ордера;
  • менеджер видит и чужие карточки; «Мои» оставляет свои и запоминается в
    настройках — после повторного открытия доски выбор на месте;
  • поиск по коду оставляет одну карточку;
  • чужую карточку менеджер не переносит: пункты меню выключены, перенос
    перетаскиванием отвечает подсказкой и базу не трогает;
  • своя карточка уходит в «Не реализовано» только с причиной; «Отменить»
    возвращает её в прежний столбец; база получает причину с комментарием;
  • «Договор подписан» с доски спрашивает подтверждение и открывает пресет
    тем же путём, что колокольчик; изменённый после согласования не
    подписывается; специалисту кнопки «Подписан» в мини-окне нет;
  • калькулятор с открытым согласованным пресетом сообщает базе отпечаток
    расчёта — по нему доска ставит «Ждёт повторного согласования»;
  • вёрстка на 390, 768 и 1440, днём и ночью (тема одна — «Бланк», «Модерн»
    снят 27.09.2026):
    страница не шире экрана, окно в экране, карточки не шире столбца, поля
    нажатия кнопок не меньше 44 px; кнопка доски не уводит ряд шапки на
    телефоне в лишнюю строку.

Проверено и обратное: без строки «Мои» в настройках, без столбца «На
согласовании» и без проверки прав проба краснеет.

    python3 check_preset_board.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


# Учебные строки доски: имена и коды выдуманы.
ДОСКА = """(свой) => { const д = Date.now(), в = м => new Date(д - м * 60e3).toISOString(), я = _sbUser.id;
  const р = (код, о) => Object.assign({ code: код, state: 'pending', preset_name: '', project_name: '', sent_by: 'u-другой', sent_name: 'Игорь Учебный',
    sent_at: в(600), sent_total: 2000000, decided_name: null, decided_at: null, approved_at: null, approved_total: null, approved_print: null,
    current_print: null, sent_print: 'v1-aaaaaaaaaaaaaaaa', price_print: null, check_print: null, for_all: false, signed_at: null, signed_name: null,
    lost_at: null, lost_name: null, lost_reason: null, author_id: null, author_name: 'Игорь Учебный', tech: 'frame', thickness: '150 мм', orders: 0, messages: 0 }, о);
  window.__ДОСКА = [
    р('111111', { preset_name: 'Учебная баня 6×4', sent_by: я, author_id: я, author_name: 'Проба Пробная', messages: 2 }),
    р('222222', { preset_name: 'Баня с террасой 5×7', state: 'returned', decided_name: 'Ольга Проверкина', decided_at: в(30), sent_by: я, author_id: я, author_name: 'Проба Пробная' }),
    р('333333', { preset_name: 'Барнхаус-баня 6×8', price_print: 'v1-aaaaaaaaaaaaaaaa', tech: 'glulam', thickness: '160 мм' }),
    р(свой, { preset_name: 'Баня «Проба»', state: 'approved', approved_at: в(120), approved_total: 2432000, approved_print: 'v1-bbbbbbbbbbbbbbbb',
      current_print: 'v1-bbbbbbbbbbbbbbbb', sent_by: я, author_id: я, author_name: 'Проба Пробная' }),
    р('555555', { preset_name: 'Баня с комнатой отдыха 7×5', state: 'approved', approved_at: в(300), approved_total: 4185000,
      approved_print: 'v1-cccccccccccccccc', current_print: 'v1-dddddddddddddddd', sent_by: я, author_id: я, author_name: 'Проба Пробная' }),
    р('666666', { preset_name: 'Учебный проект 6×6', state: 'approved', approved_at: в(900), approved_total: 2870000, signed_at: в(800), orders: 2 }),
    р('777777', { preset_name: 'Баня с бассейном 8×10', state: 'approved', approved_at: в(2000), approved_total: 7920000, lost_at: в(100), lost_reason: 'Дорого' }),
  ];
  window.__ВЫЗОВЫ = [];
  const пиши = (имя, ф) => { window.__RPC[имя] = а => { window.__ВЫЗОВЫ.push([имя, а]); return ф(а); }; };
  пиши('preset_board', () => window.__ДОСКА.map(с => Object.assign({}, с)));
  пиши('preset_approval_lost', а => ({ code: а.p_code, lost_at: new Date().toISOString(), lost_reason: а.p_reason, lost_name: 'Проба' }));
  пиши('preset_approval_unlost', а => ({ code: а.p_code }));
  пиши('preset_approval_print', () => null);
  window.__ОТКРЫТО = [];
  window.открытьСогласование = async код => { window.__ОТКРЫТО.push(String(код)); };
}"""

СОСТОЯНИЕ = """() => { const о = document.getElementById('boardOverlay');
  const кол = [...document.querySelectorAll('#boardCols .dsk-col')].map(с => ({ ид: с.dataset.dskCol, имя: с.querySelector('.dsk-cn').textContent,
    коды: [...с.querySelectorAll('.dsk-card')].map(к => к.dataset.dskCode),
    метки: [...с.querySelectorAll('.dsk-tag')].map(т => т.textContent) }));
  return { открыта: !!о && о.style.display !== 'none', кол, кто: appSettings.boardWho || '',
    счёт: document.getElementById('boardCnt').hidden ? 0 : +document.getElementById('boardCnt').textContent }; }"""

ВЁРСТКА = """() => { const н = [], W = document.documentElement.clientWidth, H = innerHeight;
  const п = document.getElementById('boardPanel').getBoundingClientRect();
  if (п.left < -.5 || п.right > W + .5) н.push('окно доски шире экрана: ' + Math.round(п.left) + '…' + Math.round(п.right));
  if (document.documentElement.scrollWidth > W + 1) н.push('страница шире экрана');
  document.querySelectorAll('#boardCols .dsk-col').forEach(с => { if (getComputedStyle(с).display === 'none') return;
    const ср = с.getBoundingClientRect();
    с.querySelectorAll('.dsk-card').forEach(к => { const r = к.getBoundingClientRect();
      if (r.left < ср.left - .5 || r.right > ср.right + .5) н.push('карточка шире столбца: ' + к.dataset.dskCode);
      if (к.scrollWidth > к.clientWidth + 1) н.push('содержимое шире карточки: ' + к.dataset.dskCode);
      const нм = к.querySelector('.dsk-nm').getBoundingClientRect(), кн = к.querySelector('.dsk-menu').getBoundingClientRect();
      if (нм.right > кн.left + .5) н.push('название налезает на «⋯»: ' + к.dataset.dskCode); }); });
  const поле = б => { const r = б.getBoundingClientRect(), с = getComputedStyle(б, '::before');
    const есть = с.content && с.content !== 'none' && с.position === 'absolute';
    return { ш: r.width - (есть ? (parseFloat(с.left) || 0) + (parseFloat(с.right) || 0) : 0), в: r.height - (есть ? (parseFloat(с.top) || 0) + (parseFloat(с.bottom) || 0) : 0) }; };
  document.querySelectorAll('#boardPanel .dsk-menu, #boardPanel .dsk-seg button, #boardPanel .dsk-tabs button, #boardPanel .ovl-x').forEach(б => {
    const r = б.getBoundingClientRect(); if (!r.width) return;
    const п_ = поле(б); if (п_.в < 43.5 || п_.ш < 43.5 && !б.closest('.dsk-seg') && !б.closest('.dsk-tabs'))
      н.push('поле нажатия «' + (б.getAttribute('aria-label') || б.textContent.trim()) + '» ' + Math.round(п_.ш) + '×' + Math.round(п_.в)); });
  return н; }"""


def открыть_доску(стр):
    стр.locator("#boardBtn").click(); стр.wait_for_timeout(500)


def закрыть_доску(стр):
    стр.evaluate("() => закрытьДоску()"); стр.wait_for_timeout(200)


def прогон(бр, порт, ш, в, ночь, модерн, полный):
    н = f"[{ш}{' ночь' if ночь else ''}{' модерн' if модерн else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    if модерн:
        стр.evaluate("() => applyUiStyle('modern', false)")
    шрифт = стр.evaluate("""() => { const и = document.createElement('span'); и.style.cssText = 'position:absolute;visibility:hidden;font-size:40px;white-space:nowrap'; и.textContent = 'Доска пресетов';
      document.body.appendChild(и); const шир = ш => { и.style.fontFamily = ш; return и.getBoundingClientRect().width; };
      const д = Math.abs(шир("'Geologica',monospace") - шир('monospace')) > .5; и.remove(); return д; }""")
    if not шрифт:
        плохо(f"{н} Geologica не легла — ширины меряются подменным шрифтом"); стр.close(); return
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДОСКА, код)
    # ── кнопка в шапке ──
    п = стр.evaluate("""() => { const к = [...document.querySelectorAll('#headerBtns > *')].map(э => э.id);
      return { до: к.indexOf('bellWrap'), доска: к.indexOf('boardBtn'), после: к.indexOf('presetsBtn') }; }""")
    if not (п["до"] >= 0 and п["доска"] == п["до"] + 1 and п["после"] == п["доска"] + 1):
        плохо(f"{н} кнопка доски не между колокольчиком и «Пресетами»: {п}")
    if ш < 500:
        ряд = стр.evaluate("""() => { const б = document.getElementById('boardBtn'), ш_ = document.getElementById('headerBtns');
          const с = ш_.getBoundingClientRect().height; б.style.display = 'none'; const без = ш_.getBoundingClientRect().height; б.style.display = ''; return [с, без]; }""")
        if ряд[0] > ряд[1] + 1:
            плохо(f"{н} кнопка доски уводит ряд шапки в лишнюю строку: {ряд[1]:.0f} → {ряд[0]:.0f} px")
        # Телефон: шестерёнка — в первом ряду с колокольчиком, доска — первой во
        # втором, перед «Пресетами» (Константин 20.10.2026: «Поменяй местами»).
        м = стр.evaluate("""() => { const в = id => document.getElementById(id).getBoundingClientRect();
          const ряд2 = [...document.querySelectorAll('#headerBtns > *')].filter(э => э.offsetParent && Math.abs(э.getBoundingClientRect().top - в('presetsBtn').top) < 4)
            .sort((а, б) => а.getBoundingClientRect().left - б.getBoundingClientRect().left).map(э => э.id);
          return { колокол: в('bellWrap').top, шест: в('settingsBtn').top, доска: в('boardBtn').top, пресеты: в('presetsBtn').top, ряд2 }; }""")
        if abs(м["шест"] - м["колокол"]) > 4:
            плохо(f"{н} шестерёнка не в первом ряду с колокольчиком: {м}")
        if abs(м["доска"] - м["пресеты"]) > 4 or not м["ряд2"] or м["ряд2"][0] != "boardBtn":
            плохо(f"{н} кнопка доски не первая во втором ряду перед «Пресетами»: {м['ряд2']}")
    # Ждущие — точкой в цвет «На согласовании», как у справки (20.10.2026: «поставь
    # на доску такую метку точку, только оранжевый цвет»): круг до 7 px у верхнего
    # правого угла значка, значок закрыт не больше чем на 8 %.
    стр.evaluate("() => { const ц = document.getElementById('boardCnt'); ц.hidden = false; ц.textContent = '1'; }")
    м = стр.evaluate("""() => { const ц = document.getElementById('boardCnt'), р = ц.getBoundingClientRect(), з = document.querySelector('#boardBtn svg').getBoundingClientRect();
      const пер = Math.max(0, Math.min(р.right, з.right) - Math.max(р.left, з.left)) * Math.max(0, Math.min(р.bottom, з.bottom) - Math.max(р.top, з.top));
      const с = getComputedStyle(ц), т = getComputedStyle(document.body).getPropertyValue('--pc-warm').trim();
      const цвет = (() => { const д = document.createElement('i'); д.style.color = т; document.body.appendChild(д); const в = getComputedStyle(д).color; д.remove(); return в; })();
      return { ш: р.width, в: р.height, круг: parseFloat(с.borderTopLeftRadius) >= р.width / 2 - .5, цвет: с.backgroundColor === цвет,
        уУгла: Math.abs(р.right - з.right) <= 7 && Math.abs(р.top - з.top) <= 7, доля: пер / (з.width * з.height) }; }""")
    if м["ш"] > 7 or м["в"] > 7 or not м["круг"] or not м["цвет"] or not м["уУгла"] or м["доля"] > .08:
        плохо(f"{н} на кнопке доски не оранжевая точка у угла значка: {м}")
    стр.evaluate("() => { window._sbProfile.role = 'manager'; appSettings.boardWho = 'all'; }")
    стр.evaluate("() => загрузитьДоску(true)"); стр.wait_for_timeout(300)
    стр.evaluate("() => scrollTo(0, 0)")
    стр.screenshot(path=str(СНИМКИ / f"шапка_{ш}{'_ночь' if ночь else ''}.png"), clip={"x": 0, "y": 0, "width": ш, "height": 260})
    стр.evaluate("() => загрузитьДоску(true)"); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["счёт"] != 2:
        плохо(f"{н} число на кнопке у менеджера: {с['счёт']}, ждали 2 (возвращённый и изменённый после согласования)")
    стр.evaluate("() => { window._sbProfile.role = 'editor'; обновитьСчётДоски(); }")
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["счёт"] != 3:
        плохо(f"{н} число на кнопке у редактора: {с['счёт']}, ждали 3 (один без цены и два своих)")
    стр.evaluate("() => { window._sbProfile.role = 'manager'; обновитьСчётДоски(); }")
    # ── столбцы ──
    открыть_доску(стр)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not с["открыта"]:
        плохо(f"{н} доска не открылась"); стр.close(); return
    имена = [к["имя"] for к in с["кол"]]
    if имена != ["На согласовании", "Договор согласован", "Договор подписан", "Не реализовано"]:
        плохо(f"{н} столбцы: {имена}")
    ждём = {"review": ["111111", "222222", "333333"], "agreed": [код, "555555"], "signed": ["666666"], "lost": ["777777"]}
    for к in с["кол"]:
        if sorted(к["коды"]) != sorted(ждём.get(к["ид"], [])):
            плохо(f"{н} в «{к['имя']}» карточки {к['коды']}, ждали {ждём.get(к['ид'])}")
    метки = {к["ид"]: к["метки"] for к in с["кол"]}
    for ид, т in [("review", "Возвращён с правками"), ("review", "Цена — согласовано"), ("agreed", "Ждёт повторного согласования"),
                  ("signed", "Приходных ордеров: 2"), ("lost", "Дорого"), ("review", "Чат · 2")]:
        if т not in метки.get(ид, []):
            плохо(f"{н} нет метки «{т}» в столбце {ид}: {метки.get(ид)}")
    if ш < 701:
        вкладки = стр.evaluate("() => [...document.querySelectorAll('#boardTabs button')].map(б => б.textContent)")
        if len(вкладки) != 4 or not вкладки[0].startswith("На согласовании"):
            плохо(f"{н} вкладки столбцов на телефоне: {вкладки}")
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {т}")
    стр.screenshot(path=str(СНИМКИ / f"доска_{ш}{'_ночь' if ночь else ''}{'_модерн' if модерн else ''}.png"))
    if полный:
        # ── «Мои» запоминается ──
        стр.locator("[data-dsk-who=mine]").click(); стр.wait_for_timeout(200)
        с = стр.evaluate(СОСТОЯНИЕ)
        коды = sum([к["коды"] for к in с["кол"]], [])
        if с["кто"] != "mine" or sorted(коды) != sorted(["111111", "222222", код, "555555"]):
            плохо(f"{н} «Мои»: настройка «{с['кто']}», карточки {коды}")
        закрыть_доску(стр); открыть_доску(стр)
        if стр.evaluate("() => document.querySelector('[data-dsk-who=mine]').getAttribute('aria-pressed')") != "true":
            плохо(f"{н} выбор «Мои» не сохранился после повторного открытия")
        стр.locator("[data-dsk-who=all]").click(); стр.wait_for_timeout(200)
        # ── поиск по коду ──
        стр.fill("#boardQ", "333 333"); стр.wait_for_timeout(200)
        коды = sum([к["коды"] for к in стр.evaluate(СОСТОЯНИЕ)["кол"]], [])
        if коды != ["333333"]:
            плохо(f"{н} поиск по коду «333 333»: {коды}")
        стр.fill("#boardQ", ""); стр.wait_for_timeout(200)
        # ── чужая карточка: менеджер не переносит ──
        if ш < 701:
            стр.locator("[data-dsk-tab=review]").click(); стр.wait_for_timeout(150)
        стр.locator("[data-dsk-menu='333333']").click(); стр.wait_for_timeout(200)
        вкл = стр.evaluate("() => [...document.querySelectorAll('#boardPop [data-dsk-to]')].filter(б => !б.disabled).map(б => б.dataset.dskTo)")
        if вкл:
            плохо(f"{н} менеджеру открыт перенос чужой карточки: {вкл}")
        стр.keyboard.press("Escape"); стр.wait_for_timeout(100)
        стр.evaluate("() => перенестиНаДоске('333333', 'lost')"); стр.wait_for_timeout(200)
        if any(в_[0] == "preset_approval_lost" for в_ in стр.evaluate("() => window.__ВЫЗОВЫ")) or not стр.locator("#boardLostDlg").is_hidden():
            плохо(f"{н} чужая карточка ушла в «Не реализовано» без прав")
        стр.evaluate("() => закрытьДиалогиДоски()")
        # ── своя — с причиной, и «Отменить» ──
        стр.locator("[data-dsk-menu='111111']").click(); стр.wait_for_timeout(200)
        стр.screenshot(path=str(СНИМКИ / f"доска_меню_{ш}.png"))
        стр.locator("#boardPop [data-dsk-to=lost]").click(); стр.wait_for_timeout(200)
        стр.screenshot(path=str(СНИМКИ / f"доска_причина_{ш}.png"))
        if стр.locator("#boardLostDlg").is_hidden():
            плохо(f"{н} перенос в «Не реализовано» не спросил причину")
        else:
            if стр.locator("#boardLostOk").is_enabled():
                плохо(f"{н} «Перенести» нажимается без причины")
            for т in стр.evaluate("""() => { const н = [], д = document.querySelector('#boardLostDlg .dsk-dlg').getBoundingClientRect();
                if (д.left < 0 || д.right > innerWidth || д.top < 0 || д.bottom > innerHeight) н.push('окно причины вне экрана');
                document.querySelectorAll('#boardLostDlg .dsk-btn, #boardLostDlg label').forEach(б => { const r = б.getBoundingClientRect(), с = getComputedStyle(б, '::before');
                  const h = r.height - (с.position === 'absolute' ? (parseFloat(с.top) || 0) + (parseFloat(с.bottom) || 0) : 0);
                  if (h < 39.5) н.push('поле «' + б.textContent.trim() + '» ' + Math.round(h)); });
                return н; }"""):
                плохо(f"{н} {т}")
            стр.locator("#boardLostRs label", has_text="Отложил стройку").click()
            стр.fill("#boardLostC", "весной вернётся")
            стр.locator("#boardLostOk").click(); стр.wait_for_timeout(400)
            выз = [в_ for в_ in стр.evaluate("() => window.__ВЫЗОВЫ") if в_[0] == "preset_approval_lost"]
            if not выз or выз[-1][1] != {"p_code": "111111", "p_reason": "Отложил стройку: весной вернётся"}:
                плохо(f"{н} база получила не ту причину: {выз}")
            с = стр.evaluate(СОСТОЯНИЕ)
            if "111111" not in [к for к_ in с["кол"] if к_["ид"] == "lost" for к in к_["коды"]]:
                плохо(f"{н} карточка не встала в «Не реализовано»")
            стр.locator("#boardToastU").click(); стр.wait_for_timeout(400)
            с = стр.evaluate(СОСТОЯНИЕ)
            if "111111" not in [к for к_ in с["кол"] if к_["ид"] == "review" for к in к_["коды"]] or \
                    not any(в_[0] == "preset_approval_unlost" for в_ in стр.evaluate("() => window.__ВЫЗОВЫ")):
                плохо(f"{н} «Отменить» не вернуло карточку на согласование")
        # ── подпись с доски ──
        стр.evaluate("() => перенестиНаДоске('555555', 'signed')"); стр.wait_for_timeout(200)
        if not стр.locator("#boardSignDlg").is_hidden():
            плохо(f"{н} изменённый после согласования расчёт предлагают подписать")
        стр.evaluate("(к) => перенестиНаДоске(к, 'signed')", код); стр.wait_for_timeout(200)
        if стр.locator("#boardSignDlg").is_hidden():
            плохо(f"{н} перенос в «Подписан» не спросил подтверждения")
        else:
            стр.locator("#boardSignOk").click(); стр.wait_for_timeout(500)
            if стр.evaluate("() => window.__ОТКРЫТО") != [код] or стр.evaluate(СОСТОЯНИЕ)["открыта"]:
                плохо(f"{н} «Подписан» с доски не открыл пресет путём колокольчика: {стр.evaluate('() => window.__ОТКРЫТО')}")
        стр.evaluate("() => { window.__ВЫЗОВЫ = []; }")
        if стр.evaluate("() => блокПодписиHtml({ state: 'approved' }, true, false)") != "":
            плохо(f"{н} кнопка «Подписан» в мини-окне без права подписи")
        # ── отпечаток расчёта — в базу ──
        стр.evaluate("""(к) => { _согласование = { код: String(к), строка: { state: 'approved', approved_print: 'v1-0000000000000000', current_print: null },
          грузится: false, когда: Date.now(), ошибка: '', шлём: false }; _доскаОтпечатки.clear(); отрисоватьЗначокПресета(); }""", код)
        стр.wait_for_timeout(4600)
        выз = [в_ for в_ in стр.evaluate("() => window.__ВЫЗОВЫ") if в_[0] == "preset_approval_print"]
        if len(выз) != 1 or выз[0][1].get("p_code") != код or not str(выз[0][1].get("p_print", "")).startswith("v1-"):
            плохо(f"{н} отпечаток расчёта не ушёл в базу один раз: {выз}")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, False, False, True)
                прогон(бр, порт, 390, 844, False, False, True)
                прогон(бр, порт, 768, 1024, False, False, False)
                прогон(бр, порт, 390, 844, True, False, False)
                прогон(бр, порт, 1440, 900, True, False, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: кнопка доски между колокольчиком и «Пресетами» с числом ждущих; четыре столбца с «На согласовании» первым; "
          "«Мои» запоминается; чужое менеджер не переносит; «Не реализовано» с причиной и отменой; «Подписан» через пресет; "
          "отпечаток расчёта уходит в базу; вёрстка на 390, 768 и 1440 днём и ночью.")


if __name__ == "__main__":
    главная()
