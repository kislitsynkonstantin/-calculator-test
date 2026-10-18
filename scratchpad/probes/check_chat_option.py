#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Опция в чат: значок у строки расчёта, слепок в чате и значок того, что с ней сейчас.

Константин 18.10.2026, макет mockups/option-to-chat-v1.html: «Да, как в
макете. Все как тут предложил делай»: опция ложится над полем ввода, как
файл; снятая галочка — то же, что удалена; изменение — цена, название,
количество, подарок; до 10 в сообщении; значок у опции, что уже над полем,
залит.

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • значок «В чат» стоит сразу после подарка у каждой видимой строки с
    подарком — каталожной, «Включено в базу» и своей; на телефоне — в
    столбце звезды на одной линии с подарком, при названии в одну строку и
    в две; пока у расчёта нет чата (не сохранён), значков нет;
  • нажатие кладёт опцию над полем чата и открывает мини-окно на «Чате»;
    значок залит; второе нажатие не кладёт её второй раз и говорит словами;
  • отправка: в ленте карточки опций над текстом, в базе — слепок (ключ,
    название, раздел, цена, время), поле и строка над ним пусты, значки
    больше не залиты;
  • значок карточки: «не изменилась»; подарок — «изменилась» и подсказка
    «Сейчас в подарок.»; снятая галочка — «удалена» и «сняли с расчёта»;
    удалённая своя позиция — «удалена»; вернули как было — снова «не
    изменилась»;
  • нажатие на карточку ведёт к строке и подсвечивает её; у снятой — ещё и
    слова «Опцию сняли с расчёта»; у удалённой — только слова;
  • отправленное только с опцией, без текста, уходит;
  • вёрстка на 390 и 1440, днём и ночью: карточки и строки над полем в поле
    мини-окна, поля нажатия значка, «к опции» и креста не меньше 44 px по
    высоте, подсказка не вылезает за ленту.

    python3 check_chat_option.py
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


ДАННЫЕ = """(код) => {
  const т = window.__ТАБЛИЦЫ, д = Date.now();
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  т.preset_messages = [{ id: 'c0000000-0000-4000-8000-000000000001', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина',
    body: 'Посмотри фанеру и воск, пожалуйста.', reply_to: null, review_state: null, kind: 'msg', attachments: [], created_at: new Date(д - 600e3).toISOString() }];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
}"""

# Значок «В чат» — сразу после подарка в каждой видимой строке.
СТРОКИ = """() => { const н = [], строки = [...document.querySelectorAll('.opt-item')].filter(р => р.getClientRects().length);
  let с = 0;
  строки.forEach(р => { const г = р.querySelector('.opt-gift-btn'); if (!г || !г.getClientRects().length) return; с++;
    const сл = г.nextElementSibling;
    if (!сл || !сл.classList.contains('opt-chat-btn')) н.push(р.id + ': после подарка не «В чат»');
    else if (!сл.getClientRects().length) н.push(р.id + ': «В чат» скрыт');
    else { const а = г.getBoundingClientRect(), б = сл.getBoundingClientRect();
      // Телефон: «В чат» — в столбце звезды, на одной линии с подарком
      // (Константин 18.10.2026: «Вертикально кнопка убегает к звезде» — при
      // отсчёте от верха строки значок у названия в две строки вставал выше
      // ряда значков, у названия в одну — ниже). Ряд цены не переносится.
      const з = р.querySelector('.opt-star-btn'), зб = з && з.getClientRects().length ? з.getBoundingClientRect() : null;
      if (innerWidth <= 600 && зб) {
        if (Math.abs((зб.left + зб.right) / 2 - (б.left + б.right) / 2) > 1.5) н.push(р.id + ': «В чат» не в столбце звезды');
        if (Math.abs((а.top + а.bottom) / 2 - (б.top + б.bottom) / 2) > 1.5) н.push(р.id + ': «В чат» не на одной линии с подарком: ' + Math.round((б.top + б.bottom) / 2 - (а.top + а.bottom) / 2) + ' px');
        // Коробки у названия в одну строку заходят друг под друга на 4 px;
        // мерятся рисунки: между ними не меньше 8 px.
        const рз = з.querySelector('svg').getBoundingClientRect(), рч = сл.querySelector('svg').getBoundingClientRect();
        if (рч.top - рз.bottom < 8) н.push(р.id + ': «В чат» вплотную к звезде: ' + Math.round(рч.top - рз.bottom) + ' px');
        if (б.right > р.getBoundingClientRect().right + .5 || б.bottom > р.getBoundingClientRect().bottom + .5) н.push(р.id + ': «В чат» за строкой');
        // «В чат» стоит вне ряда значков — ряд он не раздвигает.
        if (getComputedStyle(сл).position !== 'absolute') н.push(р.id + ': «В чат» в ряду значков на телефоне');
      } else {
        if (Math.abs((а.top + а.bottom) / 2 - (б.top + б.bottom) / 2) > 1.5) н.push(р.id + ': «В чат» не на одной линии с подарком');
        if (б.left - а.right < 2) н.push(р.id + ': «В чат» прилип к подарку');
      } } });
  return { строк: с, н }; }"""

