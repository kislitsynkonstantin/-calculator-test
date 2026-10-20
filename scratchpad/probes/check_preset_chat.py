#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чат пресета — пятая вкладка мини-окна.

Константин 17.10.2026: «Давай сначала сделаем чат (скр2) пресета. В чат добавь
только ещё опцию грузить файлы и через вставку добавлять скриншоты/фото. В чате
возле каждого сообщения при добавлении добавь небольшую иконку «Отразить в
правках» (скр1). И там рядом кнопку выполнено. В чате должна быть кнопка
«Ответить» на сообщение, чтобы копировалась строка первая сообщения, на которое
отвечаем и по нажатию можно было на него вернуться». Скриншоты — варианты А и Б
макета mockups/approval-flow-v1.html.

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • вкладок пять, «Чат» последней; все в одну строку, внутри карточки, с
    зазором и без обрезанных подписей; непрочитанное чужое — числом на
    вкладке, открытая вкладка его читает (preset_chat_read с временем
    последнего) и число снимает;
  • лента: дни, своё справа, чужое слева, у каждого сообщения «Ответить»,
    значок «Отразить в правках» и «Выполнено»; поле нажатия каждой кнопки не
    меньше 44 px по высоте, а нарисованы они тише пузыря;
  • Enter отправляет (на компьютере), строка уходит в базу с кодом пресета,
    поле пустеет, лента стоит на последнем;
  • «Ответить» — над полем первая строка отвечаемого, последнее сообщение
    под неё не уезжает; отправленное несёт reply_to, в пузыре цитата той же строкой; нажатие цитаты прокручивает к
    исходному и подсвечивает его;
  • снимок из буфера прикрепляется сам, с именем «Снимок …», уходит в
    корзину preset-chat по пути «код/автор/сообщение/1.png», в пузыре —
    картинкой; вставленный текст картинку не прикрепляет;
  • файл скрепкой — в пузыре ссылкой с настоящим именем и размером, ссылка
    скачивает под этим именем; файл больше 20 МБ не прикрепляется;
  • «Отразить в правках» — подсвечен значок, подписи нет, в базу через 3 с; пункт во вкладке «Проверка» над
    автоматическими («Правки из чата 0 из 1»), +1 к числу вкладки и значка;
    галочка там — «выполнено» в чате и «1 из 1»; текст пункта ведёт к
    сообщению в чате; «Выполнено» у сообщения не в правках ставит его в них
    сразу сделанным;
  • новое сообщение каналом базы — в ленте; пока открыта другая вкладка —
    числом на «Чате»;
  • сбой отметки возвращает прежнее; сбой загрузки файла оставляет сообщение
    в ленте с «Не отправлено», поле свободно; «Повторить» досылает его,
    «Убрать» снимает (17.10.2026: отправка — сразу, файлы догружаются в ленте);
  • вёрстка на 390 и 1440, днём и ночью: карточка в кадре, ничего не выходит
    за поле карточки, лента вбок не ходит, длинная строка без пробелов
    переносится.

    python3 check_preset_chat.py
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
  // Вкладки: одна строка, внутри поля карточки, зазор, подписи целиком.
  const вк = [...к.querySelectorAll('.pc-tab')];
  if (new Set(вк.map(т => Math.round(т.getBoundingClientRect().top))).size > 1) н.push('вкладки не в одну строку');
  вк.forEach((т, i) => {
    const б = т.getBoundingClientRect();
    if (б.left < внутр.l - .5 || б.right > внутр.r + .5) н.push('вкладка «' + т.innerText.trim() + '» за полем карточки');
    if (i && б.left - вк[i - 1].getBoundingClientRect().right < 6) н.push('вкладки ближе 6 px: «' + вк[i - 1].innerText.trim() + '» и «' + т.innerText.trim() + '»');
    // Обрезка — по самому тексту: невидимое поле нажатия scrollWidth тоже считает.
    const д = document.createRange(); д.selectNodeContents(т);
    if ([...д.getClientRects()].some(х => х.width > 0 && (х.left < б.left - .5 || х.right > б.right + .5))) н.push('подпись вкладки «' + т.innerText.replace(/\\s+/g, ' ').trim() + '» обрезана');
  });
  const пане = к.querySelector('.pc-pane.on'), пр = пане ? пане.getBoundingClientRect() : null;
  const лента = к.querySelector('#pcChatList');
  if (лента && лента.scrollWidth > лента.clientWidth + 1) н.push('лента чата шире себя на ' + (лента.scrollWidth - лента.clientWidth) + ' px');
  const лр = лента ? лента.getBoundingClientRect() : null;
  const видна = э => { const б = э.getBoundingClientRect(); return б.width > 0 && б.height > 0 && getComputedStyle(э).visibility !== 'hidden'; };
  к.querySelectorAll('.pc-chb, .pc-chact button, .pc-chin, .pc-chr, .pc-chfi, .pc-pr li, .pc-grp, .pc-chq, .pc-chfl, .pc-chim').forEach(э => {
    if (!видна(э)) return;
    const б = э.getBoundingClientRect();
    if (лр && лента.contains(э) && (б.bottom < лр.top || б.top > лр.bottom)) return;
    if (пр && пане.contains(э) && (б.bottom < пр.top || б.top > пр.bottom)) return;
    const имя = (э.getAttribute('data-act') || э.className || э.tagName) + ' «' + (э.innerText || '').trim().slice(0, 16) + '»';
    if (б.left < внутр.l - .5 || б.right > внутр.r + .5) н.push(имя + ' за полем карточки: ' + Math.round(б.left - внутр.l) + '/' + Math.round(внутр.r - б.right));
  });
  // Поля нажатия: кнопки под сообщением, скрепка, отправка, галочка правки.
  к.querySelectorAll('.pc-chact button, .pc-chclip, .pc-chsend, .pc-pr-box, .pc-chr button, .pc-chfi button').forEach(э => {
    if (!видна(э)) return;
    const б = э.getBoundingClientRect(), с = getComputedStyle(э, '::before');
    const h = б.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
    const w = б.width - (parseFloat(с.left) || 0) - (parseFloat(с.right) || 0);
    if (h < 43.5) н.push('поле нажатия ' + (э.getAttribute('data-act') || э.className) + ' по высоте ' + Math.round(h) + ' px');
    if (w < 37.5) н.push('поле нажатия ' + (э.getAttribute('data-act') || э.className) + ' по ширине ' + Math.round(w) + ' px');
  });
  // Кнопка под сообщением не касается своего пузыря и следующего.
  к.querySelectorAll('.pc-chm').forEach(м_ => {
    const пуз = м_.querySelector('.pc-chb'), ряд = м_.querySelector('.pc-chact');
    if (!пуз || !ряд || !видна(ряд)) return;
    const з = ряд.getBoundingClientRect().top - пуз.getBoundingClientRect().bottom;
    if (з < 1) н.push('кнопки сообщения прилипли к пузырю: ' + Math.round(з) + ' px');
    const след = м_.nextElementSibling;
    if (след && след.classList.contains('pc-chm')) {
      const з2 = след.getBoundingClientRect().top - ряд.getBoundingClientRect().bottom;
      if (з2 < 4) н.push('кнопки сообщения прилипли к следующему: ' + Math.round(з2) + ' px');
    }
  });
  return н;
}"""


def вёрстка(стр, н, что):
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {что}: {т}")


ДАННЫЕ_ЧАТА = """(код) => {
  const т = window.__ТАБЛИЦЫ;
  const сут = 24 * 3600 * 1000, д = Date.now();
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  т.preset_messages = [
    { id: '11111111-1111-4111-8111-111111111111', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина',
      body: 'Вальмовую кровлю убрать — у этого проекта двускатная.\\nИ водосток не забудь.', reply_to: null, attachments: [], review_state: null,
      created_at: new Date(д - сут - 3600e3).toISOString() },
    { id: '22222222-2222-4222-8222-222222222222', code: код, author_id: 'u-проба', author_name: 'Проба', body: 'Клиент просил вальмовую, это его решение. Водосток добавил.',
      reply_to: '11111111-1111-4111-8111-111111111111', attachments: [], review_state: null, created_at: new Date(д - сут).toISOString() },
    { id: '33333333-3333-4333-8333-333333333333', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина',
      body: 'Тогда в примечании к кровле напиши, что по желанию заказчика.', reply_to: null, attachments: [], review_state: null,
      created_at: new Date(д - 600e3).toISOString() },
    { id: '44444444-4444-4444-8444-444444444444', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина',
      body: 'Длинная-строка-без-пробелов-https://test.calculator.baniamsk.ru/mockups/approval-flow-v1.html?очень=длинный&адрес=чтобы-проверить-перенос-внутри-пузыря',
      reply_to: null, attachments: [], review_state: null, created_at: new Date(д - 300e3).toISOString() },
  ];
  // Последнее прочитанное — до двух свежих сообщений коллеги.
  window.__ЧИТАЛ = [];
  window.__ОТМЕТКИ = [];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д - сут + 60e3).toISOString() : null;
  window.__RPC.preset_chat_read = (а) => { window.__ЧИТАЛ.push(а); return null; };
  window.__RPC.preset_chat_mark = (а) => {
    window.__ОТМЕТКИ.push(а);
    if (window.__СБОЙ_ОТМЕТКИ) throw new Error('нет связи');
    const с = т.preset_messages.find(х => х.id === а.p_id);
    if (!с) return null;
    с.review_state = а.p_state; с.done_by = а.p_state === 'done' ? 'u-проба' : null;
    return Object.assign({}, с);
  };
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
}"""

СОСТОЯНИЕ = """() => { const к = document.getElementById('presetChipCard');
  const вк = [...к.querySelectorAll('.pc-tab')].map(т => т.innerText.replace(/\\s+/g, ' ').trim());
  const лента = к.querySelector('#pcChatList');
  return { вкладки: вк, чатСчёт: +(((к.querySelector('#pcTab-m .pc-cnt') || {}).textContent) || 0),
    провСчёт: +(((к.querySelector('#pcTab-c .pc-cnt') || {}).textContent) || 0),
    значок: +(((document.querySelector('#presetChip .pc-ckn') || {}).textContent) || 0),
    сообщений: к.querySelectorAll('.pc-chm').length, дни: [...к.querySelectorAll('.pc-chday')].map(д => д.textContent),
    мои: к.querySelectorAll('.pc-chm.me').length,
    уДна: лента ? лента.scrollTop + лента.clientHeight >= лента.scrollHeight - 4 : null,
    текст: к.innerText.replace(/\\s+/g, ' ') }; }"""


def начать(бр, порт, ш, в, ночь):
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
    return стр, ошибки


def вкладка(стр, в):
    стр.locator(f"#pcTab-{в}").click(); стр.wait_for_timeout(450)


def открыть(стр):
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.locator("#presetChip .pc-body").click()
    стр.wait_for_timeout(400)


def прогон(бр, порт, ш, в, ночь, полный):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = начать(бр, порт, ш, в, ночь)
    шрифт = стр.evaluate("""() => { const и = document.createElement('span'); и.style.cssText = 'position:absolute;visibility:hidden;font-size:40px;white-space:nowrap'; и.textContent = 'Проверка чата пресета';
      document.body.appendChild(и); const шир = ш => { и.style.fontFamily = ш; return и.getBoundingClientRect().width; };
      const д = Math.abs(шир("'Geologica',monospace") - шир('monospace')) > .5; и.remove(); return д; }""")
    if not шрифт:
        плохо(f"{н} Geologica не легла — ширины меряются подменным шрифтом"); стр.close(); return
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ_ЧАТА, код)
    открыть(стр); стр.wait_for_timeout(500)
    с = стр.evaluate(СОСТОЯНИЕ)
    # С 20.10.2026 вкладок четыре: «Сводка» — внутри «Пресета».
    if len(с["вкладки"]) != 4 or not с["вкладки"][-1].startswith("Чат"):
        плохо(f"{н} вкладок не четыре или «Чат» не последняя: {с['вкладки']}"); стр.close(); return
    if с["чатСчёт"] != 2:
        плохо(f"{н} на вкладке «Чат» не 2 непрочитанных, а {с['чатСчёт']}")
    вёрстка(стр, н, "«Пресет», пять вкладок")
    вкладка(стр, "m"); стр.wait_for_timeout(500)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["сообщений"] != 4 or с["мои"] != 1 or "Вчера" not in с["дни"] or "Сегодня" not in с["дни"] or not с["уДна"]:
        плохо(f"{н} лента: {с['сообщений']} сообщений, своих {с['мои']}, дни {с['дни']}, у дна {с['уДна']}")
    if с["чатСчёт"]:
        плохо(f"{н} открытая вкладка «Чат» не сняла число непрочитанных: {с['чатСчёт']}")
    читал = стр.evaluate("() => window.__ЧИТАЛ")
    if not читал or читал[-1].get("p_code") != код:
        плохо(f"{н} открытая лента не отметила прочитанное в базе: {читал}")
    кн = стр.evaluate("""() => { const м_ = document.querySelector('#presetChipCard .pc-chm:not(.me)');
      return м_ ? [...м_.querySelectorAll('.pc-chact button')].map(б => (б.getAttribute('aria-label') || б.innerText).trim()) : []; }""")
    if кн != ["Ответить", "В правки", "Выполнено"]:
        плохо(f"{н} кнопки под сообщением: {кн}")
    # Вес: кнопки под сообщением мельче текста сообщения.
    вес = стр.evaluate("""() => { const к = document.getElementById('presetChipCard');
      const т = parseFloat(getComputedStyle(к.querySelector('.pc-chx')).fontSize), б = parseFloat(getComputedStyle(к.querySelector('.pc-chact button')).fontSize);
      const ц = getComputedStyle(к.querySelector('.pc-chact button')).color, цт = getComputedStyle(к.querySelector('.pc-chx')).color;
      return { т, б, разныйЦвет: ц !== цт, высота: к.querySelector('.pc-chact button').getBoundingClientRect().height }; }""")
    if not (вес["б"] < вес["т"] and вес["разныйЦвет"] and вес["высота"] <= 26):
        плохо(f"{н} кнопки под сообщением весят как текст: {вес}")
    вёрстка(стр, н, "«Чат»")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-{ш}{'-n' if ночь else ''}.png"))
    if not полный:
        if ошибки: плохо(f"{н} ошибки страницы: {ошибки[:3]}")
        стр.close(); return
    # ── отправка Enter ──
    поле = стр.locator("#pcChatText")
    поле.click(); поле.fill("Добавил примечание к кровле.")
    стр.wait_for_timeout(100)
    if стр.evaluate("() => document.querySelector('#presetChipCard [data-act=\"ch-send\"]').disabled"):
        плохо(f"{н} кнопка отправки выключена при набранном тексте")
    поле.press("Enter"); стр.wait_for_timeout(500)
    о = стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ.preset_messages, п = т[т.length - 1];
      const к = document.getElementById('presetChipCard'), л = к.querySelector('#pcChatList');
      return { тело: п.body, код: п.code, последний: (к.querySelector('.pc-chm:last-of-type .pc-chx') || {}).textContent || '',
               поле: к.querySelector('#pcChatText').value, уДна: л.scrollTop + л.clientHeight >= л.scrollHeight - 4,
               фокус: document.activeElement && document.activeElement.id }; }""", код)
    if о["тело"] != "Добавил примечание к кровле." or о["код"] != код or о["последний"] != о["тело"] or о["поле"] or not о["уДна"]:
        плохо(f"{н} отправка Enter: {о}")
    # ── ответ ──
    стр.locator("#presetChipCard .pc-chm[data-mid='33333333-3333-4333-8333-333333333333'] [data-act='ch-reply']").click(); стр.wait_for_timeout(250)
    пл = стр.evaluate("() => (document.querySelector('#presetChipCard .pc-chr') || {}).innerText || ''")
    if "Ответ: Ольга П." not in пл or "Тогда в примечании к кровле" not in пл:
        плохо(f"{н} «Ответить»: над полем не первая строка отвечаемого: «{пл}»")
    if стр.evaluate("() => document.activeElement && document.activeElement.id") != "pcChatText":
        плохо(f"{н} «Ответить» не перевёл фокус в поле")
    # Лента стояла на последнем — и стоит на нём, хотя над полем встал «Ответ»
    # и ленте стало меньше места (17.10.2026: последнее уезжало под плашку).
    стр.wait_for_timeout(150)
    if not стр.evaluate(СОСТОЯНИЕ)["уДна"]:
        плохо(f"{н} «Ответить»: плашка над полем сдвинула последнее сообщение под себя")
    вёрстка(стр, н, "«Чат», ответ над полем")
    стр.locator("#pcChatText").fill("Написал.")
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(500)
    о = стр.evaluate("""() => { const т = window.__ТАБЛИЦЫ.preset_messages, п = т[т.length - 1], к = document.getElementById('presetChipCard');
      const м_ = к.querySelector('.pc-chm[data-mid="' + п.id + '"]');
      return { на: п.reply_to, цитата: м_ && м_.querySelector('.pc-chq') ? м_.querySelector('.pc-chq').innerText : '', плашка: !!к.querySelector('.pc-chr') }; }""")
    if о["на"] != "33333333-3333-4333-8333-333333333333" or "Тогда в примечании" not in о["цитата"] or о["плашка"]:
        плохо(f"{н} отправленный ответ: {о}")
    # Цитата ведёт к исходному: лента прокручена к нему, оно подсвечено.
    стр.evaluate("() => { const л = document.querySelector('#pcChatList'); л.scrollTop = л.scrollHeight; }")
    стр.locator("#presetChipCard .pc-chm[data-mid='22222222-2222-4222-8222-222222222222'] .pc-chq").click(); стр.wait_for_timeout(250)
    ц = стр.evaluate("""() => { const л = document.querySelector('#pcChatList'), м_ = л.querySelector('.pc-chm[data-mid="11111111-1111-4111-8111-111111111111"]');
      const лр = л.getBoundingClientRect(), мр = м_.getBoundingClientRect();
      return { видно: мр.top >= лр.top - 1 && мр.bottom <= лр.bottom + 1, свет: м_.classList.contains('pc-chm-flash') }; }""")
    if not ц["видно"] or not ц["свет"]:
        плохо(f"{н} цитата не привела к исходному сообщению: {ц}")
    # ── снимок вставкой ──
    стр.evaluate("""async () => {
      const х = document.createElement('canvas'); х.width = 640; х.height = 400; const г = х.getContext('2d'); г.fillStyle = '#2a8f97'; г.fillRect(0, 0, 640, 400);
      const блоб = await new Promise(р => х.toBlob(р, 'image/png'));
      const дт = new DataTransfer(); дт.items.add(new File([блоб], 'image.png', { type: 'image/png' }));
      const п = document.getElementById('pcChatText'); п.focus();
      п.dispatchEvent(new ClipboardEvent('paste', { clipboardData: дт, bubbles: true, cancelable: true })); }""")
    стр.wait_for_timeout(500)
    фл = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-chfi')].map(ф => ({ имя: ф.innerText.trim(), картинка: !!ф.querySelector('img') }))")
    if len(фл) != 1 or not re.match(r"^Снимок \d\d\.\d\d \d\d-\d\d\.png$", фл[0]["имя"]) or not фл[0]["картинка"]:
        плохо(f"{н} снимок из буфера не прикрепился как «Снимок …png» с миниатюрой: {фл}")
    вёрстка(стр, н, "«Чат», снимок прикреплён")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-attach-{ш}{'-n' if ночь else ''}.png"))
    # Вставленный текст картинку не прикрепляет.
    стр.evaluate("""() => { const дт = new DataTransfer(); дт.setData('text/plain', 'текст из таблицы');
      дт.items.add(new File([new Uint8Array([137, 80, 78, 71])], 'image.png', { type: 'image/png' }));
      document.getElementById('pcChatText').dispatchEvent(new ClipboardEvent('paste', { clipboardData: дт, bubbles: true, cancelable: true })); }""")
    стр.wait_for_timeout(300)
    if стр.evaluate("() => document.querySelectorAll('#presetChipCard .pc-chfi').length") != 1:
        плохо(f"{н} вставка текста прикрепила вместе с ним картинку")
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(600)
    о = стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ.preset_messages, п = т[т.length - 1], з = window.__ЗАГРУЖЕНО[window.__ЗАГРУЖЕНО.length - 1] || {};
      const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid="' + п.id + '"]');
      const и = м_ && м_.querySelector('.pc-chim img');
      return { вложения: п.attachments, корзина: з.корзина, путь: з.путь, тип: з.тип, картинка: !!и, ш: и ? Math.round(и.getBoundingClientRect().width) : 0, свой: п.id }; }""", код)
    в_ = (о["вложения"] or [{}])[0]
    if (о["корзина"] != "preset-chat" or not (о["путь"] or "").startswith(f"{код}/u-проба/{о['свой']}/1.png") or о["тип"] != "image/png"
            or len(о["вложения"]) != 1 or в_.get("w") != 640 or в_.get("h") != 400 or not в_.get("name", "").startswith("Снимок") or not о["картинка"]):
        плохо(f"{н} отправка снимка: {о}")
    # ── файл скрепкой ──
    стр.locator("#pcChatFile").set_input_files(files=[{"name": "Смета клиента.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 " + b"0" * 4000}])
    стр.wait_for_timeout(300)
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(700)
    ф = стр.evaluate("""() => { const т = window.__ТАБЛИЦЫ.preset_messages, п = т[т.length - 1];
      const а = document.querySelector('#presetChipCard .pc-chm[data-mid="' + п.id + '"] a.pc-chfl');
      return { имя: а ? а.querySelector('.pc-chfl-n').textContent : '', размер: а ? а.querySelector('.pc-chfl-s').textContent : '',
               скачать: а ? а.getAttribute('download') : '', адрес: а ? а.getAttribute('href') : '', путь: (п.attachments[0] || {}).path || '' }; }""")
    if ф["имя"] != "Смета клиента.pdf" or ф["размер"] != "4 КБ" or ф["скачать"] != "Смета клиента.pdf" or "download=" not in ф["адрес"] or not ф["путь"].endswith("/1.pdf"):
        плохо(f"{н} файл скрепкой: {ф}")
    # Больше 20 МБ — не прикрепляется, говорит словами.
    стр.evaluate("""() => { const ф = new File([new Uint8Array(8)], 'Огромный.zip'); Object.defineProperty(ф, 'size', { value: 21 * 1024 * 1024 });
      добавитьФайлыВЧат([ф], false); }""")
    стр.wait_for_timeout(250)
    if стр.evaluate("() => document.querySelectorAll('#presetChipCard .pc-chfi').length") or not any("больше 20 МБ" in т for т in стр.evaluate("() => window.__тосты")):
        плохо(f"{н} файл больше 20 МБ прикрепился или промолчал")
    # ── отразить в правках ──
    до = стр.evaluate(СОСТОЯНИЕ)
    # Отметка уходит в базу, когда 3 секунды на «Отменить» вышли (18.10.2026).
    стр.locator("#presetChipCard .pc-chm[data-mid='11111111-1111-4111-8111-111111111111'] [data-act='ch-flag']").click(); стр.wait_for_timeout(3400)
    с = стр.evaluate("""() => { const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid="11111111-1111-4111-8111-111111111111"]');
      return { метка: (м_.querySelector('.pc-cht') || {}).textContent || '', нажат: м_.querySelector('[data-act="ch-flag"]').getAttribute('aria-pressed'), отметка: window.__ОТМЕТКИ.slice(-1)[0] }; }""")
    после = стр.evaluate(СОСТОЯНИЕ)
    if с["метка"] or с["нажат"] != "true" or (с["отметка"] or {}).get("p_state") != "open":
        плохо(f"{н} «Отразить в правках»: {с}")
    if после["провСчёт"] != до["провСчёт"] + 1 or после["значок"] != до["значок"] + 1:
        плохо(f"{н} правка не прибавилась к числу «Проверки» и значка: вкладка {до['провСчёт']}→{после['провСчёт']}, значок {до['значок']}→{после['значок']}")
    вкладка(стр, "c")
    п = стр.evaluate("""() => { const к = document.getElementById('presetChipCard');
      return { группы: [...к.querySelectorAll('.pc-grp')].map(г => г.innerText.replace(/\\s+/g, ' ').trim()), пункты: [...к.querySelectorAll('.pc-pr li')].map(л => л.innerText.replace(/\\s+/g, ' ').trim()) }; }""")
    if len(п["группы"]) != 2 or not re.match(r"(?i)^Правки из чата 1 осталась$", п["группы"][0]) or not re.match(r"(?i)^Автоматическая проверка \d+$", п["группы"][1]) or len(п["пункты"]) != 1 or "Вальмовую кровлю убрать" not in п["пункты"][0] or "Ольга П." not in п["пункты"][0]:
        плохо(f"{н} «Проверка»: правки из чата не над автоматическими: {п}")
    вёрстка(стр, н, "«Проверка» с правкой из чата")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-check-{ш}{'-n' if ночь else ''}.png"))
    стр.locator("#presetChipCard .pc-pr-box").click(); стр.wait_for_timeout(400)
    п = стр.evaluate("""() => { const к = document.getElementById('presetChipCard'), б = к.querySelector('.pc-pr-box');
      return { группа: (к.querySelector('.pc-grp') || {}).innerText || '', отмечен: б && б.getAttribute('aria-checked'), зачёркнут: getComputedStyle(к.querySelector('.pc-pr-tx')).textDecorationLine,
               счёт: +(((к.querySelector('#pcTab-c .pc-cnt') || {}).textContent) || 0) }; }""")
    if "готово" not in п["группа"].lower() or п["отмечен"] != "true" or "line-through" not in п["зачёркнут"] or п["счёт"] != до["провСчёт"]:
        плохо(f"{н} галочка правки в «Проверке»: {п} (до отметки было {до['провСчёт']})")
    стр.locator("#presetChipCard .pc-pr-t").click(); стр.wait_for_timeout(500)
    ч = стр.evaluate("""() => { const к = document.getElementById('presetChipCard'), м_ = к.querySelector('.pc-chm[data-mid="11111111-1111-4111-8111-111111111111"]');
      return { вкладка: _пкВкладка, метка: м_ ? (м_.querySelector('.pc-cht') || {}).textContent : '', выполнено: м_ ? м_.querySelector('[data-act="ch-done"]').getAttribute('aria-pressed') : '',
               свет: м_ ? м_.classList.contains('pc-chm-flash') : false }; }""")
    if ч["вкладка"] != "m" or ч["метка"] != "выполнено" or ч["выполнено"] != "true" or not ч["свет"]:
        плохо(f"{н} пункт правки не привёл к сообщению или чат не показал «выполнено»: {ч}")
    # «Выполнено» у сообщения не в правках — сразу сделанной правкой.
    стр.locator("#presetChipCard .pc-chm[data-mid='33333333-3333-4333-8333-333333333333'] [data-act='ch-done']").click(); стр.wait_for_timeout(3400)
    if (стр.evaluate("() => window.__ОТМЕТКИ.slice(-1)[0]") or {}).get("p_state") != "done" or len(стр.evaluate("() => правкиЧата()")) != 2:
        плохо(f"{н} «Выполнено» у сообщения не в правках не поставило его сделанной правкой")
    # Сбой отметки — отметка возвращается и сказано словами.
    стр.evaluate("() => { window.__СБОЙ_ОТМЕТКИ = true; }")
    стр.locator("#presetChipCard .pc-chm[data-mid='44444444-4444-4444-8444-444444444444'] [data-act='ch-flag']").click(); стр.wait_for_timeout(3400)
    сб = стр.evaluate("() => ({ состояние: (сообщениеЧата('44444444-4444-4444-8444-444444444444') || {}).review_state, тост: window.__тосты.slice(-1)[0] || '' })")
    if сб["состояние"] or "Не удалось отметить" not in сб["тост"]:
        плохо(f"{н} сбой отметки: {сб}")
    стр.evaluate("() => { window.__СБОЙ_ОТМЕТКИ = false; }")
    # Сбой загрузки — сообщение остаётся в ленте «Не отправлено», поле свободно.
    СБОЙ = """() => { const к = document.getElementById('presetChipCard'), м_ = [...к.querySelectorAll('.pc-chm')].pop();
      return { строк: window.__ТАБЛИЦЫ.preset_messages.length, поле: document.getElementById('pcChatText').value, полеВыкл: document.getElementById('pcChatText').disabled,
        файлов: к.querySelectorAll('.pc-chfi').length, тост: window.__тосты.slice(-1)[0] || '', текст: м_ ? (м_.querySelector('.pc-chx') || {}).textContent : '',
        сбой: м_ ? (м_.querySelector('.pc-chfail') || {}).innerText || '' : '', ответить: !!(м_ && м_.querySelector('[data-act="ch-reply"]')) }; }"""
    def с_файлом(текст):
        стр.locator("#pcChatFile").set_input_files(files=[{"name": "план.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"0" * 100}])
        стр.locator("#pcChatText").fill(текст)
        стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(500)
    стр.evaluate("() => { window.__СБОЙ_ЗАГРУЗКИ = 'нет места'; }")
    было = стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.length")
    с_файлом("С файлом")
    сз = стр.evaluate(СБОЙ)
    if (сз["строк"] != было or сз["поле"] or сз["полеВыкл"] or сз["файлов"] or "Не удалось отправить" not in сз["тост"]
            or сз["текст"] != "С файлом" or "Не отправлено" not in сз["сбой"] or сз["ответить"]):
        плохо(f"{н} сбой загрузки файла: {сз}")
    вёрстка(стр, н, "«Чат», сообщение «Не отправлено»")
    # «Повторить» после сбоя досылает: строка в базе с файлом, «Не отправлено» ушло.
    стр.evaluate("() => { window.__СБОЙ_ЗАГРУЗКИ = null; }")
    стр.locator("#presetChipCard .pc-chfail [data-act='ch-resend']").click(); стр.wait_for_timeout(600)
    пв = стр.evaluate(СБОЙ)
    последняя = стр.evaluate("() => { const т = window.__ТАБЛИЦЫ.preset_messages, п = т[т.length - 1]; return { тело: п.body, файлов: (п.attachments || []).length, флаги: Object.keys(п).filter(к => к.startsWith('__')) }; }")
    if пв["строк"] != было + 1 or пв["сбой"] or not пв["ответить"] or последняя["тело"] != "С файлом" or последняя["файлов"] != 1 or последняя["флаги"]:
        плохо(f"{н} «Повторить» после сбоя: {пв}, в базе {последняя}")
    # «Убрать» снимает несданное, в базу ничего не уходит.
    стр.evaluate("() => { window.__СБОЙ_ЗАГРУЗКИ = 'нет места'; }")
    с_файлом("Уберу")
    стр.evaluate("() => { window.__СБОЙ_ЗАГРУЗКИ = null; }")
    стр.locator("#presetChipCard .pc-chfail [data-act='ch-drop']").click(); стр.wait_for_timeout(300)
    уб = стр.evaluate(СБОЙ)
    if уб["строк"] != было + 1 or уб["сбой"] or уб["текст"] == "Уберу":
        плохо(f"{н} «Убрать» несданное: {уб}")
    # ── канал базы: новое сообщение ──
    вкладка(стр, "p")
    стр.evaluate("""(код) => { const к = (window.__КАНАЛЫ || []).filter(х => !х.закрыт && х.слушатели.some(с => с.отбор && с.отбор.table === 'preset_messages' && с.отбор.filter === 'code=eq.' + код));
      const с = { id: '55555555-5555-4555-8555-555555555555', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина', body: 'Согласую после примечания.', reply_to: null, attachments: [], review_state: null, created_at: new Date().toISOString() };
      к.forEach(х => х.слушатели.forEach(л => л.об({ eventType: 'INSERT', new: с })));
      window.__каналов = к.length; }""", код)
    стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if стр.evaluate("() => window.__каналов") != 1 or с["чатСчёт"] != 1:
        плохо(f"{н} сообщение каналом: каналов {стр.evaluate('() => window.__каналов')}, число на «Чате» {с['чатСчёт']}")
    вкладка(стр, "m")
    if "Согласую после примечания." not in стр.evaluate(СОСТОЯНИЕ)["текст"]:
        плохо(f"{н} сообщение, пришедшее каналом, не в ленте")
    вёрстка(стр, н, "«Чат» после переписки")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-full-{ш}{'-n' if ночь else ''}.png"))
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
    print("Чисто: четыре вкладки в одну строку, лента с днями и своим справа, отправка Enter, ответ с первой строкой и возвратом к исходному, "
          "снимок вставкой и файл скрепкой в закрытую корзину, «Отразить в правках» и «Выполнено» в чате и в «Проверке», "
          "сообщение каналом, сбои отметки и загрузки, вёрстка на 390 и 1440 днём и ночью.")


if __name__ == "__main__":
    главная()
