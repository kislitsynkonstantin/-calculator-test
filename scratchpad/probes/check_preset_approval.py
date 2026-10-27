#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Согласование расчёта — наверху вкладки «Проверка» мини-окна.

Константин 17.10.2026, раздел «Решения за тобой» макета
mockups/approval-flow-v1.html: «Вот тут отлично, делай как тут написал».
С 18.10.2026 согласование двойное (Константин: «должно быть 2 согласования:
от роли Редактор… и от Администратора/Специалиста… Но у меня должно быть
админское ещё согласование, типа «Согласовать за всех»»): цену согласует
редактор, чек-лист — администратор или специалист, администратор может
согласовать оба места разом. Согласование снимает любое изменение
суммы (опции, цены, проект, толщина, скидка), реквизиты его не снимают; со
стопом не отправить, вопросы не мешают; весть — в колокольчике.

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • автор без согласования: «Не согласован», «Отправить на согласование»;
    договоры в окне печати закрыты подписью «После согласования спецификации»;
  • отправка: функция базы получает код, отпечаток текущего расчёта, сумму со
    скидкой и снимок; плашка «Ждёт согласования»; действие в журнале;
  • два места под плашкой: «Цена» и «Чек-лист», кто и когда или «ждёт»;
  • проверяющий (редактор): «Вернуть с правками» и «Согласовать цену»; открытая
    правка из чата держит «Согласовать» выключенным и говорит почему, база
    при этом не спрашивается; возврат — плашка «Возвращён с правками»;
  • автор после возврата: число открытых правок и «Отправить снова»;
  • согласование цены одно договор не открывает: расчёт ждёт чек-листа, у
    редактора кнопки «Согласовать» больше нет, автору в колокольчик —
    «Цена согласована, ждёт чек-листа»; специалист видит «Согласовать
    чек-лист», после него — «Согласовано», в плашке оба имени, договоры
    открыты, подпись «Согласован ДД.ММ»; реквизиты согласования не снимают;
  • администратор: «Согласовать чек-лист» и отдельно «Согласовать за всех»;
    «за всех» согласует оба места, в плашке «за всех»;
  • специалисту договор открыт и без согласования (Константин, 27.10.2026:
    «„Специалисту“ сделай доступ к комплекту договора сразу, так как ей надо
    заполнить реквизиты, может текст поправить»), в плашке — «открыт и без
    согласования»;
  • добавленная опция снимает согласование: «Изменён после согласования»,
    «Что изменилось» с опцией, разделом и суммой, договоры снова закрыты;
    «Что изменилось» сворачивается птичкой, сумма разницы остаётся в шапке;
    расчёт, изменённый после отправки, согласовать нельзя: кнопки нет, есть
    подсказка, «Что изменилось» с отправки и «Отправить снова» у автора;
  • повторная отправка — проверяющий видит только разницу;
  • стоп: кнопка выключена, стоп назван, база не спрашивается;
  • отказ базы: сказано словами, состояние прежнее;
  • отпечаток тот же после восстановления того же расчёта — так его считает
    проверяющий, открывший пресет по коду;
  • колокольчик: проверяющему — «Ждёт согласования», автору — «Расчёт
    согласован»; нажатие открывает пресет на вкладке «Проверка»;
  • вёрстка на 390 и 1440, днём и ночью: блок внутри карточки, поля нажатия
    кнопок не меньше 44 px, кнопки не касаются плашки и друг друга.

  • личный пресет на согласование не уходит: кнопка бледная, подсказка —
    опубликовать, вызов функции отправки говорит словами и базу не трогает;
    после публикации кнопка оживает (19.10.2026).

    python3 check_preset_approval.py
