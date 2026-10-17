#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чат пресета: отметка сотрудника через «@» и строка о ней в колокольчике.

Константин 17.10.2026: «В чате через @ чтобы можно было отметить пользователя
и тогда ему сообщение прийдет в колокольчик со ссылкой на пресет, в котором
чат и текстом сообщения в колокольчике. Он с колокольчика заходит в пресет и
читает там сообщение».

Проба держит, на заглушке базы (preset_chat_people и preset_chat_mentions
ведут себя как функции миграции preset_chat_mentions) и в настоящих Geologica
и Unbounded:
  • «@» в начале слова открывает список сотрудников без себя самого; «@»
    посреди слова (адрес почты) и набранное, чего ни у кого нет, — не открывают;
  • набранное после «@» отбирает по началу имени и фамилии, «ё» как «е»;
    стрелки двигают выбор, Enter и Tab вставляют, мышь — тоже, курсор встаёт
    после имени; Escape закрывает список, а мини-окно остаётся;
  • в базу уходит mentions — номера тех, чьё «@Имя» осталось в тексте:
    отмеченный и потом стёртый в номера не попадает;
  • в ленте выделено «@Имя» только у отмеченных на самом деле, своё имя —
    заливкой; набранное руками «@Иван» без выбора — просто текст;
  • колокольчик: строка «Вас отметили в чате пресета „…“: «текст»», подпись —
    кто написал; нажатие открывает мини-окно на вкладке «Чат» и подсвечивает
    само сообщение;
  • вёрстка на 390 и 1440: список внутри карточки, над полем и не касается
    его, строки не ниже 40 px, лента и поле — как в пробе чата.

    python3 check_chat_mentions.py
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


ОТМЕТИЛИ_МЕНЯ = "a0000000-0000-4000-8000-0000000000a1"

ДАННЫЕ = """(код) => {
  const т = window.__ТАБЛИЦЫ, д = Date.now(), мин = 60e3;
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  const с = (ид, кто, тело, назад, доп) => Object.assign({ id: ид, code: код, author_id: кто, author_name: кто === 'u-проба' ? 'Проба' : 'Ольга Проверкина',
    body: тело, reply_to: null, attachments: [], review_state: null, kind: 'msg', mentions: [], created_at: new Date(д - назад).toISOString() }, доп || {});
  т.preset_messages = [
    с('a0000000-0000-4000-8000-0000000000a0', 'u-коллега', 'Набрано руками: @Иван Петров, без выбора из списка.', 40 * мин),
    с('""" + ОТМЕТИЛИ_МЕНЯ + """', 'u-коллега', '@Проба посмотри фундамент — у заказчика уклон участка.', 20 * мин, { mentions: ['u-проба'] }),
  ];
  // После отметки — ещё переписка: лента длинная, и переход из колокольчика,
  // сброшенный к последнему сообщению, отмеченное бы не показал.
  for (let i = 0; i < 8; i++) т.preset_messages.push(с('a0000000-0000-4000-8000-0000000001' + String(i).padStart(2, '0'), i % 2 ? 'u-проба' : 'u-коллега',
    'Переписка после отметки, сообщение ' + (i + 1) + '.\\nВторая строка, чтобы лента была длиннее окна.', (18 - i * 2) * мин));
  window.__ЛЮДИ_СПРОШЕНО = 0;
  window.__RPC.preset_chat_people = () => { window.__ЛЮДИ_СПРОШЕНО++; return [
    { id: 'u-иван', name: 'Иван Петров' }, { id: 'u-ирина', name: 'Ирина Иванова' }, { id: 'u-логин', name: 'ivanov.ivan' },
    { id: 'u-коллега', name: 'Ольга Проверкина' }, { id: 'u-проба', name: 'Проба' }, { id: 'u-фёдор', name: 'Фёдор Ёлкин' }]; };
  window.__RPC.preset_chat_mentions = () => [{ id: '""" + ОТМЕТИЛИ_МЕНЯ + """', code: код,
    body: '@Проба посмотри фундамент — у заказчика уклон участка.', author_name: 'Ольга Проверкина',
    created_at: new Date(д - 20 * мин).toISOString(), preset_name: 'Баня с уклоном' }];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д - мин).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  _чатЛюди = { список: null, грузится: false, ошибка: '', когда: 0 };
  _чатИзменение = null;
}"""

