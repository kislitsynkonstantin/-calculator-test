#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Удаление сообщения в чате пресета — долгим нажатием, с «Отменить» на 3 секунды.

Константин 19.10.2026: «В чате по долгому нажатию на сообщение сделай
возможность его удалять. Если это файл, то удалять из базы» и, снимком
Telegram: «Сообщение удалено вот такое сделай уведомление на 3 секунды. Пока я
только могу удалять всегда. А все остальные могут редактировать и удалять
первые 5 минут после отправки».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • долгое касание пальцем (настоящие события касания) и правая кнопка мыши
    открывают под пузырём полоску, а палец, отпущенный следом, ничего не
    нажимает; у своего свежего — «Копировать» и
    «Удалить», у своего старше 5 минут и у чужого — только «Копировать»;
  • у администратора «Удалить» есть и у чужого старого;
  • «Удалить»: сообщение сразу пропадает, над полем — «Сообщение удалено» с
    «Отменить»; 2,5 секунды база не спрошена;
  • «Отменить» — сообщение на месте, ни сейчас, ни через 3,5 секунды запроса нет;
  • без отмены: через 3 секунды один запрос preset_chat_delete, файл сообщения
    стёрт из хранилища, на месте — «Сообщение удалено», в журнале действий —
    chat_deleted с первой строкой;
  • нажатие мимо полоски её закрывает; полоска и строка над полем в карточке,
    поле нажатия кнопок не меньше 44 px, текст не обрезан; 390 и 1440.

    python3 check_chat_delete.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
ЧУЖОЕ = "11111111-1111-4111-8111-111111111111"      # Ольга, вчера
СТАРОЕ_СВОЁ = "22222222-2222-4222-8222-222222222222"  # своё, вчера
СВЕЖЕЕ = "55555555-5555-4555-8555-555555555555"       # своё, минуту назад, с файлом
ПУТЬ = "файлы/проба/план.pdf"


def плохо(т):
    НАХОДКИ.append(т)


ДОБАВИТЬ = """(путь) => {
  const т = window.__ТАБЛИЦЫ, код = (т.preset_messages[0] || {}).code;
  т.preset_messages.push({ id: '55555555-5555-4555-8555-555555555555', code: код, author_id: 'u-проба', author_name: 'Проба',
    body: 'План с размерами — посмотрите.', reply_to: null, review_state: null,
    attachments: [{ path: путь, name: 'план.pdf', type: 'application/pdf', size: 2048 }], created_at: new Date(Date.now() - 60e3).toISOString() });
  window.__УДАЛЕНИЯ = []; window.__СТЁРТО = []; window.__ЖУРНАЛ = [];
  window.__RPC.preset_chat_delete = (а) => {
    window.__УДАЛЕНИЯ.push(а.p_id);
    const с = т.preset_messages.find(х => х.id === а.p_id);
    Object.assign(с, { body: '', attachments: [], review_state: null, deleted_at: new Date().toISOString() });
    return Object.assign({}, с);
  };
  const из = _sb.storage.from.bind(_sb.storage);
  _sb.storage.from = к => { const о = из(к); о.remove = (пути) => { window.__СТЁРТО.push(...пути); return Promise.resolve({ data: [], error: null }); }; return о; };
  const был = window.logEvent; window.logEvent = function (вид, д) { window.__ЖУРНАЛ.push([вид, д && д.obj]); return был.apply(this, arguments); };
  window._sbProfile = Object.assign({}, window._sbProfile || {}, { role: 'manager' });
}"""

МЕНЮ = """(ид) => { const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid="' + ид + '"]');
  const п = м_ && м_.querySelector('.pc-chmenu'); return п ? [...п.querySelectorAll('button')].map(б => б.innerText.trim()) : null; }"""

СОСТ = """(ид) => { const к = document.getElementById('presetChipCard'), м_ = к.querySelector('.pc-chm[data-mid="' + ид + '"]');
  const ст = к.querySelector('.pc-chdelst');
  return { есть: !!м_, заглушка: !!(м_ && м_.classList.contains('pc-chdel')), текст: м_ ? м_.innerText.replace(/\\s+/g, ' ').trim() : '',
    строка: ст ? ст.innerText.replace(/\\s+/g, ' ').trim() : '', удаления: window.__УДАЛЕНИЯ.slice(), стёрто: window.__СТЁРТО.slice(),
    журнал: window.__ЖУРНАЛ.filter(х => х[0] === 'chat_deleted') }; }"""