"""
import os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
ШРИФТЫ = (pathlib.Path(__file__).parent / "шрифты_google.css").read_text(encoding="utf-8")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


ВЁРСТКА = """() => {
  const к = document.getElementById('presetChipCard');
  const r = к.getBoundingClientRect(), cs = getComputedStyle(к);
  const внутр = { l: r.left + parseFloat(cs.borderLeftWidth) + parseFloat(cs.paddingLeft),
                  r: r.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight) };
  const н = [];
  if (r.left < 4 || r.right > innerWidth - 4 || r.top < 4 || r.bottom > innerHeight) н.push('карточка вне кадра ' + JSON.stringify([r.left, r.top, r.right, r.bottom].map(Math.round)));
  if (document.documentElement.scrollWidth > innerWidth + 1) н.push('страница шире экрана');
  const блок = к.querySelector('.pc-ap-blk');
  if (!блок) return н;
  const пане = к.querySelector('.pc-pane.on');
  if (пане && пане.scrollWidth > пане.clientWidth + 1) н.push('вкладка «Проверка» шире себя на ' + (пане.scrollWidth - пане.clientWidth) + ' px');
  блок.querySelectorAll('.pc-st, .pc-row button, .pc-hint, .pc-grp, .pc-ap-df li, .pc-ap-sl li').forEach(э => {
    const б = э.getBoundingClientRect();
    if (!б.width) return;
    const имя = (э.getAttribute('data-act') || э.className || э.tagName) + ' «' + (э.innerText || '').trim().slice(0, 18) + '»';
    if (б.left < внутр.l - .5 || б.right > внутр.r + .5) н.push(имя + ' за полем карточки: ' + Math.round(б.left - внутр.l) + '/' + Math.round(внутр.r - б.right));
    if (э.scrollWidth > э.clientWidth + 1 && getComputedStyle(э).overflow !== 'visible') н.push(имя + ' обрезан');
  });
  // Текст кнопок целиком.
  блок.querySelectorAll('.pc-row button').forEach(э => {
    const б = э.getBoundingClientRect(), д = document.createRange(); д.selectNodeContents(э);
    if ([...д.getClientRects()].some(х => х.width > 0 && (х.left < б.left - .5 || х.right > б.right + .5))) н.push('подпись кнопки «' + э.innerText.trim() + '» обрезана');
    const с = getComputedStyle(э, '::before');
    const h = б.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
    if (h < 43.5) н.push('поле нажатия «' + э.innerText.trim() + '» по высоте ' + Math.round(h) + ' px');
  });
  // Зазоры: кнопки — от плашки, подсказки и друг от друга.
  // Соседи по ряду — по горизонтали, ряды между собой — по вертикали.
  const ряды = [...блок.querySelectorAll('.pc-row')];
  ряды.forEach((р, j) => {
    const кн = [...р.querySelectorAll('button')];
    кн.forEach((э, i) => { if (i && э.getBoundingClientRect().left - кн[i - 1].getBoundingClientRect().right < 4) н.push('кнопки ближе 4 px друг к другу'); });
    if (j && р.getBoundingClientRect().top - ряды[j - 1].getBoundingClientRect().bottom < 6) н.push('ряды кнопок ближе 6 px: ' + Math.round(р.getBoundingClientRect().top - ряды[j - 1].getBoundingClientRect().bottom));
  });
  const пл = блок.querySelector('.pc-st'), ряд = блок.querySelector('.pc-row');
  if (пл && ряд && ряд.getBoundingClientRect().top - пл.getBoundingClientRect().bottom < 8) н.push('кнопки прилипли к плашке: ' + Math.round(ряд.getBoundingClientRect().top - пл.getBoundingClientRect().bottom) + ' px');
  const подс = блок.querySelector('.pc-row + .pc-hint');
  if (подс && ряд && подс.getBoundingClientRect().top - ряд.getBoundingClientRect().bottom < 4) н.push('подсказка прилипла к кнопкам');
  return н;
}"""


def вёрстка(стр, н, что):
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {что}: {т}")


# База согласования — по правилам миграций preset_approval и
# preset_approval_two_slots: цену решает редактор, чек-лист — администратор
# или специалист, «за всех» — администратор; согласовать нельзя при открытой
# правке чата; расчёт согласован, когда оба места согласованы одним отпечатком.
ДАННЫЕ = """(код) => {
  const т = window.__ТАБЛИЦЫ;
  т.profiles.push({ id: 'u-ред', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  т.profiles.push({ id: 'u-спец', role: 'specialist', first_name: 'Нина', last_name: 'Офисная' });
  т.preset_messages = [];
  т.preset_approvals = [];
  window.__ВЫЗОВЫ = [];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(Date.now() - 864e5).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  window.__RPC.preset_chat_mark = (а) => { const с = т.preset_messages.find(х => х.id === а.p_id); if (!с) return null; с.review_state = а.p_state; return Object.assign({}, с); };
  const кто = () => { const р = window._sbProfile && window._sbProfile.role;
    return р === 'editor' ? ['u-ред', 'Ольга Проверкина'] : р === 'specialist' ? ['u-спец', 'Нина Офисная'] : р === 'admin' ? ['u-адм', 'Константин Главный'] : ['u-проба', 'Проба Пробная']; };
  const МЕСТА = ['price', 'check'];
  const снять = (с, м) => { с[м + '_by'] = null; с[м + '_name'] = null; с[м + '_at'] = null; с[м + '_print'] = null; };
  window.__RPC.preset_approval_send = (а) => {
    // Медленная база: ответ через __ЖДАТЬ_ОТПРАВКИ мс — экран обязан показать статус сразу.
    if (window.__ЖДАТЬ_ОТПРАВКИ) { const ж = window.__ЖДАТЬ_ОТПРАВКИ; window.__ЖДАТЬ_ОТПРАВКИ = 0;
      return new Promise(r => setTimeout(() => r(window.__RPC.preset_approval_send(а)), ж)); }
    window.__ВЫЗОВЫ.push(['send', JSON.parse(JSON.stringify(а))]);
    if (window.__СБОЙ_СОГЛАСОВАНИЯ) return { __ошибка: 'нет связи' };
    let с = т.preset_approvals.find(х => х.code === а.p_code);
    if (!с) { с = { code: а.p_code }; т.preset_approvals.push(с); }
    Object.assign(с, { state: 'pending', preset_name: а.p_preset, project_name: а.p_project, sent_by: кто()[0], sent_name: кто()[1],
      sent_at: new Date().toISOString(), sent_total: а.p_total, sent_print: а.p_print, sent_snapshot: а.p_snapshot,
      decided_by: null, decided_name: null, decided_at: null, for_all: false });
    МЕСТА.forEach(м => { if (с[м + '_print'] !== а.p_print) снять(с, м); });
    return Object.assign({}, с);
  };
  window.__RPC.preset_approval_decide = (а) => {
    window.__ВЫЗОВЫ.push(['decide', JSON.parse(JSON.stringify(а))]);
    const р = (window._sbProfile || {}).role || '';
    if (['admin', 'editor', 'specialist'].indexOf(р) < 0) return { __ошибка: 'согласуют редактор, администратор и специалист' };
    if (['price', 'check', 'all'].indexOf(а.p_slot) < 0) return { __ошибка: 'неверное место согласования' };
    if (а.p_slot === 'price' && р !== 'editor') return { __ошибка: 'цену согласует редактор' };
    if (а.p_slot === 'check' && ['admin', 'specialist'].indexOf(р) < 0) return { __ошибка: 'чек-лист согласует администратор или специалист' };
    if (а.p_slot === 'all' && р !== 'admin') return { __ошибка: 'согласовать за всех может администратор' };
    if (а.p_state === 'approved' && т.preset_messages.some(м => м.code === а.p_code && м.review_state === 'open')) return { __ошибка: 'есть открытые правки' };
    const с = т.preset_approvals.find(х => х.code === а.p_code);
    if (!с) return { __ошибка: 'расчёт не отправлен на согласование' };
    if (с.state !== 'pending') return { __ошибка: 'расчёт сейчас не ждёт согласования' };
    const мои = а.p_slot === 'all' ? МЕСТА : [а.p_slot];
    Object.assign(с, { decided_by: кто()[0], decided_name: кто()[1], decided_at: new Date().toISOString() });
    if (а.p_state === 'returned') { с.state = 'returned'; с.for_all = false; мои.forEach(м => снять(с, м)); return Object.assign({}, с); }
    с.for_all = а.p_slot === 'all';
    МЕСТА.forEach(м => {
      if (мои.includes(м)) Object.assign(с, { [м + '_by']: кто()[0], [м + '_name']: кто()[1], [м + '_at']: new Date().toISOString(), [м + '_print']: а.p_print });
      else if (с[м + '_print'] !== а.p_print) снять(с, м);
    });
    if (с.price_print === а.p_print && с.check_print === а.p_print) Object.assign(с, { state: 'approved', approved_by: кто()[0], approved_name: кто()[1],
      approved_at: new Date().toISOString(), approved_total: а.p_total, approved_print: а.p_print, approved_snapshot: а.p_snapshot });
    return Object.assign({}, с);
  };
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  _согласование = { код: '', строка: null, грузится: false, когда: 0, ошибка: '', шлём: false };
}"""

СОСТОЯНИЕ = """() => { const к = document.getElementById('presetChipCard'), б = к.querySelector('.pc-ap-blk');
  return { есть: !!б, плашка: б ? (б.querySelector('.pc-st') || {}).innerText || '' : '',
    кнопки: б ? [...б.querySelectorAll('.pc-row button')].map(х => ({ т: х.innerText.trim(), выкл: х.disabled, act: х.getAttribute('data-act') })) : [],
    подсказки: б ? [...б.querySelectorAll('.pc-hint')].map(х => х.innerText.trim()) : [],
    разница: б ? [...б.querySelectorAll('.pc-ap-df li')].map(х => х.innerText.replace(/\\s+/g, ' ').trim()) : [],
    места: б ? [...б.querySelectorAll('.pc-ap-sl li')].map(х => ({ к: х.querySelector('.pc-ap-sl-k').innerText.trim(), в: х.querySelector('.pc-ap-sl-v').innerText.trim(), да: х.classList.contains('pc-ap-sl-ok') })) : [],
    группа: б ? ((б.querySelector('.pc-grp') || {}).innerText || '').replace(/\\s+/g, ' ').trim() : '',
    договор: договорДоступен() }; }"""

МЕНЮ = """() => { обновитьМенюДокумента(); const п = [...document.querySelectorAll('#previewEntityMenu [data-contract]')];
  return п.map(х => ({ закрыт: х.classList.contains('ent-locked'), согл: х.classList.contains('ent-approved'),
    подпись: (х.querySelector('.ent-lock') || {}).textContent || '', видна: getComputedStyle(х.querySelector('.ent-lock')).display !== 'none' })); }"""


def роль(стр, р):
    стр.evaluate("(р) => { window._sbProfile.role = р; _согласование.когда = 0; заполнитьКарточкуЗначка(); }", р)
    стр.wait_for_timeout(200)


def опубликовать_пресет(стр):
    стр.evaluate("""() => { const все = loadAllPresets(), p = все[activePresetId]; if (!p) return;
      p.publishedAs = 'user'; saveAllPresets(все); заполнитьКарточкуЗначка(); }""")
    стр.wait_for_timeout(200)


def начать(бр, порт, ш, в, ночь, опубликовать=True):
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async (ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); document.body.classList.toggle('dark', ночь);
      appSettings.showCheckBadge = true;
      window.__тосты = []; const был = window.showToast; window.showToast = function (т) { window.__тосты.push(String(т)); return был.apply(this, arguments); };
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""", ночь)
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
    if стр.locator("#pcName").count():
        стр.locator("#pcName").press("Enter")
    стр.wait_for_timeout(2600)
    # С 19.10.2026 на согласование уходит только опубликованный пресет —
    # расчёт пробы публикуется сразу после сохранения.
    if опубликовать:
        опубликовать_пресет(стр)
    return стр, ошибки


def открытьПроверку(стр):
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#pcTab-c").click(); стр.wait_for_timeout(450)


def нажать(стр, act):
    стр.locator(f"#presetChipCard .pc-ap-blk [data-act='{act}']").click(); стр.wait_for_timeout(500)


def прогон(бр, порт, ш, в, ночь, полный):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = начать(бр, порт, ш, в, ночь, опубликовать=False)
    # Личный пресет: кнопка отправки бледная, подсказка — опубликовать
    # (Константин, 19.10.2026: «Личный пресет на согласование отправить нельзя…
    # Когда опубликует, то становится активной»).
    открытьПроверку(стр)
    лч = стр.evaluate("""() => { const к = document.querySelector('#presetChipCard .pc-ap-blk [data-act="ap-send"]');
      const п = document.querySelector('#presetChipCard .pc-ap-blk .pc-ap-why');
      return { есть: !!к, выкл: к ? к.disabled : null, подсказка: п ? п.textContent : '', прозр: к ? +getComputedStyle(к).opacity : 1 }; }""")
    if not лч["есть"] or not лч["выкл"] or "опубликуйте" not in лч["подсказка"] or лч["прозр"] > .7:
        плохо(f"{н} личный пресет: кнопка отправки {лч}")
    стр.evaluate("() => { window.__ВЫЗ_ДО = (window.__ВЫЗОВЫ || []).length; отправитьНаСогласование(); }"); стр.wait_for_timeout(300)
    if стр.evaluate("() => (window.__ВЫЗОВЫ || []).length !== window.__ВЫЗ_ДО") or not any("опубликуйте" in т for т in стр.evaluate("() => window.__тосты.slice(-2)")):
        плохо(f"{н} личный пресет ушёл на согласование или отказ без слов")
    # Личный пресет, который уже прошёл согласование (отправлен до правила о
    # публикации), а потом изменён: повторная отправка открыта — публикация
    # нужна только для первой (Константин, 20.10.2026: «Активных правок нет,
    # но на повторное согласование не даёт отправить»).
    пв = стр.evaluate("""() => { const о = пресетКарточки(); if (!о || !о.код) return { кода: false };
      const было = _согласование, с = составДляСогласования();
      _согласование = { код: String(о.код), строка: { code: String(о.код), state: 'approved', approved_print: 'прежний',
        approved_snapshot: с, approved_at: new Date(Date.now() - 864e5).toISOString(), approved_total: 1 }, грузится: false, когда: Date.now(), ошибка: '', шлём: false };
      заполнитьКарточкуЗначка();
      const к = document.querySelector('#presetChipCard .pc-ap-blk [data-act="ap-send"]');
      const п = document.querySelector('#presetChipCard .pc-ap-blk .pc-ap-why');
      const р = { кода: true, вид: о.вид, есть: !!к, текст: к ? к.textContent : '', подсказка: п ? п.textContent : '' };
      _согласование = было; заполнитьКарточкуЗначка(); return р; }""")
    if not пв["кода"]:
        плохо(f"{н} личному пресету не выдан код — повторную отправку не проверить")
    elif пв["вид"] != "own" or not пв["есть"] or "повторное" not in пв["текст"] or "опубликуйте" in пв["подсказка"]:
        плохо(f"{н} личный согласованный пресет: повторную отправку держит публикация {пв}")
    опубликовать_пресет(стр)
    лч = стр.evaluate("""() => { const к = document.querySelector('#presetChipCard .pc-ap-blk [data-act="ap-send"]');
      const п = document.querySelector('#presetChipCard .pc-ap-blk .pc-ap-why');
      return { выкл: к ? к.disabled : null, подсказка: п ? п.textContent : '' }; }""")
    # Стоп в учебном расчёте до ДАННЫХ может быть — тогда кнопку держит он, а
    # не публикация; важно, что подсказка о публикации ушла.
    if "опубликуйте" in лч["подсказка"] or (лч["выкл"] and not лч["подсказка"]):
        плохо(f"{н} после публикации кнопку отправки всё ещё держит публикация: {лч}")
    стр.locator("#presetChipCard .pc-x").click(); стр.wait_for_timeout(300)
    шрифт = стр.evaluate("""() => { const и = document.createElement('span'); и.style.cssText = 'position:absolute;visibility:hidden;font-size:40px;white-space:nowrap'; и.textContent = 'Согласование расчёта';
      document.body.appendChild(и); const шир = ш => { и.style.fontFamily = ш; return и.getBoundingClientRect().width; };
      const д = Math.abs(шир("'Geologica',monospace") - шир('monospace')) > .5; и.remove(); return д; }""")
    if not шрифт:
        плохо(f"{н} Geologica не легла — ширины меряются подменным шрифтом"); стр.close(); return
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    # Стопов в учебном расчёте быть не должно — иначе отправку не проверить.
    стр.evaluate("""() => { window.__проверкаБыла = проверкаПоЧекЛисту;
      window.проверкаПоЧекЛисту = function () { const п = window.__проверкаБыла.apply(this, arguments);
        п.замечания = п.замечания.filter(з => !з.стоп);
        if (window.__СТОП) п.замечания.unshift({ т: 'Добавить водосточную систему', раздел: 'roof', стоп: true, эл: '' });
        return п; }; }""")
    открытьПроверку(стр)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not с["есть"]:
        плохо(f"{н} во вкладке «Проверка» нет блока согласования"); стр.close(); return
    if "Не согласован" not in с["плашка"] or [к["т"] for к in с["кнопки"]] != ["Отправить на согласование"] or с["кнопки"][0]["выкл"]:
        плохо(f"{н} автор без согласования: {с}")
    if с["договор"]:
        плохо(f"{н} договор открыт менеджеру без согласования")
    меню = стр.evaluate(МЕНЮ)
    if not меню or not all(п["закрыт"] and п["подпись"] == "После согласования спецификации" for п in меню):
        плохо(f"{н} пункты договоров в окне печати не закрыты до согласования: {меню}")
    вёрстка(стр, н, "«Не согласован»")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-new-{ш}{'-n' if ночь else ''}.png"))
    if not полный:
        if ошибки: плохо(f"{н} ошибки страницы: {ошибки[:3]}")
        стр.close(); return

    # ── стоп держит отправку ──
    стр.evaluate("() => { window.__СТОП = true; заполнитьКарточкуЗначка(); }"); стр.wait_for_timeout(200)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not с["кнопки"] or not с["кнопки"][0]["выкл"] or not any("Сначала снимите стоп: «Добавить водосточную систему»" in п for п in с["подсказки"]):
        плохо(f"{н} стоп не выключил отправку или не назван: {с}")
    вёрстка(стр, н, "отправка со стопом")
    стр.evaluate("() => отправитьНаСогласование()"); стр.wait_for_timeout(300)
    if стр.evaluate("() => window.__ВЫЗОВЫ.length"):
        плохо(f"{н} со стопом база спрошена: {стр.evaluate('() => window.__ВЫЗОВЫ')}")
    стр.evaluate("() => { window.__СТОП = false; заполнитьКарточкуЗначка(); }"); стр.wait_for_timeout(200)

    # ── отказ базы ──
    стр.evaluate("() => { window.__СБОЙ_СОГЛАСОВАНИЯ = true; }")
    нажать(стр, "ap-send")
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Не согласован" not in с["плашка"] or not any("Не удалось отправить на согласование" in т for т in стр.evaluate("() => window.__тосты")) or с["кнопки"][0]["выкл"]:
        плохо(f"{н} отказ базы при отправке: {с}")
    стр.evaluate("() => { window.__СБОЙ_СОГЛАСОВАНИЯ = false; window.__ВЫЗОВЫ = []; }")

    # ── отправка: статус сразу, база за кулисами, строка в журнале пресета сразу ──
    стр.evaluate("(код) => { window.__ЖДАТЬ_ОТПРАВКИ = 1500; _журналПресета = { код: String(код), события: [], ошибка: '', грузится: false, когда: Date.now(), заранее: false }; }", код)
    стр.locator("#presetChipCard .pc-ap-blk [data-act='ap-send']").click(); стр.wait_for_timeout(150)
    с = стр.evaluate(СОСТОЯНИЕ)
    сразу = стр.evaluate("(код) => ({ вБазе: window.__ТАБЛИЦЫ.preset_approvals.some(х => х.code === код), журнал: (_журналПресета.события || []).map(е => е.event_type) })", код)
    if "Ждёт согласования" not in с["плашка"] or с["кнопки"] or сразу["вБазе"] or сразу["журнал"][:1] != ["approval_sent"]:
        плохо(f"{н} отправка не сразу: плашка «{с['плашка']}», кнопки {с['кнопки']}, {сразу}")
    стр.wait_for_timeout(1700)
    о = стр.evaluate("""(код) => { const в = (window.__ВЫЗОВЫ.find(х => х[0] === 'send') || [])[1] || {}, с = составДляСогласования();
      return { код: в.p_code, отпечаток: в.p_print === отпечатокСостава(с), сумма: в.p_total, соСкидкой: с.соСкидкой, снимок: !!(в.p_snapshot && в.p_snapshot.строки && в.p_snapshot.строки.length),
        журнал: (window.__ТАБЛИЦЫ.events || []).some(е => е.event_type === 'approval_sent' && е.details && String(е.details.presetCode) === String(код)) }; }""", код)
    if о["код"] != код or not о["отпечаток"] or о["сумма"] != о["соСкидкой"] or not о["снимок"] or not о["журнал"]:
        плохо(f"{н} отправка на согласование: {о}")
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Ждёт согласования" not in с["плашка"] or с["кнопки"] or с["места"] != [{"к": "Цена", "в": "ждёт", "да": False}, {"к": "Чек-лист", "в": "ждёт", "да": False}]:
        плохо(f"{н} после отправки: {с}")
    вёрстка(стр, н, "ждёт согласования, автор")

    # ── проверяющий: открытая правка держит «Согласовать» ──
    роль(стр, "editor")
    стр.evaluate("""(код) => { window.__ТАБЛИЦЫ.preset_messages.push({ id: 'aaaaaaaa-1111-4111-8111-111111111111', code: код, author_id: 'u-ред', author_name: 'Ольга Проверкина',
        body: 'Вальмовую кровлю убрать — у проекта двускатная.', reply_to: null, attachments: [], review_state: 'open', created_at: new Date().toISOString() });
      _чат.когда = 0; }""", код)
    стр.evaluate("() => загрузитьЧат(true)"); стр.wait_for_timeout(500)
    с = стр.evaluate(СОСТОЯНИЕ)
    кн = {к["act"]: к for к in с["кнопки"]}
    if "Ждёт согласования" not in с["плашка"] or set(кн) != {"ap-back", "ap-ok"} or кн["ap-ok"]["т"] != "Согласовать цену" or not кн["ap-ok"]["выкл"] or кн["ap-back"]["выкл"] or not any("открытых правок не останется" in п for п in с["подсказки"]):
        плохо(f"{н} проверяющий при открытой правке: {с}")
    вёрстка(стр, н, "проверяющий, открытая правка")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-review-{ш}{'-n' if ночь else ''}.png"))
    было = стр.evaluate("() => window.__ВЫЗОВЫ.length")
    стр.evaluate("() => решитьСогласование('approved', 'price')"); стр.wait_for_timeout(300)
    if стр.evaluate("() => window.__ВЫЗОВЫ.length") != было:
        плохо(f"{н} «Согласовать» при открытой правке спросило базу")
    нажать(стр, "ap-back")
    с = стр.evaluate(СОСТОЯНИЕ)
    # Проверка идёт на своём пресете под ролью администратора: с 18.10.2026
    # администратор отправляет свой расчёт тем же путём, что менеджер, поэтому
    # после возврата у него «Отправить снова», а не «Ждёт повторной отправки».
    if "Возвращён с правками" not in с["плашка"] or "Ждёт повторной отправки" in с["плашка"] \
            or [к.get("т") for к in с["кнопки"]] != ["Отправить снова"]:
        плохо(f"{н} проверяющий после возврата на своём пресете: {с}")

    # ── автор после возврата ──
    роль(стр, "manager")
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Возвращён с правками" not in с["плашка"] or "Открытых правок: 1" not in с["плашка"] or [к["т"] for к in с["кнопки"]] != ["Отправить снова"]:
        плохо(f"{н} автор после возврата: {с}")
    вёрстка(стр, н, "возвращён с правками")
    стр.locator("#presetChipCard .pc-pr-box").click(); стр.wait_for_timeout(400)
    нажать(стр, "ap-send")

    # ── согласование ──
    роль(стр, "editor")
    с = стр.evaluate(СОСТОЯНИЕ)
    кн = {к["act"]: к for к in с["кнопки"]}
    if кн.get("ap-ok", {}).get("выкл", True):
        плохо(f"{н} «Согласовать» выключено без открытых правок: {с}")
    нажать(стр, "ap-ok")
    а = стр.evaluate("(код) => window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код)", код)
    if not а or а.get("state") != "pending" or а.get("price_name") != "Ольга Проверкина" or а.get("check_by"):
        плохо(f"{н} согласование цены: {а}")
    if not any(т == "Цена согласована — ждёт чек-листа" for т in стр.evaluate("() => window.__тосты")):
        плохо(f"{н} тост после согласования цены: {стр.evaluate('() => window.__тосты.slice(-3)')}")
    с = стр.evaluate(СОСТОЯНИЕ)
    if [к["act"] for к in с["кнопки"]] != ["ap-back"] or not any("Цену вы согласовали" in п for п in с["подсказки"]) \
            or not (с["места"] and с["места"][0]["да"] and с["места"][0]["в"].startswith("Ольга П.") and not с["места"][1]["да"]):
        плохо(f"{н} редактор после своего согласования: {с}")
    вёрстка(стр, н, "редактор согласовал цену")
    роль(стр, "manager")
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Ждёт согласования" not in с["плашка"] or с["договор"]:
        плохо(f"{н} одно согласование цены открыло договор или сняло ожидание: {с}")
    стр.evaluate("(код) => { window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код).sent_by = 'u-проба'; }", код)
    у = стр.evaluate("""async () => { await собратьУведомления(); return _уведомления.filter(у => у.согласование).map(у => у.текст.replace(/<[^>]+>/g, '')); }""")
    # Каждый шаг круга — своя строка: отправка и согласованная цена, ни одна
    # не затирает другую (Константин 18.10.2026: «старое затирает»).
    if [т.split(":")[0] for т in у] != ["Цена согласована", "Отправлен на согласование"]:
        плохо(f"{н} колокольчик автора без половины пути: {у}")
    # Специалист: договоры ему открыты и без согласования; чек-лист — его место.
    роль(стр, "specialist")
    с = стр.evaluate(СОСТОЯНИЕ)
    кн = {к["act"]: к for к in с["кнопки"]}
    if кн.get("ap-ok", {}).get("т") != "Согласовать чек-лист" or "ap-all" in кн or not с["договор"]:
        плохо(f"{н} специалист перед согласованием чек-листа: {с}")
    if not стр.evaluate(МЕНЮ) or any(п["закрыт"] for п in стр.evaluate(МЕНЮ)):
        плохо(f"{н} специалист: пункты комплекта в окне печати закрыты — {стр.evaluate(МЕНЮ)}")
    вёрстка(стр, н, "специалист")
    # Расчёт поменяли после отправки: согласовывать нечего, пока его не
    # отправят заново (Константин, 18.10.2026: «нажимаю согласовать чек-лист,
    # пишет согласован. Но статус тут не меняется»). Кнопки «Согласовать»
    # нет, есть подсказка и «Что изменилось» с отправки; вызов решения базу
    # не спрашивает и тоста об успехе не даёт; у автора — «Отправить снова».
    оп2 = стр.evaluate("""() => { const о = OPTIONS.find(x => { const л = document.getElementById('lbl_' + x.id);
        return !x.included && !checkedOptions[x.id] && ценаОпцииВИтог(x) > 0 && л && л.dataset.blocked !== '1' && л.getClientRects().length; });
      if (!о) return null; toggleOpt(о.id); calc(); заполнитьКарточкуЗначка(); return о.id; }""")
    стр.wait_for_timeout(300)
    if оп2:
        с = стр.evaluate(СОСТОЯНИЕ)
        было = стр.evaluate("() => window.__ВЫЗОВЫ.length")
        стр.evaluate("() => { window.__тосты = []; решитьСогласование('approved', 'check'); }"); стр.wait_for_timeout(400)
        после = стр.evaluate("(код) => ({ вызовов: window.__ВЫЗОВЫ.length, тосты: window.__тосты.slice(), чек: (window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код) || {}).check_by || null })", код)
        if "ap-ok" in [к["act"] for к in с["кнопки"]] or not any("изменили после отправки" in п for п in с["подсказки"]) or not с["разница"] \
                or "Отправить снова" not in [к["т"] for к in с["кнопки"]] or после["вызовов"] != было or после["чек"] \
                or any("согласован" in т.lower() and "изменили" not in т for т in после["тосты"]):
            плохо(f"{н} расчёт изменён после отправки: {с}, после попытки согласовать {после}")
        вёрстка(стр, н, "изменён после отправки")
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"approval-stale-{ш}{'-n' if ночь else ''}.png"))
        стр.evaluate("(ид) => { toggleOpt(ид); calc(); заполнитьКарточкуЗначка(); }", оп2); стр.wait_for_timeout(300)
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-half-{ш}{'-n' if ночь else ''}.png"))
    нажать(стр, "ap-ok")
    а = стр.evaluate("(код) => window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код)", код)
    if not а or а.get("state") != "approved" or а.get("approved_print") != стр.evaluate("() => отпечатокСостава(составДляСогласования())"):
        плохо(f"{н} согласование не запомнило отпечаток: {а}")
    роль(стр, "manager")
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Согласовано" not in с["плашка"] or "Договор можно печатать" not in с["плашка"] or not с["договор"] \
            or "цена — Ольга П., чек-лист — Нина О." not in с["плашка"]:
        плохо(f"{н} автор после согласования: {с}")
    меню = стр.evaluate(МЕНЮ)
    if not меню or not all(not п["закрыт"] and п["согл"] and re.match(r"^Согласован \d\d\.\d\d$", п["подпись"]) and п["видна"] for п in меню):
        плохо(f"{н} договоры в окне печати после согласования: {меню}")
    вёрстка(стр, н, "согласовано")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-ok-{ш}{'-n' if ночь else ''}.png"))

    # ── реквизиты согласования не снимают ──
    стр.evaluate("""() => { const п = document.getElementById('clientName');
      if (п) { п.value = 'Иванов Иван Иванович'; п.dispatchEvent(new Event('input', { bubbles: true })); } calc(); }""")
    стр.wait_for_timeout(300)
    if not стр.evaluate("() => договорДоступен()"):
        плохо(f"{н} реквизиты сняли согласование")

    # ── добавленная опция снимает согласование ──
    оп = стр.evaluate("""() => { const о = OPTIONS.find(x => { const л = document.getElementById('lbl_' + x.id);
        return !x.included && !checkedOptions[x.id] && ценаОпцииВИтог(x) > 0 && л && л.dataset.blocked !== '1' && л.getClientRects().length; });
      if (!о) return null; toggleOpt(о.id); calc(); return { имя: о.name, раздел: имяРаздела(о.section), цена: ценаОпцииВИтог(о) }; }""")
    стр.wait_for_timeout(300)
    if not оп:
        плохо(f"{н} не нашлась опция с ценой, чтобы изменить расчёт")
    else:
        стр.evaluate("() => заполнитьКарточкуЗначка()")
        с = стр.evaluate(СОСТОЯНИЕ)
        if "Изменён после согласования" not in с["плашка"] or с["договор"] or not any(("Добавлено: " + оп["имя"]) in р and оп["раздел"] in р for р in с["разница"]) \
                or "ИЗМЕНИЛОСЬ С" not in с["группа"].upper() or "+" not in с["группа"] \
                or [к["т"] for к in с["кнопки"]] != ["Отправить на повторное согласование"]:
            плохо(f"{н} изменённый после согласования: {с} (опция {оп})")
        меню = стр.evaluate(МЕНЮ)
        if not all(п["закрыт"] and п["подпись"] == "После согласования спецификации" for п in меню):
            плохо(f"{н} изменённый расчёт не закрыл договоры: {меню}")
        вёрстка(стр, н, "изменён после согласования")
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"approval-changed-{ш}{'-n' if ночь else ''}.png"))
        # «Что изменилось» сворачивается птичкой (18.10.2026): строки уходят,
        # шапка с суммой разницы остаётся; выбор помнится; второе нажатие
        # разворачивает.
        стр.evaluate("() => { try { localStorage.removeItem('banya_ap_diff_folded'); } catch (e) {} _разницаСвёрнута = false; заполнитьКарточкуЗначка(); }")
        if not стр.locator("#presetChipCard [data-act='ap-diff-fold']").count():
            плохо(f"{н} нет птички «Что изменилось» — блок не показан"); стр.close(); return
        стр.locator("#presetChipCard [data-act='ap-diff-fold']").click(); стр.wait_for_timeout(300)
        с2 = стр.evaluate(СОСТОЯНИЕ)
        птичка = стр.evaluate("() => { const б = document.querySelector('#presetChipCard [data-act=\"ap-diff-fold\"]'); return б ? { раскрыт: б.getAttribute('aria-expanded'), фокус: document.activeElement === б } : null; }")
        помнит = стр.evaluate("() => { try { return localStorage.getItem('banya_ap_diff_folded'); } catch (e) { return null; } }")
        if с2["разница"] or "ИЗМЕНИЛОСЬ С" not in с2["группа"].upper() or "+" not in с2["группа"] or not птичка or птичка["раскрыт"] != "false" or not птичка["фокус"] or помнит != "1":
            плохо(f"{н} свёрнутое «Что изменилось»: {с2['разница']}, шапка «{с2['группа']}», птичка {птичка}, помнит {помнит}")
        вёрстка(стр, н, "«Что изменилось» свёрнуто")
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"approval-diff-folded-{ш}{'-n' if ночь else ''}.png"))
        стр.locator("#presetChipCard [data-act='ap-diff-fold']").click(); стр.wait_for_timeout(300)
        if not стр.evaluate(СОСТОЯНИЕ)["разница"]:
            плохо(f"{н} второе нажатие птички не развернуло «Что изменилось»")
        # Повторная отправка — проверяющий видит разницу с прошлым согласованием.
        нажать(стр, "ap-send")
        роль(стр, "editor")
        с = стр.evaluate(СОСТОЯНИЕ)
        if "Ждёт согласования" not in с["плашка"] or not any(("Добавлено: " + оп["имя"]) in р for р in с["разница"]):
            плохо(f"{н} проверяющий при повторной отправке не видит разницы: {с}")
        вёрстка(стр, н, "повторное согласование")
        роль(стр, "admin")
        с = стр.evaluate(СОСТОЯНИЕ)
        кн = {к["act"]: к for к in с["кнопки"]}
        if кн.get("ap-ok", {}).get("т") != "Согласовать чек-лист" or кн.get("ap-all", {}).get("т") != "Согласовать за всех" or кн["ap-all"]["выкл"]:
            плохо(f"{н} администратор: нет «Согласовать за всех»: {с}")
        вёрстка(стр, н, "администратор, «за всех»")
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"approval-admin-{ш}{'-n' if ночь else ''}.png"))
        нажать(стр, "ap-all")
        а = стр.evaluate("(код) => window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код)", код)
        if not а or а.get("state") != "approved" or not а.get("for_all") or а.get("price_name") != "Константин Главный":
            плохо(f"{н} «за всех» не согласовало оба места: {а}")
        роль(стр, "manager")
        с = стр.evaluate(СОСТОЯНИЕ)
        if "за всех — Константин Г." not in с["плашка"] or not с["договор"]:
            плохо(f"{н} автор после «за всех»: {с}")

    # ── отпечаток тот же у восстановленного того же расчёта ──
    д = стр.evaluate("""async () => { const до = отпечатокСостава(составДляСогласования());
      _идётВосстановление++; restoreState(JSON.parse(JSON.stringify(collectState()))); await new Promise(r => setTimeout(r, 900)); _идётВосстановление--; calc();
      return { до, после: отпечатокСостава(составДляСогласования()) }; }""")
    if д["до"] != д["после"]:
        плохо(f"{н} отпечаток расчёта меняется от восстановления того же состояния: {д}")

    # ── колокольчик ──
    # Проверяющий и автор здесь — один вход; своё отправленное колокольчик не
    # показывает, поэтому отправителем ставится другой человек.
    роль(стр, "editor")
    стр.evaluate("(код) => { const а = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код); Object.assign(а, { state: 'pending', sent_by: 'u-автор', sent_name: 'Пётр Автор', price_by: null, price_print: null, check_by: null, check_print: null, for_all: false }); }", код)
    у = стр.evaluate("""async () => { await собратьУведомления(); return _уведомления.filter(у => у.согласование).map(у => у.текст.replace(/<[^>]+>/g, '') + ' · ' + у.автор); }""")
    if not any(т.startswith("Ждёт согласования") and т.endswith("Пётр Автор") for т in у):
        плохо(f"{н} колокольчик проверяющего без «Ждёт согласования» с именем автора: {у}")
    роль(стр, "specialist")
    стр.evaluate("(код) => { const а = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код); Object.assign(а, { state: 'approved', approved_at: new Date().toISOString(), decided_by: 'u-ред', decided_name: 'Ольга Проверкина', decided_at: new Date().toISOString() }); }", код)
    у = стр.evaluate("""async () => { await собратьУведомления(); return _уведомления.filter(у => у.согласование).map(у => у.текст.replace(/<[^>]+>/g, '') + ' · ' + у.автор); }""")
    if not any(т.startswith("Расчёт согласован") and т.endswith("Ольга Проверкина") for т in у):
        плохо(f"{н} колокольчик специалиста без статуса чужого согласованного расчёта: {у}")
    стр.evaluate("(код) => { const а = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код); а.sent_by = 'u-проба'; }", код)
    роль(стр, "manager")
    стр.evaluate("(код) => { const а = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === код); Object.assign(а, { state: 'approved', decided_name: 'Ольга Проверкина', decided_at: new Date().toISOString() }); }", код)
    у = стр.evaluate("""async () => { await собратьУведомления(); return _уведомления.filter(у => у.согласование).map(у => ({ т: у.текст.replace(/<[^>]+>/g, ''), код: у.код })); }""")
    if not any(х["т"].startswith("Расчёт согласован") and х["код"] == код for х in у):
        плохо(f"{н} колокольчик автора без «Расчёт согласован»: {у}")
    стр.evaluate("() => { закрытьКарточкуЗначка(); _пкВкладка = 'p'; }")
    стр.evaluate("(код) => открытьСогласование(код)", код); стр.wait_for_timeout(1500)
    о = стр.evaluate("() => ({ открыта: document.getElementById('presetChipCard').classList.contains('show'), вкладка: _пкВкладка })")
    if not о["открыта"] or о["вкладка"] != "c":
        плохо(f"{н} колокольчик не открыл пресет на «Проверке»: {о}")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, False, True)
                прогон(бр, порт, 390, 844, False, True)
                прогон(бр, порт, 390, 844, True, False)
                прогон(бр, порт, 1440, 900, True, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: два места — цена у редактора, чек-лист у специалиста или администратора, «за всех» у администратора, одно место договор не открывает; "
          "отправка с отпечатком и снимком, стоп и отказ базы, возврат с правками и «Согласовать» за открытыми правками, "
          "договоры открываются согласованием и закрываются изменением суммы, реквизиты его не снимают, разница при повторном согласовании, "
          "колокольчик обеим сторонам, вёрстка на 390 и 1440 днём и ночью.")


if __name__ == "__main__":
    главная()
