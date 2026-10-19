#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чат пресета: правка своего сообщения, галочка правки в журнале и в чате,
вся история.

Константин 17.10.2026: «В чате добавь возможность редактировать свои сообщения
первые 5 минут после отправки… А если уже кто-то сделал „Ответить“ на это
сообщение, то сразу правки его запрещай. И проверь, чтобы в базу все писалось,
вся история чата… В журнале действий отображай согласование пунктов ручных,
которые через галочку. И в чате эту запись тоже дублируй».

Проба держит, на заглушке базы (она ведёт себя как функции миграции
preset_chat: правка — только своё, 5 минут и без ответа; отметка «выполнено»
кладёт в ленту строку-событие) и в настоящих Geologica и Unbounded:
  • «Изменить» есть только у своего сообщения моложе 5 минут без ответа: у
    старого, у отвеченного и у чужого — нет; пропадает само, когда срок вышел,
    и когда на сообщение ответили каналом;
  • правка: текст в поле, над полем «Изменение», скрепка выключена; Enter —
    в базу уходит preset_chat_edit с новым текстом, в ленте новый текст и
    «изменено», набранное до правки вернулось в поле; Escape — отмена без
    базы; отказ базы — сказано словами, изменённый текст остался черновиком;
  • в журнале — сама правка, текстом из чата целиком: «Правка из чата
    выполнена / снова открыта / добавлена в проверку / убрана из проверки:
    «…»» (17.10.2026);
  • галочка правки: в журнале действий «Правка из чата выполнена» с кодом
    пресета и первой строкой, в чате строка «Правка выполнена: «…»»; снятие —
    «снова открыта» там и там; строка-событие ведёт к правке и правкой не
    считается;
  • история: 1203 сообщения — сначала последние 500 и «Показать ранние
    сообщения», дальше 1000 и 1203, кнопка пропадает, на экране остаётся то
    же сообщение; переспрос ленты ранние не теряет;
  • вёрстка на 390 и 1440: строка-событие и кнопка ранних внутри карточки,
    поле нажатия «Изменить» не меньше 44 px.

    python3 check_chat_edit.py
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
  const т = window.__ТАБЛИЦЫ, д = Date.now(), мин = 60e3;
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  const с = (ид, кто, тело, назад, доп) => Object.assign({ id: ид, code: код, author_id: кто, author_name: кто === 'u-проба' ? 'Проба' : 'Ольга Проверкина',
    body: тело, reply_to: null, attachments: [], review_state: null, kind: 'msg', created_at: new Date(д - назад).toISOString() }, доп || {});
  т.preset_messages = [
    с('a0000000-0000-4000-8000-000000000001', 'u-коллега', 'Вальмовую кровлю убрать.\\nИ водосток не забудь.', 30 * мин),
    с('a0000000-0000-4000-8000-000000000002', 'u-проба', 'Старое своё сообщение.', 10 * мин),
    с('a0000000-0000-4000-8000-000000000003', 'u-проба', 'Своё, на которое уже ответили.', 3 * мин),
    с('a0000000-0000-4000-8000-000000000004', 'u-коллега', 'Ответ на твоё.', 2 * мин, { reply_to: 'a0000000-0000-4000-8000-000000000003' }),
    с('a0000000-0000-4000-8000-000000000005', 'u-проба', 'Свежее своё с опечаткой.', 1 * мин),
  ];
  window.__ПРАВКИ = []; window.__ОТМЕТКИ = [];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д - мин).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  window.__RPC.preset_chat_edit = (а) => {
    window.__ПРАВКИ.push(а);
    if (window.__СБОЙ_ПРАВКИ) return { __ошибка: window.__СБОЙ_ПРАВКИ };
    const м_ = т.preset_messages.find(х => х.id === а.p_id);
    if (!м_ || м_.author_id !== 'u-проба') return { __ошибка: 'изменить можно только своё сообщение' };
    if (Date.parse(м_.created_at) < Date.now() - 5 * мин) return { __ошибка: 'изменить можно в первые 5 минут' };
    if (т.preset_messages.some(х => х.reply_to === а.p_id)) return { __ошибка: 'на сообщение уже ответили' };
    м_.edit_history = (м_.edit_history || []).concat([{ body: м_.body, at: м_.edited_at || м_.created_at }]);
    м_.body = а.p_body; м_.edited_at = new Date().toISOString();
    return Object.assign({}, м_);
  };
  // Как preset_chat_mark миграции: стала выполненной или перестала — в ленту
  // строка-событие с первой строкой правки.
  window.__RPC.preset_chat_mark = (а) => {
    window.__ОТМЕТКИ.push(а);
    const м_ = т.preset_messages.find(х => х.id === а.p_id);
    if (!м_) return { __ошибка: 'сообщение не найдено' };
    const было = м_.review_state;
    м_.review_state = а.p_state;
    if ((было === 'done') !== (а.p_state === 'done'))
      т.preset_messages.push({ id: 'e' + Math.random().toString(16).slice(2), code: код, author_id: 'u-проба', author_name: 'Проба',
        body: (м_.body || '').trim().split('\\n')[0].slice(0, 160) || 'Вложение', reply_to: null, attachments: [], review_state: null,
        kind: 'event', event: а.p_state === 'done' ? 'done' : 'reopened', ref: м_.id, created_at: new Date().toISOString() });
    return Object.assign({}, м_);
  };
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  _чатИзменение = null;
}"""

КНОПКИ = """() => [...document.querySelectorAll('#presetChipCard .pc-chm')].map(м_ => ({ ид: м_.getAttribute('data-mid'),
  правка: !!м_.querySelector('[data-act="ch-edit"]'), текст: (м_.querySelector('.pc-chx') || {}).textContent || '',
  изменено: !!м_.querySelector('.pc-ched') }))"""


def кнопки(стр):
    return {к["ид"]: к for к in стр.evaluate(КНОПКИ)}


def прогон(бр, порт, ш, в, полный):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(500)
    к = кнопки(стр)
    if not к:
        плохо(f"{н} лента пуста"); стр.close(); return
    ждали = {"a0000000-0000-4000-8000-000000000005": True, "a0000000-0000-4000-8000-000000000002": False,
             "a0000000-0000-4000-8000-000000000003": False, "a0000000-0000-4000-8000-000000000001": False,
             "a0000000-0000-4000-8000-000000000004": False}
    for ид, надо in ждали.items():
        if к.get(ид, {}).get("правка") != надо:
            плохо(f"{н} «Изменить» у {ид[-1]}: {'нет' if надо else 'есть'}, а должно {'быть' if надо else 'не быть'}")
    if not к.get("a0000000-0000-4000-8000-000000000005", {}).get("правка"):
        стр.close(); return
    # поле нажатия и место кнопки
    кн = стр.evaluate("""() => { const б = document.querySelector('#presetChipCard [data-act="ch-edit"]'); if (!б) return null;
      const р = б.getBoundingClientRect(), с = getComputedStyle(б, '::before'), к = document.getElementById('presetChipCard').getBoundingClientRect();
      return { h: р.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0), вКарточке: р.right <= к.right - 8 && р.left >= к.left + 8 }; }""")
    if not кн or кн["h"] < 43.5 or not кн["вКарточке"]:
        плохо(f"{н} кнопка «Изменить»: {кн}")
    for т in стр.evaluate(ч.ВЁРСТКА):
        плохо(f"{н} лента с «Изменить»: {т}")
    # ── правка ──
    поле = стр.locator("#pcChatText")
    поле.fill("Черновик до правки")
    стр.locator("#presetChipCard [data-act='ch-edit']").click(); стр.wait_for_timeout(250)
    с = стр.evaluate("""() => { const к = document.getElementById('presetChipCard');
      return { поле: к.querySelector('#pcChatText').value, над: (к.querySelector('.pc-chr-ed') || {}).innerText || '',
        скрепка: к.querySelector('[data-act="ch-attach"]').disabled, отпр: к.querySelector('[data-act="ch-send"]').getAttribute('aria-label') }; }""")
    if с["поле"] != "Свежее своё с опечаткой." or "Изменение" not in с["над"] or not с["скрепка"] or с["отпр"] != "Сохранить изменение":
        плохо(f"{н} начало правки: {с}")
    вёрстка_ = стр.evaluate(ч.ВЁРСТКА)
    for т in вёрстка_:
        плохо(f"{н} поле в правке: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-edit-{ш}.png"))
    if not полный:
        if ошибки: плохо(f"{н} ошибки страницы: {ошибки[:3]}")
        стр.close(); return
    # Escape — отмена без базы, черновик вернулся.
    поле.press("Escape"); стр.wait_for_timeout(200)
    с = стр.evaluate("() => ({ поле: document.getElementById('pcChatText').value, над: !!document.querySelector('#presetChipCard .pc-chr-ed'), правок: window.__ПРАВКИ.length })")
    if с["поле"] != "Черновик до правки" or с["над"] or с["правок"]:
        плохо(f"{н} Escape: {с}")
    # Сохранение Enter.
    стр.locator("#presetChipCard [data-act='ch-edit']").click(); стр.wait_for_timeout(200)
    поле.fill("Свежее своё без опечатки.")
    поле.press("Enter"); стр.wait_for_timeout(400)
    с = стр.evaluate("""() => ({ вызов: window.__ПРАВКИ.slice(-1)[0], поле: document.getElementById('pcChatText').value,
      над: !!document.querySelector('#presetChipCard .pc-chr-ed') })""")
    к = кнопки(стр).get("a0000000-0000-4000-8000-000000000005", {})
    if (с["вызов"] or {}).get("p_body") != "Свежее своё без опечатки." or к.get("текст") != "Свежее своё без опечатки." or not к.get("изменено") \
            or с["поле"] != "Черновик до правки" or с["над"]:
        плохо(f"{н} сохранение правки: {с}, сообщение {к}")
    # Отказ базы — словами, текст остался черновиком.
    стр.evaluate("() => { window.__СБОЙ_ПРАВКИ = 'на сообщение уже ответили'; window.__тосты = []; }")
    поле.fill("")
    стр.locator("#presetChipCard [data-act='ch-edit']").click(); стр.wait_for_timeout(200)
    поле.fill("Вторая правка"); поле.press("Enter"); стр.wait_for_timeout(400)
    с = стр.evaluate("() => ({ поле: document.getElementById('pcChatText').value, тост: window.__тосты.slice(-1)[0] || '', над: !!document.querySelector('#presetChipCard .pc-chr-ed') })")
    if с["поле"] != "Вторая правка" or "Не удалось изменить" not in с["тост"] or с["над"]:
        плохо(f"{н} отказ базы при правке: {с}")
    стр.evaluate("() => { window.__СБОЙ_ПРАВКИ = null; _чатЧерновик.текст = ''; document.getElementById('pcChatText').value = ''; }")
    # Ответ каналом закрывает правку сразу.
    стр.evaluate("""(код) => { const к = (window.__КАНАЛЫ || []).filter(х => !х.закрыт && х.слушатели.some(с => с.отбор && с.отбор.table === 'preset_messages'));
      const с = { id: 'a0000000-0000-4000-8000-000000000006', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина', body: 'Отвечаю на свежее.',
        reply_to: 'a0000000-0000-4000-8000-000000000005', attachments: [], review_state: null, kind: 'msg', created_at: new Date().toISOString() };
      window.__ТАБЛИЦЫ.preset_messages.push(с); к.forEach(х => х.слушатели.forEach(л => л.об({ eventType: 'INSERT', new: с }))); }""", код)
    стр.wait_for_timeout(300)
    if кнопки(стр).get("a0000000-0000-4000-8000-000000000005", {}).get("правка"):
        плохо(f"{н} ответ на сообщение не снял «Изменить»")
    # Срок вышел — кнопка пропадает сама.
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ.preset_messages, с = { id: 'a0000000-0000-4000-8000-000000000007', code: код, author_id: 'u-проба', author_name: 'Проба',
        body: 'Почти пять минут.', reply_to: null, attachments: [], review_state: null, kind: 'msg', created_at: new Date(Date.now() - 5 * 60e3 + 1500).toISOString() };
      т.push(с); _чат.сообщения.push(Object.assign({}, с)); отрисоватьЧат(); }""", код)
    стр.wait_for_timeout(200)
    было = кнопки(стр).get("a0000000-0000-4000-8000-000000000007", {}).get("правка")
    стр.wait_for_timeout(2600)
    стало = кнопки(стр).get("a0000000-0000-4000-8000-000000000007", {}).get("правка")
    if not было or стало:
        плохо(f"{н} «Изменить» по сроку: было {было}, через срок {стало}")
    # ── галочка правки: журнал и строка в чате ──
    стр.locator("#presetChipCard .pc-chm[data-mid='a0000000-0000-4000-8000-000000000001'] [data-act='ch-done']").click(); стр.wait_for_timeout(3700)
    с = стр.evaluate("""(код) => { const е = (window.__ТАБЛИЦЫ.events || []).filter(х => х.event_type === 'review_done').slice(-1)[0];
      const ст = [...document.querySelectorAll('#presetChipCard .pc-chev')].map(х => х.innerText.replace(/\\s+/g, ' ').trim());
      return { журнал: е ? { код: String(е.details && е.details.presetCode), что: е.details && е.details.obj } : null, строки: ст,
        правок: правкиЧата().length, кнопокУсобытия: document.querySelectorAll('#presetChipCard .pc-chev .pc-chact').length }; }""", код)
    if not с["журнал"] or с["журнал"]["код"] != код or с["журнал"]["что"] != "Вальмовую кровлю убрать.":
        плохо(f"{н} журнал без «Правка из чата выполнена» с кодом и строкой: {с['журнал']}")
    if not any(т.startswith("Правка выполнена: «Вальмовую кровлю убрать.»") for т in с["строки"]) or с["правок"] != 1 or с["кнопокУсобытия"]:
        плохо(f"{н} строка в чате о выполненной правке: {с}")
    подпись = стр.evaluate("() => AL_ВСЕ_ВИДЫ.review_done + ' / ' + AL_ВСЕ_ВИДЫ.review_reopened")
    if подпись != "Правка из чата выполнена / Правка из чата снова открыта":
        плохо(f"{н} подписи журнала: {подпись}")
    for т in стр.evaluate(ч.ВЁРСТКА):
        плохо(f"{н} лента со строкой-событием: {т}")
    ев = стр.evaluate("""() => { const к = document.getElementById('presetChipCard').getBoundingClientRect();
      return [...document.querySelectorAll('#presetChipCard .pc-chev button, #presetChipCard .pc-chev-w')].filter(э => э.getBoundingClientRect().width)
        .filter(э => { const б = э.getBoundingClientRect(); return б.left < к.left + 8 || б.right > к.right - 8; }).length; }""")
    if ев:
        плохо(f"{н} строка-событие выходит за поле карточки")
    стр.mouse.move(5, 5)
    стр.evaluate("() => { const л = document.getElementById('pcChatList'); л.scrollTop = л.scrollHeight; }")
    стр.screenshot(path=str(СНИМКИ / f"chat-event-{ш}.png"))
    # Строка ведёт к правке.
    стр.locator("#presetChipCard .pc-chev button").first.click(); стр.wait_for_timeout(300)
    if not стр.evaluate("() => { const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid=\"a0000000-0000-4000-8000-000000000001\"]'); return !!м_ && м_.classList.contains('pc-chm-flash'); }"):
        плохо(f"{н} строка-событие не привела к правке")
    # Снятие галочки.
    стр.locator("#presetChipCard .pc-chm[data-mid='a0000000-0000-4000-8000-000000000001'] [data-act='ch-done']").click(); стр.wait_for_timeout(3700)
    с = стр.evaluate("""() => ({ журнал: (window.__ТАБЛИЦЫ.events || []).some(х => х.event_type === 'review_reopened'),
      строка: [...document.querySelectorAll('#presetChipCard .pc-chev')].some(х => /Правка снова открыта: «Вальмовую кровлю убрать\\.»/.test(х.innerText)) })""")
    if not с["журнал"] or not с["строка"]:
        плохо(f"{н} снятие галочки: {с}")
    # ── в журнале — сама правка словами из чата, целиком (17.10.2026) ──
    # Поставить в правки и снять: «добавлена в проверку», «убрана из проверки».
    с2 = "a0000000-0000-4000-8000-000000000002"
    for _ in range(2):
        стр.locator(f"#presetChipCard .pc-chm[data-mid='{с2}'] [data-act='ch-flag']").click(); стр.wait_for_timeout(3400)
    ж = стр.evaluate("""() => (window.__ТАБЛИЦЫ.events || []).filter(х => /^review_/.test(х.event_type))
      .map(х => [х.event_type, ((х.details || {}).rows || []).filter(р => р.k === 'Правка').map(р => р.b)[0] || '',
        typeof названиеСобытияЖурнала === 'function' ? названиеСобытияЖурнала(х) : (AL_ВСЕ_ВИДЫ[х.event_type] || х.event_type)])""")
    полный = "Вальмовую кровлю убрать. И водосток не забудь."
    ждём = [
        ["review_done", полный, "Правка из чата выполнена: «" + полный + "»"],
        ["review_reopened", полный, "Правка из чата снова открыта: «" + полный + "»"],
        ["review_added", "Старое своё сообщение.", "Правка из чата добавлена в проверку: «Старое своё сообщение.»"],
        ["review_removed", "Старое своё сообщение.", "Правка из чата убрана из проверки: «Старое своё сообщение.»"],
    ]
    if ж[-4:] != ждём:
        плохо(f"{н} журнал правок из чата: {ж[-4:]}")
    # Мини-окно, вкладка «Журнал»: правка в самой строке, без повтора под ней.
    стр.locator("#pcTab-l").click(); стр.wait_for_timeout(1500)
    стр_ж = стр.evaluate("""() => [...document.querySelectorAll('#presetChipCard .pc-lg li')].filter(л => /Правка из чата/.test(л.textContent))
      .map(л => [(л.querySelector('.pc-lg-w') || {}).textContent || '', !!л.querySelector('.pc-lg-d'), !!л.querySelector('.pc-lg-chev')])""")
    if not any(w.endswith("Правка из чата выполнена: «" + полный + "»") and not d and not ch for w, d, ch in стр_ж):
        плохо(f"{н} в мини-окне журнал правок из чата: {стр_ж[:4]}")
    if not any("добавлена в проверку: «Старое своё сообщение.»" in w for w, d, ch in стр_ж):
        плохо(f"{н} в мини-окне нет «добавлена в проверку»: {стр_ж[:4]}")
    стр.locator("#pcTab-m").click(); стр.wait_for_timeout(600)
    # ── история ──
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ, д = Date.now();
      т.preset_messages = Array.from({ length: 1203 }, (_, i) => ({ id: 'h' + String(i).padStart(5, '0'), code: код, author_id: i % 2 ? 'u-проба' : 'u-коллега',
        author_name: i % 2 ? 'Проба' : 'Ольга Проверкина', body: 'Сообщение ' + (i + 1), reply_to: null, attachments: [], review_state: null, kind: 'msg',
        created_at: new Date(д - (1203 - i) * 3600e3).toISOString() }));
      _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false }; }""", код)
    стр.evaluate("() => загрузитьЧат(true)"); стр.wait_for_timeout(900)
    сч = lambda: стр.evaluate("() => ({ n: document.querySelectorAll('#presetChipCard .pc-chm').length, кнопка: !!document.querySelector('#presetChipCard [data-act=\"ch-older\"]') })")
    а = сч()
    if а != {"n": 500, "кнопка": True}:
        плохо(f"{н} первая страница истории: {а}")
    стр.evaluate("() => { document.getElementById('pcChatList').scrollTop = 0; }")
    верх = стр.evaluate("() => { const л = document.getElementById('pcChatList'), лр = л.getBoundingClientRect(); const м_ = [...л.querySelectorAll('.pc-chm')].find(х => х.getBoundingClientRect().top >= лр.top - 1); return м_ && м_.getAttribute('data-mid'); }")
    стр.locator("#presetChipCard [data-act='ch-older']").click(); стр.wait_for_timeout(900)
    б = сч()
    на_месте = стр.evaluate("(ид) => { const л = document.getElementById('pcChatList'), лр = л.getBoundingClientRect(), м_ = л.querySelector('.pc-chm[data-mid=\"' + ид + '\"]'); if (!м_) return false; const р = м_.getBoundingClientRect(); return р.top >= лр.top - 2 && р.top <= лр.bottom; }", верх)
    if б != {"n": 1000, "кнопка": True} or not на_месте:
        плохо(f"{н} вторая страница истории: {б}, сообщение на месте {на_месте}")
    стр.locator("#presetChipCard [data-act='ch-older']").click(); стр.wait_for_timeout(900)
    в_ = сч()
    if в_ != {"n": 1203, "кнопка": False}:
        плохо(f"{н} вся история: {в_}")
    стр.evaluate("() => загрузитьЧат(true, true)"); стр.wait_for_timeout(900)
    if сч()["n"] != 1203:
        плохо(f"{н} переспрос ленты потерял ранние: {сч()}")
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
    print("Чисто: «Изменить» только у своего свежего без ответа и пропадает по сроку и по ответу, правка Enter, Escape и отказ базы, "
          "галочка правки в журнале и строкой в чате, вся история страницами без потерь, вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
