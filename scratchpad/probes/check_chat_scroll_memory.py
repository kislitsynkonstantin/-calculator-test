#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чат пресета открывается там, где его оставили, и стрелка к последнему сообщению.

Константин 21.10.2026, снимком чата: «Когда проматываю чат, запоминай положение
в чате. И если закрыл окно и потом открыл, открывай на том же месте. И добавь
кнопку перемотать вниз чат (стрелочку аккуратную)».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • первое открытие — у последнего сообщения, стрелки нет;
  • пролистали вверх — стрелка появилась, над полем справа, внутри карточки,
    32 px нарисована и не меньше 44 px поле нажатия, ленту не перекрывает
    кнопками сообщений;
  • закрыли мини-окно и открыли — то же сообщение у верхнего края, с тем же
    отступом (±4 px); переключились на «Пресет» и обратно — так же;
  • память сброшена и прочитана из localStorage, как при перезагрузке, — так же; место хранится сообщением, а не высотой:
    новое сообщение снизу место не сдвигает;
  • стрелка возвращает к последнему сообщению и пропадает; закрыли у дна —
    открывается у дна, с новым сообщением;
  • отправка своего сообщения уводит к нему, как и раньше;
  • вёрстка на 390 и 1440.

    python3 check_chat_scroll_memory.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ЕЩЁ = """(код) => { const т = window.__ТАБЛИЦЫ, д = Date.now();
  for (let i = 0; i < 24; i++) т.preset_messages.splice(0, 0, { id: 'aaaaaaaa-0000-4000-8000-' + String(i).padStart(12, '0'), code: код,
    author_id: i % 2 ? 'u-проба' : 'u-коллега', author_name: i % 2 ? 'Проба' : 'Ольга Проверкина',
    body: 'Сообщение номер ' + (24 - i) + ': уточнение по разделу — проверить размеры парной и окна.', reply_to: null, attachments: [], review_state: null,
    created_at: new Date(д - 3 * 86400e3 + (24 - i) * 600e3).toISOString() });
  т.preset_messages.sort((а, б) => а.created_at < б.created_at ? -1 : 1); }"""

МЕСТО = """() => { const л = document.getElementById('pcChatList'); if (!л) return null;
  const в = л.getBoundingClientRect().top;
  const эл = [...л.querySelectorAll('.pc-chm[data-mid]')].find(х => х.getBoundingClientRect().bottom > в + 1);
  const кн = document.querySelector('#presetChipCard .pc-chdown');
  return { mid: эл && эл.getAttribute('data-mid'), сдвиг: эл ? эл.getBoundingClientRect().top - в : null,
    дно: л.scrollTop + л.clientHeight >= л.scrollHeight - 4, верх: л.scrollTop,
    стрелка: !!(кн && кн.classList.contains('on') && getComputedStyle(кн).visibility === 'visible') }; }"""

ВИД = """() => { const к = document.getElementById('presetChipCard'), кн = к.querySelector('.pc-chdown'), н = [];
  const б = кн.getBoundingClientRect(), р = к.getBoundingClientRect(), л = document.getElementById('pcChatList').getBoundingClientRect();
  const п = document.querySelector('#presetChipCard .pc-chin').getBoundingClientRect();
  if (б.left < р.left + 4 || б.right > р.right - 4) н.push('стрелка у края карточки или за ним');
  if (Math.abs(б.width - 32) > 1 || Math.abs(б.height - 32) > 1) н.push('стрелка нарисована ' + Math.round(б.width) + '×' + Math.round(б.height));
  const с = getComputedStyle(кн, '::before');
  if (б.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0) < 43.5) н.push('поле нажатия стрелки меньше 44 px');
  if (б.bottom > п.top - 4) н.push('стрелка садится на поле сообщения: зазор ' + Math.round(п.top - б.bottom));
  if (б.top < л.top) н.push('стрелка выше ленты');
  if (б.right < л.right - 30) н.push('стрелка не у правого края ленты');
  return н; }"""


def прокрутить(стр, сколько):
    стр.evaluate("(с) => { const л = document.getElementById('pcChatList'); л.scrollTop = с; л.dispatchEvent(new Event('scroll')); }", сколько)
    стр.wait_for_timeout(500)


def переоткрыть(стр):
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(400)
    ч.открыть(стр); стр.wait_for_timeout(900)