КАРТОЧКИ = """() => [...document.querySelectorAll('#presetChipCard .pc-choc')].map(к => ({
  имя: (к.querySelector('.pc-choc-n') || {}).textContent || '', раздел: (к.querySelector('.pc-choc-s') || {}).textContent || '',
  цена: ((к.querySelector('.pc-choc-p > span') || {}).textContent) || '',
  вид: к.classList.contains('pc-choc-del') ? 'del' : к.classList.contains('pc-choc-ch') ? 'ch' : 'same',
  подсказка: (к.querySelector('.pc-choc-tip') || {}).textContent || '', метка: (к.querySelector('.pc-choc-st') || {}).getAttribute('aria-label') || '' }))"""

ВЁРСТКА = """() => { const к = document.getElementById('presetChipCard'), r = к.getBoundingClientRect(), cs = getComputedStyle(к);
  const л = r.left + parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth), п = r.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
  const лента = к.querySelector('#pcChatList'), лр = лента && лента.getBoundingClientRect(), н = [];
  к.querySelectorAll('.pc-choc, .pc-chopi, .pc-choc-tip').forEach(э => { const б = э.getBoundingClientRect(); if (!б.width) return;
    if (лр && лента.contains(э) && (б.bottom < лр.top || б.top > лр.bottom)) return;
    if (б.left < л - .5 || б.right > п + .5) н.push((э.className || '') + ' за полем карточки: ' + Math.round(б.left - л) + '/' + Math.round(п - б.right)); });
  к.querySelectorAll('.pc-choc-st, .pc-choc-go, .pc-chopi button').forEach(э => { const б = э.getBoundingClientRect(); if (!б.width) return;
    if (лр && лента.contains(э) && (б.bottom < лр.top || б.top > лр.bottom)) return;
    const с = getComputedStyle(э, '::before'); const h = б.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
    const w = б.width - (parseFloat(с.left) || 0) - (parseFloat(с.right) || 0);
    if (h < 43.5) н.push('поле нажатия ' + э.className + ' по высоте ' + Math.round(h) + ' px');
    if (w < 37.5) н.push('поле нажатия ' + э.className + ' по ширине ' + Math.round(w) + ' px'); });
  // Имя в карточке не налезает на значок справа.
  к.querySelectorAll('.pc-choc').forEach(о => { const и = о.querySelector('.pc-choc-n'), з = о.querySelector('.pc-choc-st');
    if (и && з && и.getBoundingClientRect().right > з.getBoundingClientRect().left - 2) н.push('название опции налезает на значок'); });
  if (лента && лента.scrollWidth > лента.clientWidth + 1) н.push('лента шире себя');
  return н; }"""


def вёрстка(стр, н, что):
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {что}: {т}")
    ч.НАХОДКИ.clear()
    ч.вёрстка(стр, н, что)
    for т in ч.НАХОДКИ:
        плохо(т)
    ч.НАХОДКИ.clear()


def нажать_в_чат(стр, ид):
    стр.evaluate("(ид) => { const б = document.getElementById('tochat_' + ид); б.scrollIntoView({ block: 'center' }); }", ид)
    стр.wait_for_timeout(200)
    стр.locator(f"#tochat_{ид}").click(); стр.wait_for_timeout(500)