# Полоска и строка над полем: в карточке, поле нажатия, текст целиком.
ВИД = """() => { const к = document.getElementById('presetChipCard'), р = к.getBoundingClientRect(), н = [];
  к.querySelectorAll('.pc-chmenu button, .pc-chdelst button').forEach(б => { const п = б.getBoundingClientRect(), с = getComputedStyle(б, '::before');
    if (п.left < р.left + 2 || п.right > р.right - 2) н.push('«' + б.innerText.trim() + '» у края карточки или за ним');
    const h = п.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
    if (h < 43.5) н.push('поле нажатия «' + б.innerText.trim() + '» ' + Math.round(h) + ' px');
    if (б.scrollWidth > б.clientWidth + 1) н.push('«' + б.innerText.trim() + '» обрезано'); });
  const ст = к.querySelector('.pc-chdelst');
  if (ст) { const п = ст.getBoundingClientRect(); if (п.left < р.left || п.right > р.right) н.push('строка «Сообщение удалено» за краем карточки'); }
  return н; }"""


def к_сообщению(стр, ид):
    # Ленту листаем сами: прокрутка Playwright уводит страницу, а не ленту, и
    # пузырь остаётся под краем ленты.
    стр.evaluate("(ид) => { const э = document.querySelector('#presetChipCard .pc-chm[data-mid=\"' + ид + '\"] .pc-chb'); if (э) э.scrollIntoView({ block: 'center' }); }", ид)
    стр.wait_for_timeout(150)


def правая(стр, ид):
    к_сообщению(стр, ид)
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{ид}'] .pc-chb").click(button="right"); стр.wait_for_timeout(250)


def касание(стр, cdp, ид, мс=750):
    # Настоящее долгое касание: события касания, а не мыши.
    к_сообщению(стр, ид)
    # Касание — по тексту сообщения: короткое касание файла законно открывает просмотр.
    б = стр.locator(f"#presetChipCard .pc-chm[data-mid='{ид}'] .pc-chx").bounding_box()
    x, y = б["x"] + 10, б["y"] + б["height"] / 2
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    стр.wait_for_timeout(мс)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    стр.wait_for_timeout(250)