def близко(а, б, н, что):
    if not а or not б or а["mid"] != б["mid"] or abs((а["сдвиг"] or 0) - (б["сдвиг"] or 0)) > 4:
        НАХОДКИ.append(f"{н} {что}: было {б}, стало {а}")


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        НАХОДКИ.append(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate("() => { try { localStorage.removeItem('banya_chat_pos'); } catch (e) {} _чатМеста = {}; }")
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код); стр.evaluate(ЕЩЁ, код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(900)
    с = стр.evaluate(МЕСТО)
    if not с or not с["дно"] or с["стрелка"]:
        НАХОДКИ.append(f"{н} первое открытие не у последнего сообщения или со стрелкой: {с}")
    # ── пролистали вверх ──
    прокрутить(стр, 300)
    было = стр.evaluate(МЕСТО)
    if not было["стрелка"]:
        НАХОДКИ.append(f"{н} пролистали вверх — стрелки нет: {было}")
    for т in стр.evaluate(ВИД):
        НАХОДКИ.append(f"{н} {т}")
    ч.вёрстка(стр, н, "стрелка к последнему сообщению")
    стр.mouse.move(5, 5)
    стр.screenshot(path=f"/tmp/chat-down-{ш}.png")
    # ── закрыли и открыли ──
    переоткрыть(стр)
    близко(стр.evaluate(МЕСТО), было, н, "после закрытия и открытия мини-окна место другое")
    # ── вкладка «Пресет» и обратно ──
    ч.вкладка(стр, "p"); ч.вкладка(стр, "m"); стр.wait_for_timeout(700)
    близко(стр.evaluate(МЕСТО), было, н, "после вкладки «Пресет» место другое")
    # ── новое сообщение снизу место не сдвигает ──
    стр.evaluate("""(код) => { window.__ТАБЛИЦЫ.preset_messages.push({ id: 'bbbbbbbb-0000-4000-8000-000000000001', code: код, author_id: 'u-коллега',
      author_name: 'Ольга Проверкина', body: 'Новое сообщение снизу.', reply_to: null, attachments: [], review_state: null, created_at: new Date().toISOString() }); }""", код)
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    стр.evaluate("() => загрузитьЧат(true, true)"); стр.wait_for_timeout(600)
    ч.открыть(стр); стр.wait_for_timeout(900)
    близко(стр.evaluate(МЕСТО), было, н, "новое сообщение снизу сдвинуло место")
    # ── перезагрузка страницы: память забыта, место читается из localStorage ──
    # (настоящая перезагрузка в пробе теряет заглушку входа, поэтому память
    # и ленту сбрасывают руками, а место берётся из хранилища, как при запуске).
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    стр.evaluate("""() => { _чатМеста = {}; _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
      _чатМеста = JSON.parse(localStorage.getItem('banya_chat_pos') || '{}'); }""")
    ч.открыть(стр); стр.wait_for_timeout(1200)
    близко(стр.evaluate(МЕСТО), было, н, "после перезагрузки страницы место другое")
    # ── стрелка ведёт вниз и пропадает; закрыли у дна — открывается у дна ──
    стр.locator("#presetChipCard .pc-chdown").click(); стр.wait_for_timeout(900)
    с = стр.evaluate(МЕСТО)
    if not с["дно"] or с["стрелка"]:
        НАХОДКИ.append(f"{н} стрелка не привела к последнему сообщению или не пропала: {с}")
    переоткрыть(стр)
    с = стр.evaluate(МЕСТО)
    if not с["дно"]:
        НАХОДКИ.append(f"{н} закрыли у последнего сообщения — открылось не у него: {с}")
    # ── своё сообщение уводит вниз и с места выше ──
    прокрутить(стр, 200)
    стр.locator("#pcChatText").fill("Проба: своё сообщение"); стр.locator("#presetChipCard [data-act='ch-send']").click()
    стр.wait_for_timeout(1200)
    с = стр.evaluate(МЕСТО)
    if not с["дно"]:
        НАХОДКИ.append(f"{н} отправка своего сообщения не увела к нему: {с}")
    for е in [е for е in ошибки if "supabase.co" not in е][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {е[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 390, 844)
                прогон(бр, порт, 1440, 900)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: чат открывается на том же сообщении после закрытия мини-окна, смены вкладки, нового сообщения снизу "
          "и перезагрузки страницы; стрелка над полем справа появляется выше дна, ведёт к последнему и пропадает; "
          "закрытый у дна открывается у дна; своё сообщение уводит к себе; 390 и 1440.")


if __name__ == "__main__":
    главная()