def прогон(бр, порт, ш, в, ночь, полный):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    # До сохранения у расчёта нет чата — значков «В чат» нет.
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ч.ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    видно = стр.evaluate("() => [...document.querySelectorAll('.opt-chat-btn')].filter(б => б.getClientRects().length).length")
    if видно:
        плохо(f"{н} у несохранённого расчёта видно значков «В чат»: {видно}")
    стр.close()

    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    # Своя позиция — «Обработка торцов воском».
    стр.evaluate("""() => { const к = SECTIONS[0].key; toggleAddForm(к, true);
      document.getElementById('addName_' + к).value = 'Обработка торцов воском'; document.getElementById('addPrice_' + к).value = '6500';
      confirmAddOpt(к); }""")
    стр.wait_for_timeout(400)
    с = стр.evaluate(СТРОКИ)
    if not с["строк"] or с["н"]:
        плохо(f"{н} значок «В чат» в строках: {с}")
    # Опции для пробы: платная отмеченная, «Включено в базу» и своя.
    ид = стр.evaluate("""() => { const видна = id => { const э = document.getElementById('lbl_' + id); return э && э.getClientRects().length; };
      const плат = OPTIONS.find(o => !o.included && checkedOptions[o.id] && ценаОпцииВИтог(o) > 0 && !giftedOpts.has(o.id) && видна(o.id) && document.getElementById('tochat_' + o.id))
        || OPTIONS.find(o => { const л = document.getElementById('lbl_' + o.id); if (o.included || checkedOptions[o.id] || !(ценаОпцииВИтог(o) > 0) || !л || !л.getClientRects().length || л.dataset.blocked === '1') return false;
             toggleOpt(o.id); calc(); return !!checkedOptions[o.id] && !!document.getElementById('tochat_' + o.id); });
      const баз = OPTIONS.find(o => o.included && видна(o.id) && document.getElementById('tochat_' + o.id));
      const свой = 'custom_' + getCustomOpts(SECTIONS[0].key).slice(-1)[0].id;
      return { плат: плат && плат.id, платИмя: плат && плат.name, баз: баз && баз.id, базИмя: баз && баз.name, свой }; }""")
    if not ид["плат"] or not ид["баз"]:
        плохо(f"{н} не нашлись опции для пробы: {ид}"); стр.close(); return
    стр.evaluate("() => { закрытьКарточкуЗначка(); }"); стр.wait_for_timeout(200)

    # ── над полем ──
    нажать_в_чат(стр, ид["плат"])
    о = стр.evaluate("""(ид) => ({ окно: document.getElementById('presetChipCard').classList.contains('show'), вкладка: _пкВкладка,
      над: [...document.querySelectorAll('#presetChipCard .pc-chopi .pc-chop-n')].map(х => х.textContent),
      залит: document.getElementById('tochat_' + ид).classList.contains('on'), тосты: window.__тосты.slice(-4) })""", ид["плат"])
    if not о["окно"] or о["вкладка"] != "m" or о["над"] != [ид["платИмя"]] or not о["залит"] or "Опция в чате — допишите вопрос и отправьте" not in о["тосты"]:
        плохо(f"{н} опция над полем: {о}")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(200)
    нажать_в_чат(стр, ид["плат"])
    о = стр.evaluate("() => ({ над: document.querySelectorAll('#presetChipCard .pc-chopi').length, тосты: window.__тосты.slice(-4) })")
    if о["над"] != 1 or "Эта опция уже над полем чата" not in о["тосты"]:
        плохо(f"{н} второе нажатие той же опции: {о}")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(200)
    нажать_в_чат(стр, ид["баз"])
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(200)
    нажать_в_чат(стр, ид["свой"])
    над = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-chopi')].map(х => х.innerText.replace(/\\s+/g, ' ').trim())")
    if len(над) != 3 or "Включено в базу" not in над[1] or "6 500" not in над[2]:
        плохо(f"{н} три опции над полем: {над}")
    вёрстка(стр, н, "опции над полем")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chatopt-draft-{ш}{'-n' if ночь else ''}.png"))

    # ── отправка ──
    стр.locator("#pcChatText").fill("Фанеру под стяжку точно нужно? И воск на торцы — это в каком разделе обычно?")
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(900)
    к = стр.evaluate(КАРТОЧКИ)
    база = стр.evaluate("() => (window.__ТАБЛИЦЫ.preset_messages.slice(-1)[0] || {}).attachments || []")
    выше = стр.evaluate("""() => { const м_ = [...document.querySelectorAll('#presetChipCard .pc-chm')].pop(), о = м_.querySelector('.pc-choc'), т = м_.querySelector('.pc-chx');
      return !!(о && т && о.getBoundingClientRect().bottom <= т.getBoundingClientRect().top + .5); }""")
    if not выше:
        плохо(f"{н} карточки опций не над текстом сообщения")
    if [х["имя"] for х in к] != [ид["платИмя"], ид["базИмя"], "Обработка торцов воском"] or any(х["вид"] != "same" for х in к):
        плохо(f"{н} карточки после отправки: {к}")
    if len(база) != 3 or not all(х.get("opt") and х.get("k") and х.get("n") and х.get("s") and х.get("at") for х in база) \
            or база[2].get("p") != 6500 or not база[1].get("inc"):
        плохо(f"{н} слепок в базе: {база}")
    о = стр.evaluate("""(ид) => ({ над: document.querySelectorAll('#presetChipCard .pc-chopi').length, поле: document.getElementById('pcChatText').value,
      залит: document.querySelectorAll('.opt-chat-btn.on').length })""", ид["плат"])
    if о["над"] or о["поле"] or о["залит"]:
        плохо(f"{н} после отправки: {о}")
    вёрстка(стр, н, "карточки в ленте")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chatopt-sent-{ш}{'-n' if ночь else ''}.png"))

    # ── что стало с опцией ──
    стр.evaluate("(ид) => { toggleGift(ид, { stopPropagation() {} }); calc(); заполнитьКарточкуЗначка(); }", ид["плат"]); стр.wait_for_timeout(400)
    к = стр.evaluate(КАРТОЧКИ)
    if not к or к[0]["вид"] != "ch" or к[0]["метка"] != "Сейчас в подарок." :
        плохо(f"{н} подарок не отмечен «изменилась»: {к[:1]}")
    стр.locator("#presetChipCard .pc-choc .pc-choc-st").first.click(); стр.wait_for_timeout(300)
    к = стр.evaluate(КАРТОЧКИ)
    if not к or к[0]["подсказка"] != "Сейчас в подарок.":
        плохо(f"{н} подсказка значка: {к[:1]}")
    вёрстка(стр, н, "подсказка значка")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chatopt-tip-{ш}{'-n' if ночь else ''}.png"))
    стр.evaluate("(ид) => { toggleGift(ид, { stopPropagation() {} }); toggleOpt(ид); calc(); заполнитьКарточкуЗначка(); }", ид["плат"]); стр.wait_for_timeout(400)
    к = стр.evaluate(КАРТОЧКИ)
    if not к or к[0]["вид"] != "del" or "сняли с расчёта" not in к[0]["метка"]:
        плохо(f"{н} снятая галочка не «удалена»: {к[:1]}")
    # Нажатие на карточку снятой — к строке и слова.
    стр.locator("#presetChipCard .pc-choc .pc-choc-go").first.click(); стр.wait_for_timeout(900)
    о = стр.evaluate("""(ид) => { const р = document.getElementById('lbl_' + ид), б = р && р.getBoundingClientRect();
      return { окно: document.getElementById('presetChipCard').classList.contains('show'), тосты: window.__тосты.slice(-4),
        вКадре: !!(б && б.top >= 0 && б.bottom <= innerHeight), вспышка: !!(р && р.classList.contains('pc-flash-row')) }; }""", ид["плат"])
    if о["окно"] or "Опцию сняли с расчёта" not in о["тосты"] or not о["вКадре"] or not о["вспышка"]:
        плохо(f"{н} переход к снятой опции: {о}")
    # Своя удалена.
    стр.evaluate("(ид) => { deleteCustomOpt(SECTIONS[0].key, Number(ид.slice(7)), { stopPropagation() {} }); }", ид["свой"])
    стр.evaluate("(ид) => { toggleOpt(ид); calc(); }", ид["плат"]); стр.wait_for_timeout(300)
    ч.открыть(стр); стр.wait_for_timeout(400)
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        плохо(f"{н} мини-окно не открылось после перехода к строке")
    к = стр.evaluate(КАРТОЧКИ)
    if [х["вид"] for х in к] != ["same", "same", "del"] or "удалили" not in к[2]["метка"]:
        плохо(f"{н} вернули как было и своя удалена: {к}")
    стр.locator("#presetChipCard .pc-choc").nth(2).click(); стр.wait_for_timeout(500)
    о = стр.evaluate("() => ({ окно: document.getElementById('presetChipCard').classList.contains('show'), тосты: window.__тосты.slice(-4) })")
    if not о["окно"] or "Опцию удалили из расчёта — в чате она такой, какой была" not in о["тосты"]:
        плохо(f"{н} нажатие на удалённую: {о}")
    вёрстка(стр, н, "удалённая опция")

    if полный:
        # Только опция, без текста.
        стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(200)
        нажать_в_чат(стр, ид["баз"])
        было = стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.length")
        стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(800)
        стало = стр.evaluate("() => { const с = window.__ТАБЛИЦЫ.preset_messages.slice(-1)[0]; return { н: window.__ТАБЛИЦЫ.preset_messages.length, текст: с.body, опций: (с.attachments || []).length }; }")
        if стало["н"] != было + 1 or стало["текст"] or стало["опций"] != 1:
            плохо(f"{н} сообщение только с опцией: {стало}")
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
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: значок «В чат» после подарка у каждой строки и только у расчёта с чатом, опция над полем и залитый значок, "
          "слепок в базе, «не изменилась / изменилась / удалена» с подсказкой, переход к строке, сообщение только с опцией, "
          "вёрстка на 390 и 1440 днём и ночью.")


if __name__ == "__main__":
    главная()