СПИСОК = """() => { const сп = document.getElementById('pcChatMention'), к = document.getElementById('presetChipCard');
  if (!сп) return null;
  const р = сп.getBoundingClientRect(), кр = к.getBoundingClientRect(), вв = к.querySelector('.pc-chin').getBoundingClientRect();
  const строки = [...сп.querySelectorAll('[role="option"]')];
  const поле = document.getElementById('pcChatText');
  return { имена: строки.map(с => с.querySelector('.pc-chmn-n').textContent), выбран: строки.findIndex(с => с.getAttribute('aria-selected') === 'true'),
    акт: поле.getAttribute('aria-activedescendant') || '', вКарточке: р.left >= кр.left + 4 && р.right <= кр.right - 4 && р.top >= кр.top + 4,
    зазорДоПоля: Math.round(вв.top - р.bottom), низшая: строки.length ? Math.min(...строки.map(с => с.getBoundingClientRect().height)) : 0,
    видна: р.height > 0 && getComputedStyle(сп).visibility !== 'hidden', текст: сп.innerText }; }"""

ПОЛЕ = """() => { const п = document.getElementById('pcChatText'); return { т: п.value, к: п.selectionStart, фокус: document.activeElement === п }; }"""


def набрать(стр, т):
    стр.locator("#pcChatText").press_sequentially(т, delay=15)
    стр.wait_for_timeout(200)


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(600)
    # ── выделение в ленте ──
    в_ = стр.evaluate("""(ид) => { const л = document.getElementById('pcChatList');
      const м_ = л.querySelector('.pc-chm[data-mid="' + ид + '"]'), руками = л.querySelector('.pc-chm[data-mid="a0000000-0000-4000-8000-0000000000a0"]');
      const с = м_ && м_.querySelector('.pc-chmt');
      // Сдвиг самого текста, а не коробки выделения: поля подложки сдвигали
      // строку с именем вправо от соседних, а коробка при этом стояла ровно.
      const д = document.createRange(); if (с) д.selectNodeContents(с);
      const сдвиг = с ? Math.round(д.getClientRects()[0].left - м_.querySelector('.pc-chx').getBoundingClientRect().left) : null;
      return { моё: с ? с.textContent : '', сдвиг, заливка: !!(с && с.classList.contains('me') && getComputedStyle(с).backgroundColor !== 'rgba(0, 0, 0, 0)'),
        руками: руками ? руками.querySelectorAll('.pc-chmt').length : -1, текст: м_ ? м_.querySelector('.pc-chx').textContent : '' }; }""", ОТМЕТИЛИ_МЕНЯ)
    if в_["моё"] != "@Проба" or not в_["заливка"] or в_["сдвиг"] != 0 or в_["руками"] != 0 or not в_["текст"].startswith("@Проба посмотри"):
        плохо(f"{н} выделение отмеченных в ленте: {в_}")
    # ── список ──
    поле = стр.locator("#pcChatText")
    поле.click()
    набрать(стр, "почта ivan@")
    if стр.evaluate(СПИСОК):
        плохо(f"{н} «@» посреди слова (адрес почты) открыл список")
    поле.fill(""); стр.wait_for_timeout(100)
    набрать(стр, "Посмотри, @")
    с = стр.evaluate(СПИСОК)
    if not с or с["имена"] != ["Иван Петров", "Ирина Иванова", "ivanov.ivan", "Ольга Проверкина", "Фёдор Ёлкин"]:
        плохо(f"{н} «@» — список всех без себя: {с}")
    elif not (с["вКарточке"] and с["видна"] and с["зазорДоПоля"] >= 4 and с["низшая"] >= 39.5 and с["выбран"] == 0 and с["акт"] == "pcChmn-0"):
        плохо(f"{н} список над полем: {с}")
    for т in стр.evaluate(ч.ВЁРСТКА):
        плохо(f"{н} открытый список: {т}")
    if с:
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"mention-{ш}{'-n' if ночь else ''}.png"))
    набрать(стр, "Ив")
    с = стр.evaluate(СПИСОК)
    if not с or с["имена"] != ["Иван Петров", "Ирина Иванова"]:
        плохо(f"{н} «@Ив» отбирает по началу имени и фамилии: {с}")
    поле.press("ArrowDown"); стр.wait_for_timeout(120)
    с = стр.evaluate(СПИСОК)
    if not с or с["выбран"] != 1 or с["акт"] != "pcChmn-1":
        плохо(f"{н} стрелка вниз не сдвинула выбор: {с}")
    поле.press("Enter"); стр.wait_for_timeout(250)
    п = стр.evaluate(ПОЛЕ)
    if п["т"] != "Посмотри, @Ирина Иванова " or п["к"] != len(п["т"]) or not п["фокус"] or стр.evaluate(СПИСОК):
        плохо(f"{н} Enter вставил выбранное: {п}")
    if стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.length") != 10:
        плохо(f"{н} Enter при открытом списке отправил сообщение")
    набрать(стр, "и @пет")
    с = стр.evaluate(СПИСОК)
    if not с or с["имена"] != ["Иван Петров"]:
        плохо(f"{н} «@пет» — по фамилии: {с}")
    else:
        стр.locator("#pcChatMention [role='option']").first.click(); стр.wait_for_timeout(250)
    набрать(стр, "и @фе")
    с = стр.evaluate(СПИСОК)
    if not с or с["имена"] != ["Фёдор Ёлкин"]:
        плохо(f"{н} «@фе» — «ё» как «е»: {с}")
    поле.press("Tab"); стр.wait_for_timeout(250)
    п = стр.evaluate(ПОЛЕ)
    if п["т"] != "Посмотри, @Ирина Иванова и @Иван Петров и @Фёдор Ёлкин " or not п["фокус"]:
        плохо(f"{н} мышь и Tab вставили выбранное: {п}")
    набрать(стр, "@Щ")
    if стр.evaluate(СПИСОК):
        плохо(f"{н} «@Щ», которого ни у кого нет, оставил список открытым")
    набрать(стр, " @")
    if not стр.evaluate(СПИСОК):
        плохо(f"{н} второй «@» список не открыл")
    поле.press("Escape"); стр.wait_for_timeout(200)
    if стр.evaluate(СПИСОК) or not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        плохо(f"{н} Escape: список {'открыт' if стр.evaluate(СПИСОК) else 'закрыт'}, мини-окно "
              f"{'открыто' if стр.evaluate('() => document.getElementById(\"presetChipCard\").classList.contains(\"show\")') else 'закрылось'}")
    # Отмеченный и стёртый в номера не попадает.
    поле.fill("Посмотри, @Ирина Иванова и @Иван Петров, проверьте кровлю."); стр.wait_for_timeout(100)
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(600)
    о = стр.evaluate("""() => { const т = window.__ТАБЛИЦЫ.preset_messages, п = т[т.length - 1];
      const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid="' + п.id + '"]');
      return { тело: п.body, кто: п.mentions || null, выделено: м_ ? [...м_.querySelectorAll('.pc-chmt')].map(с => с.textContent) : null }; }""")
    if о["тело"] != "Посмотри, @Ирина Иванова и @Иван Петров, проверьте кровлю." or о["кто"] != ["u-ирина", "u-иван"]:
        плохо(f"{н} в базу ушло: {о}")
    if о["выделено"] != ["@Ирина Иванова", "@Иван Петров"]:
        плохо(f"{н} отправленное — выделение отмеченных: {о['выделено']}")
    # Время сообщению ставит база (preset_messages_before_insert); заглушка — нет.
    стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.forEach(х => { х.created_at = х.created_at || new Date().toISOString(); })")
    if стр.evaluate("() => window.__ЛЮДИ_СПРОШЕНО") != 1:
        плохо(f"{н} список сотрудников спрошен у базы {стр.evaluate('() => window.__ЛЮДИ_СПРОШЕНО')} раз, а не один")
    # Без отметок mentions не уходит вовсе: до миграции столбца нет, и
    # обычное сообщение не должно зависеть от него.
    поле.fill("Просто сообщение."); стр.wait_for_timeout(100)
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(500)
    if "mentions" in стр.evaluate("() => { const т = window.__ТАБЛИЦЫ.preset_messages; return Object.keys(т[т.length - 1]); }"):
        плохо(f"{н} сообщение без отметок несёт mentions")
    стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.forEach(х => { х.created_at = х.created_at || new Date().toISOString(); })")
    # ── колокольчик ──
    ч.вкладка(стр, "p")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    стр.locator("#bellBtn").click(); стр.wait_for_timeout(900)
    у = стр.evaluate("""() => { const м_ = document.getElementById('bellMenu');
      const и = [...м_.querySelectorAll('.nt-i')].find(х => /отметили/.test(х.innerText));
      if (!и) return null;
      const р = и.getBoundingClientRect(), мр = м_.getBoundingClientRect();
      return { т: и.querySelector('.t').innerText.replace(/\\s+/g, ' '), кто: (и.querySelector('.nt-who') || {}).textContent || '', жмётся: и.classList.contains('go'),
        вОкне: р.left >= мр.left && р.right <= мр.right + .5, значок: !!и.querySelector('svg circle') }; }""")
    if not у or "Вас отметили в чате пресета Баня с уклоном" not in у["т"] or "«@Проба посмотри фундамент — у заказчика уклон участка.»" not in у["т"] \
            or у["кто"] != "Ольга Проверкина" or not у["жмётся"] or not у["вОкне"] or not у["значок"]:
        плохо(f"{н} строка в колокольчике: {у}")
    else:
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"mention-bell-{ш}{'-n' if ночь else ''}.png"))
        # Лента осталась у последнего сообщения — как у человека, который
        # переписывался и закрыл окно: переход обязан увести её от дна.
        стр.evaluate("() => { const л = document.getElementById('pcChatList'); if (л) л.scrollTop = л.scrollHeight; }")
        стр.locator("#bellMenu .nt-i.go").filter(has_text="отметили").first.click(); стр.wait_for_timeout(1500)
        п = стр.evaluate("""(ид) => { const к = document.getElementById('presetChipCard'), л = к.querySelector('#pcChatList');
          const м_ = л && л.querySelector('.pc-chm[data-mid="' + ид + '"]');
          const лр = л && л.getBoundingClientRect(), мр = м_ && м_.getBoundingClientRect();
          return { открыто: к.classList.contains('show'), вкладка: _пкВкладка, колокольчик: окноУведомленийОткрыто(),
            вспышка: !!(м_ && м_.classList.contains('pc-chm-flash')), виден: !!(мр && мр.top >= лр.top - 1 && мр.bottom <= лр.bottom + 1),
            где: мр && лр ? [Math.round(мр.top - лр.top), Math.round(мр.bottom - лр.top), Math.round(лр.height), л.scrollTop, л.scrollHeight] : null }; }""", ОТМЕТИЛИ_МЕНЯ)
        if not (п["открыто"] and п["вкладка"] == "m" and not п["колокольчик"] and п["вспышка"] and п["виден"]):
            плохо(f"{н} нажатие в колокольчике: {п}")
        стр.wait_for_timeout(2400)
        стр.screenshot(path=str(СНИМКИ / f"mention-feed-{ш}{'-n' if ночь else ''}.png"))
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, True)
                прогон(бр, порт, 390, 844, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «@» открывает список сотрудников без себя, отбор по имени и фамилии, стрелки, Enter, Tab и мышь, Escape; "
          "в базу уходят только оставшиеся в тексте, выделены только отмеченные; колокольчик — текст, автор и переход "
          "к сообщению; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