def прогон(бр, порт, ш, в, полный):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    стр.evaluate(ДОБАВИТЬ, ПУТЬ)
    ч.открыть(стр); стр.wait_for_timeout(500)
    ч.вкладка(стр, "m"); стр.wait_for_timeout(700)

    # ── права в полоске ──
    правая(стр, СВЕЖЕЕ)
    if стр.evaluate(МЕНЮ, СВЕЖЕЕ) != ["Копировать", "Удалить"]:
        плохо(f"{н} своё свежее, правая кнопка: полоска {стр.evaluate(МЕНЮ, СВЕЖЕЕ)}")
    for т in стр.evaluate(ВИД):
        плохо(f"{н} полоска: {т}")
    стр.mouse.move(5, 5); стр.locator(f"#presetChipCard .pc-chm[data-mid='{СВЕЖЕЕ}']").scroll_into_view_if_needed()
    стр.screenshot(path=str(СНИМКИ / f"chat-del-menu-{ш}.png"))
    # Нажатие мимо полоски её закрывает.
    стр.locator("#pcChatText").click(); стр.wait_for_timeout(200)
    if стр.evaluate(МЕНЮ, СВЕЖЕЕ) is not None:
        плохо(f"{н} нажатие мимо полоски её не закрыло")
    for ид, что in ((СТАРОЕ_СВОЁ, "своё старше 5 минут"), (ЧУЖОЕ, "чужое")):
        правая(стр, ид)
        if стр.evaluate(МЕНЮ, ид) != ["Копировать"]:
            плохо(f"{н} {что}: полоска {стр.evaluate(МЕНЮ, ид)} — «Удалить» быть не должно")
        стр.keyboard.press("Escape"); стр.wait_for_timeout(150)
        if стр.evaluate(МЕНЮ, ид) is not None:
            плохо(f"{н} Escape не закрыл полоску")

    # ── долгое касание пальцем ──
    if полный:
        cdp = стр.context.new_cdp_session(стр)
        cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
        касание(стр, cdp, СВЕЖЕЕ)
        if стр.evaluate(МЕНЮ, СВЕЖЕЕ) != ["Копировать", "Удалить"]:
            плохо(f"{н} долгое касание не открыло полоску: {стр.evaluate(МЕНЮ, СВЕЖЕЕ)}")
        # Полоска сдвигает ленту, и палец отпускается над другой кнопкой; это
        # отпускание не должно ничего нажать (было: нажимало «В правки»).
        нажато = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-chflag[aria-pressed=\"true\"]')].length")
        if нажато:
            плохо(f"{н} палец, отпущенный после долгого касания, нажал кнопку под собой: «В правки» нажато у {нажато}")
        стр.keyboard.press("Escape"); стр.wait_for_timeout(150)
        касание(стр, cdp, СВЕЖЕЕ, 200)
        if стр.evaluate(МЕНЮ, СВЕЖЕЕ) is not None:
            плохо(f"{н} короткое касание открыло полоску")
        cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": False})

    # ── «Удалить» → «Отменить» ──
    правая(стр, СВЕЖЕЕ)
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{СВЕЖЕЕ}'] [data-act='ch-del']").click(); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ, СВЕЖЕЕ)
    if с["есть"] or "Сообщение удалено" not in с["строка"] or "Отменить" not in с["строка"]:
        плохо(f"{н} после «Удалить»: сообщение не скрыто или нет строки «Сообщение удалено / Отменить»: {с}")
    for т in стр.evaluate(ВИД):
        плохо(f"{н} строка над полем: {т}")
    стр.screenshot(path=str(СНИМКИ / f"chat-del-undo-{ш}.png"))
    стр.wait_for_timeout(2200)
    if стр.evaluate(СОСТ, СВЕЖЕЕ)["удаления"]:
        плохо(f"{н} за 2,5 секунды удаление ушло в базу")
    стр.locator("#presetChipCard [data-act='ch-del-undo']").click(); стр.wait_for_timeout(3700)
    с = стр.evaluate(СОСТ, СВЕЖЕЕ)
    if not с["есть"] or с["заглушка"] or с["удаления"] or с["строка"]:
        плохо(f"{н} после «Отменить»: {с}")

    # ── без отмены ──
    правая(стр, СВЕЖЕЕ)
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{СВЕЖЕЕ}'] [data-act='ch-del']").click(); стр.wait_for_timeout(3600)
    с = стр.evaluate(СОСТ, СВЕЖЕЕ)
    if с["удаления"] != [СВЕЖЕЕ] or с["стёрто"] != [ПУТЬ] or not с["заглушка"] or "Сообщение удалено" not in с["текст"] or с["строка"]:
        плохо(f"{н} удаление без отмены: {с}")
    if len(с["журнал"]) != 1 or "План с размерами" not in str(с["журнал"][0][1]):
        плохо(f"{н} журнал действий: {с['журнал']}")
    стр.screenshot(path=str(СНИМКИ / f"chat-del-done-{ш}.png"))

    # ── администратор ──
    стр.evaluate("() => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'admin' }); }")
    правая(стр, ЧУЖОЕ)
    if стр.evaluate(МЕНЮ, ЧУЖОЕ) != ["Копировать", "Удалить"]:
        плохо(f"{н} администратор: у чужого старого полоска {стр.evaluate(МЕНЮ, ЧУЖОЕ)}")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(150)
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{СВЕЖЕЕ}'] .pc-chdel-b").click(button="right"); стр.wait_for_timeout(250)
    if стр.evaluate(МЕНЮ, СВЕЖЕЕ) is not None:
        плохо(f"{н} у удалённого открылась полоска")
    for о in ошибки[:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 390, 844, True)
                прогон(бр, порт, 1440, 900, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: удаление в чате — долгим касанием и правой кнопкой, «Удалить» только у своего в первые 5 минут и у "
          "администратора всегда; «Отменить» 3 секунды, отменённое базы не трогает; без отмены один запрос, файл стёрт, "
          "на месте «Сообщение удалено», строка в журнале; полоска закрывается мимо и Escape; 390 и 1440.")


if __name__ == "__main__":
    главная()
