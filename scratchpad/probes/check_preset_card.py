#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карточка пресета во вкладках: «Пресет / Журнал / Проверка».

Константин 28.09.2026: «Внедряй новые варианты макетов. Добавь сразу действия
в пресете все с полоской. Проработай чек-лист: внеси на проверку только те
пункты, в которых ты уверен». Итоговый макет — mockups/preset-card-final.html.

Проба держит:
  • свой пресет из «Моих» — значок «Мой пресет» с облаком; без связи — экран
    тёплым цветом и тёплая строка в карточке; опубликованный — глобус и замок;
  • карточка: три вкладки, в строке «Опубликовать», звезда и «Все пресеты» —
    одной строкой, с зазором от поля карточки, поле нажатия 44 px;
  • «Мои / Общие»: переход в обе стороны; открытие замка из «Моих» переводит
    пресет в «Общие», и «Мои» при открытом замке недоступны;
  • «⋯» → «Снять с публикации» → подтверждение в карточке (без слов о клиенте,
    фокус на «Отмене», Escape снимает по слою) → снятие; открытый в «Общих»
    пресет после снятия открывается в «Моих»;
  • «Журнал»: все действия этого пресета — и только его — листаются внутри,
    «Открыть в журнале действий» ведёт в журнал с фильтром по пресету за всё
    время;
  • «Проверка»: замечание о водостоке при фасаде без водостока (стоп), о
    Rockwool в своей опции; нажатие ведёт к разделу и подсвечивает его;
    отмеченный водосток замечание снимает; счётчик на вкладке равен числу
    замечаний;
  • чужой общий — серым, без меню «⋯»;
  • вёрстка на 320, 390, 768 и 1440, днём и ночью: карточка в кадре, ничего не
    выходит за поле карточки и не обрезано, страница не едет вбок.

    python3 check_preset_card.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


# Вёрстка карточки: кадр, поле карточки, обрезка, поля нажатия, одна строка.
ВЁРСТКА = """() => {
  const к = document.getElementById('presetChipCard');
  const r = к.getBoundingClientRect(), cs = getComputedStyle(к);
  const внутр = { l: r.left + parseFloat(cs.borderLeftWidth) + parseFloat(cs.paddingLeft),
                  r: r.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight),
                  b: r.bottom - parseFloat(cs.borderBottomWidth) - parseFloat(cs.paddingBottom) };
  const н = [];
  if (r.left < 4 || r.right > innerWidth - 4 || r.top < 4 || r.bottom > innerHeight) н.push('карточка вне кадра ' + JSON.stringify([r.left, r.top, r.right, r.bottom].map(Math.round)));
  if (document.documentElement.scrollWidth > innerWidth + 1) н.push('страница шире экрана: ' + document.documentElement.scrollWidth);
  const видна = э => { const б = э.getBoundingClientRect(); return б.width > 0 && б.height > 0 && getComputedStyle(э).visibility !== 'hidden'; };
  const пане = к.querySelector('.pc-pane.on');
  const пр = пане ? пане.getBoundingClientRect() : null;
  к.querySelectorAll('button, .pc-st, .pc-meta, .pc-q, .pc-conf').forEach(э => {
    if (!видна(э)) return;
    if (пр && пане.contains(э)) { const б = э.getBoundingClientRect(); if (б.bottom < пр.top || б.top > пр.bottom) return; }  // уехало в прокрутку панели
    const б = э.getBoundingClientRect(), имя = (э.getAttribute('data-act') || э.className || э.tagName) + ' «' + (э.innerText || '').trim().slice(0, 18) + '»';
    const абс = getComputedStyle(э).position === 'absolute';
    if (абс) { if (б.left < r.left || б.right > r.right || б.top < r.top) н.push(имя + ' выходит за карточку'); return; }
    if (э.closest('.pc-menu')) return;
    if (б.left < внутр.l - 0.5 || б.right > внутр.r + 0.5) н.push(имя + ' заходит в поле карточки: ' + Math.round(б.left - внутр.l) + '/' + Math.round(внутр.r - б.right));
    // Обрезка — по самому тексту, а не по scrollWidth: невидимое поле нажатия
    // (::before с отрицательными отступами) scrollWidth тоже считает.
    if (э.tagName === 'BUTTON') {
      const д = document.createRange(); д.selectNodeContents(э);
      const т = [...д.getClientRects()].filter(x => x.width > 0);
      const bs = getComputedStyle(э);
      const лв = б.left + parseFloat(bs.borderLeftWidth), пр_ = б.right - parseFloat(bs.borderRightWidth);
      if (т.some(x => x.left < лв - 0.5 || x.right > пр_ + 0.5)) н.push(имя + ' обрезана по тексту');
      if (bs.whiteSpace !== 'nowrap' && т.length && new Set(т.map(x => Math.round(x.top))).size > 2 && э.closest('.pc-row')) н.push(имя + ' переносится');
    }
  });
  // Строки кнопок: одна строка, зазор между кнопками, поле нажатия 44.
  к.querySelectorAll('.pc-row').forEach(ряд => {
    if (!видна(ряд)) return;
    if (пр && пане.contains(ряд)) { const б = ряд.getBoundingClientRect(); if (б.top > пр.bottom) return; }
    const кн = [...ряд.querySelectorAll(':scope > button')].filter(видна);
    const верх = кн.map(б => Math.round(б.getBoundingClientRect().top));
    if (new Set(верх).size > 1) н.push('кнопки строки не в одну строку: ' + кн.map(б => (б.innerText || б.getAttribute('data-act')).trim()).join(' | '));
    кн.forEach((б, i) => {
      const bb = б.getBoundingClientRect(), с = getComputedStyle(б, '::before');
      const h = bb.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
      if (h < 43.5) н.push('поле нажатия «' + б.innerText.trim() + '» ' + Math.round(h) + ' px');
      if (i && bb.left - кн[i - 1].getBoundingClientRect().right < 4) н.push('кнопки впритык: «' + кн[i - 1].innerText.trim() + '» и «' + б.innerText.trim() + '»');
    });
  });
  к.querySelectorAll('.pc-tab, .pc-seg button, .pc-x, .pc-more').forEach(э => {
    if (!видна(э)) return;
    const bb = э.getBoundingClientRect(), с = getComputedStyle(э, '::before');
    const h = bb.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
    if (h < 36) н.push('поле нажатия ' + (э.getAttribute('data-act') || э.className) + ' ' + Math.round(h) + ' px');
  });
  // Низ панели: кнопка полного журнала не уходит под край карточки.
  const низ = к.querySelector('.pc-pane.on .pc-lg-foot button');
  if (низ && видна(низ) && низ.getBoundingClientRect().bottom > внутр.b + 8.5) н.push('«Открыть в журнале действий» под краем карточки');
  return н;
}"""

ВИД = """() => { const з = document.getElementById('presetChip'), к = document.getElementById('presetChipCard');
  return { класс: з.className, надпись: ((з.querySelector('.pc-lbl') || {}).textContent || ''), замок: !!з.querySelector('.pc-lk'),
    svg: (з.querySelector('.pc-body svg') || {}).innerHTML || '', цветЗначка: з.querySelector('.pc-body svg') ? getComputedStyle(з.querySelector('.pc-body svg')).color : '',
    рамка: getComputedStyle(з).borderTopColor,
    открыта: к.classList.contains('show'), текст: к.innerText.replace(/\\s+/g, ' '), надзаг: ((к.querySelector('.pc-k') || {}).textContent || ''),
    вкладки: к.querySelectorAll('.pc-tab').length, ещё: !!к.querySelector('.pc-more'),
    мои: к.querySelector('[data-act="to-mine"]') ? { нажата: к.querySelector('[data-act="to-mine"]').getAttribute('aria-pressed'), выкл: к.querySelector('[data-act="to-mine"]').disabled } : null,
    общие: к.querySelector('[data-act="to-shared"]') ? к.querySelector('[data-act="to-shared"]').getAttribute('aria-pressed') : null,
    активный: activePresetId, общий: _activeSharedCode }; }"""


def открыть(стр):
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.locator("#presetChip .pc-body").click()
    стр.wait_for_timeout(350)


def вкладка(стр, в):
    стр.locator(f"#pcTab-{в}").click(); стр.wait_for_timeout(400)


def вёрстка(стр, н, что):
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {что}: {т}")


def начать(бр, порт, ш, в, ночь):
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async (ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); document.body.classList.toggle('dark', ночь);
      window.__тосты = []; const был = window.showToast; window.showToast = function (т) { window.__тосты.push(String(т)); return был.apply(this, arguments); };
      window.__RPC.set_preset_lock = () => new Promise(r => setTimeout(() => r(true), 300));
      window.__RPC.retract_preset = () => new Promise(r => setTimeout(() => r(true), 300));
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""", ночь)
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
    if стр.locator("#presetNameDialog input").count():
        стр.locator("#presetNameDialog input").press("Enter")
    стр.wait_for_timeout(2600)
    return стр, ошибки


def снимок(стр, имя):
    стр.screenshot(path=str(СНИМКИ / f"card-{имя}.png"))


def полный(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = начать(бр, порт, ш, в, ночь)
    с = стр.evaluate(ВИД)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    ид = с["активный"]
    if с["надпись"] != "Мой пресет" or "pc-own" not in с["класс"] or с["замок"] or "M9.3 13.6" not in с["svg"]:
        плохо(f"{н} сохранённый пресет: значок не «Мой пресет» с облаком без замка: {с['класс']} «{с['надпись']}»")
    if not код:
        плохо(f"{н} пресету не выдан код — дальше проверять нечего"); стр.close(); return
    открыть(стр)
    с = стр.evaluate(ВИД)
    if с["вкладки"] != 3 or с["надзаг"].lower() != "мой пресет" or "Сохранён в облаке" not in с["текст"] or "Опубликовать" not in с["текст"] or с["ещё"]:
        плохо(f"{н} карточка своего пресета: {с['текст'][:160]}")
    вёрстка(стр, н, "свой, «Пресет»")
    снимок(стр, f"own-{ш}{'-n' if ночь else ''}")
    # ── без связи: экран тёплым и тёплая строка ──
    стр.evaluate("() => { _вОчередь(loadAllPresets()[activePresetId]); }"); стр.wait_for_timeout(300)
    с = стр.evaluate(ВИД)
    тёплый = "rgb(224, 176, 112)" if ночь else "rgb(192, 96, 16)"
    if "pc-loc" not in с["класс"] or 'x="3" y="4"' not in с["svg"] or с["цветЗначка"] != тёплый or "Нет связи" not in с["текст"]:
        плохо(f"{н} без связи: значок {с['класс']} цвет {с['цветЗначка']}, карточка «{с['текст'][:120]}»")
    вёрстка(стр, н, "без связи")
    стр.evaluate("() => { _записатьОчередь({}); }"); стр.wait_for_timeout(300)
    if "pc-loc" in стр.evaluate(ВИД)["класс"]:
        плохо(f"{н} связь вернулась, а значок остался экраном")
    # ── журнал: только этот пресет, листается, ведёт в полный журнал ──
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ; т.events = (т.events || []).filter(e => e.created_at);
      const д = Date.now();
      for (let i = 0; i < 30; i++) т.events.push({ id: 'e' + i, user_id: 'u-проба', event_type: i % 3 ? 'options_batch' : 'discount_changed',
        created_at: new Date(д - i * 3.7 * 3600 * 1000).toISOString(), project_name: 'Проба дом 8×8',
        details: { presetCode: код, preset: 'Проба', rows: i % 3 ? [{ k: 'Добавлены', b: 'Метка-этого ' + i + '\\nВторая опция' }] : [{ k: 'Скидка', a: '0 %', b: (i % 7) + ' %' }] } });
      for (let i = 0; i < 5; i++) т.events.push({ id: 'x' + i, user_id: 'u-проба', event_type: 'options_batch', created_at: new Date(д - i * 3600 * 1000).toISOString(),
        details: { presetCode: '999999', rows: [{ k: 'Добавлены', b: 'Чужая-метка ' + i }] } });
      _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 }; }""", код)
    вкладка(стр, "l"); стр.wait_for_timeout(500)
    ж = стр.evaluate("""() => { const к = document.getElementById('presetChipCard'), л = к.querySelector('.pc-lg-sc');
      const строк = к.querySelectorAll('.pc-lg li:not(.pc-lg-day):not(.pc-lg-more)').length, т = к.innerText;
      const было = л ? л.scrollTop : 0; if (л) л.scrollTop = 200;
      return { строк, чужие: т.includes('Чужая-метка'), свои: т.includes('Метка-этого'), дни: к.querySelectorAll('.pc-lg-day').length,
               листается: !!л && л.scrollHeight > л.clientHeight + 20, сдвиг: л ? л.scrollTop - было : 0 }; }""")
    if ж["строк"] < 30 or ж["чужие"] or not ж["свои"] or ж["дни"] < 2 or not ж["листается"] or ж["сдвиг"] < 100:
        плохо(f"{н} журнал пресета: {ж}")
    вёрстка(стр, н, "«Журнал»")
    снимок(стр, f"log-{ш}{'-n' if ночь else ''}")
    стр.locator("#presetChipCard [data-act='to-log']").click(); стр.wait_for_timeout(900)
    пж = стр.evaluate("() => ({ открыт: getComputedStyle(document.getElementById('actionLogOverlay')).display !== 'none', пресет: _alПресет, период: _alПериод, карточка: document.getElementById('presetChipCard').classList.contains('show'), подпись: (document.getElementById('alSub') || {}).textContent || '' })")
    if not пж["открыт"] or пж["пресет"] != код or пж["период"] != "всё" or пж["карточка"]:
        плохо(f"{н} «Открыть в журнале действий»: {пж}")
    стр.evaluate("() => { closeActionLog(); _alПресет = null; _alПериод = '7'; }"); стр.wait_for_timeout(300)
    # ── проверка ──
    открыть(стр); вкладка(стр, "c")
    пр = стр.evaluate("""() => { const к = document.getElementById('presetChipCard');
      return { текст: к.innerText.replace(/\\s+/g, ' '), замечаний: к.querySelectorAll('.pc-ck li').length,
               счёт: +(((к.querySelector('#pcTab-c .pc-cnt') || {}).textContent) || 0), стоп: к.querySelectorAll('.pc-ck .pc-stop').length }; }""")
    if "водосточную" not in пр["текст"] or пр["стоп"] < 1 or пр["счёт"] != пр["замечаний"]:
        плохо(f"{н} проверка: нет стопа о водостоке или счётчик не равен числу замечаний: {пр}")
    вёрстка(стр, н, "«Проверка»")
    снимок(стр, f"check-{ш}{'-n' if ночь else ''}")
    стр.locator("#presetChipCard .pc-ck button").first.click(); стр.wait_for_timeout(900)
    пер = стр.evaluate("""() => { const ш = document.querySelector('#sec_opts_roof').closest('.card').querySelector('.section-header');
      const б = ш.getBoundingClientRect(); return { вспышка: ш.classList.contains('pc-flash'), верх: Math.round(б.top), карточка: document.getElementById('presetChipCard').classList.contains('show') }; }""")
    if not пер["вспышка"] or пер["карточка"] or not (0 <= пер["верх"] <= 260):
        плохо(f"{н} переход к разделу «Кровля» из замечания: {пер}")
    стр.evaluate("""() => { toggleOpt('r6'); customOptions.insulation = customOptions.insulation || [];
      customOptions.insulation.push({ id: 99991, name: 'Утеплитель Rockwool Лайт Баттс 50 мм', price: 0, checked: true }); }""")
    стр.wait_for_timeout(400)
    открыть(стр); вкладка(стр, "c")
    т = стр.evaluate("() => document.getElementById('presetChipCard').innerText")
    if "водосточную" in т or "Rockwool" not in т:
        плохо(f"{н} после водостока и Rockwool замечания не те: {т[:200]!r}")
    стр.evaluate("() => { customOptions.insulation.pop(); }")
    вкладка(стр, "p")
    # ── публикация ──
    стр.locator("#presetChipCard [data-act='publish']").click(); стр.wait_for_timeout(1500)
    с = стр.evaluate(ВИД)
    if с["надпись"] != "Мой пресет · опубликован" or not с["замок"] or not с["ещё"] or not с["мои"] or с["мои"]["нажата"] != "true" or с["мои"]["выкл"]:
        плохо(f"{н} после публикации: «{с['надпись']}» замок {с['замок']} ⋯ {с['ещё']} «Мои» {с['мои']}")
    вёрстка(стр, н, "опубликован, «Мои»")
    снимок(стр, f"pub-{ш}{'-n' if ночь else ''}")
    # «Общие» и обратно
    стр.locator("#presetChipCard [data-act='to-shared']").click(); стр.wait_for_timeout(700); открыть(стр)
    с = стр.evaluate(ВИД)
    if с["общий"] != код or с["активный"] or с["надзаг"].lower() != "общий пресет · мой" or с["общие"] != "true":
        плохо(f"{н} «Общие»: общий {с['общий']}, свой {с['активный']}, «{с['надзаг']}», нажата {с['общие']}")
    стр.locator("#presetChipCard [data-act='to-mine']").click(); стр.wait_for_timeout(700); открыть(стр)
    с = стр.evaluate(ВИД)
    if с["активный"] != ид or с["общий"]:
        плохо(f"{н} «Мои» из «Общих» не открыли свой пресет: {с['активный']} / {с['общий']}")
    # открытие замка из «Моих» переводит в «Общие», «Мои» недоступны
    стр.locator("#presetChipCard [data-act='lock']").click(); стр.wait_for_timeout(1200); открыть(стр)
    с = стр.evaluate(ВИД)
    if с["общий"] != код or not с["мои"] or not с["мои"]["выкл"] or "Закрыть замок" not in с["текст"]:
        плохо(f"{н} открытие замка из «Моих»: общий {с['общий']}, «Мои» {с['мои']}, «{с['текст'][:120]}»")
    вёрстка(стр, н, "замок открыт, «Общие»")
    снимок(стр, f"open-{ш}{'-n' if ночь else ''}")
    стр.locator("#presetChipCard [data-act='lock']").click(); стр.wait_for_timeout(1200)
    if стр.evaluate(ВИД)["мои"]["выкл"]:
        плохо(f"{н} замок закрыт, а «Мои» по-прежнему недоступны")
    # ── «⋯» → снять с публикации ──
    стр.locator("#presetChipCard [data-act='more']").click(); стр.wait_for_timeout(250)
    меню = стр.evaluate("() => { const м = document.querySelector('#presetChipCard .pc-menu'); return м ? { текст: м.innerText.trim(), фокус: document.activeElement && document.activeElement.getAttribute('data-act') } : null; }")
    if not меню or меню["текст"] != "Снять с публикации" or меню["фокус"] != "unpub":
        плохо(f"{н} меню «⋯»: {меню}")
    вёрстка(стр, н, "меню «⋯»")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(200)
    if стр.evaluate("() => !!document.querySelector('#presetChipCard .pc-menu') || !document.getElementById('presetChipCard').classList.contains('show')"):
        плохо(f"{н} Escape не закрыл одно меню «⋯» (или закрыл всю карточку)")
    стр.locator("#presetChipCard [data-act='more']").click(); стр.wait_for_timeout(200)
    стр.locator("#presetChipCard [data-act='unpub']").click(); стр.wait_for_timeout(250)
    пд = стр.evaluate("""() => { const к = document.getElementById('presetChipCard'), п = к.querySelector('.pc-conf');
      return п ? { текст: п.innerText, режим: !!к.querySelector('.pc-mode'), фокус: document.activeElement && document.activeElement.getAttribute('data-act') } : null; }""")
    if not пд or "Снять с публикации?" not in пд["текст"] or "клиент" in пд["текст"].lower() or пд["режим"] or пд["фокус"] != "unpub-no":
        плохо(f"{н} подтверждение снятия: {пд}")
    вёрстка(стр, н, "подтверждение снятия")
    снимок(стр, f"confirm-{ш}{'-n' if ночь else ''}")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(200)
    if стр.evaluate("() => !!document.querySelector('#presetChipCard .pc-conf') || !document.querySelector('#presetChipCard .pc-mode')"):
        плохо(f"{н} Escape не снял подтверждение")
    стр.locator("#presetChipCard [data-act='more']").click(); стр.wait_for_timeout(200)
    стр.locator("#presetChipCard [data-act='unpub']").click(); стр.wait_for_timeout(200)
    стр.locator("#presetChipCard [data-act='unpub-yes']").click(); стр.wait_for_timeout(1500)
    с = стр.evaluate(ВИД)
    if с["активный"] != ид or с["общий"] or с["надпись"] != "Мой пресет" or с["ещё"]:
        плохо(f"{н} после снятия с публикации: свой {с['активный']}, общий {с['общий']}, «{с['надпись']}», ⋯ {с['ещё']}")
    # ── чужой общий — серым, без «⋯» ──
    стр.evaluate("""() => { _sharedPresets.push({ short_code: '111222', id: '111222', name: 'Баня «Лейпциг» 5×7', author_name: 'Сергей Волков',
      author_id: 'u-другой', is_public: true, visibility: 'public', locked: true, created_at: '2026-09-22T13:05:00Z', updated_at: '2026-09-22T13:05:00Z', state: {} });
      openSharedPreset('111222'); }""")
    стр.wait_for_timeout(600); открыть(стр)
    с = стр.evaluate(ВИД)
    серый = "rgb(74, 77, 71)" if ночь else "rgb(210, 212, 207)"
    if с["рамка"] != серый or с["ещё"] or с["надзаг"].lower() != "общий пресет" or с["вкладки"] != 3:
        плохо(f"{н} чужой общий: рамка {с['рамка']}, ⋯ {с['ещё']}, «{с['надзаг']}», вкладок {с['вкладки']}")
    вёрстка(стр, н, "чужой общий")
    снимок(стр, f"other-{ш}{'-n' if ночь else ''}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def только_вёрстка(бр, порт, ш, в, ночь):
    н = f"[{ш}×{в}{' ночь' if ночь else ''}]"
    стр, ошибки = начать(бр, порт, ш, в, ночь)
    открыть(стр)
    for т, имя in (("p", "свой"), ("l", "журнал"), ("c", "проверка")):
        вкладка(стр, т); стр.wait_for_timeout(300)
        вёрстка(стр, н, имя)
    вкладка(стр, "p")
    стр.locator("#presetChipCard [data-act='publish']").click(); стр.wait_for_timeout(1500); открыть(стр)
    вёрстка(стр, н, "опубликован")
    стр.locator("#presetChipCard [data-act='more']").click(); стр.wait_for_timeout(200)
    стр.locator("#presetChipCard [data-act='unpub']").click(); стр.wait_for_timeout(250)
    вёрстка(стр, н, "подтверждение")
    снимок(стр, f"confirm-{ш}x{в}{'-n' if ночь else ''}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            полный(бр, порт, 390, 844, False)
            полный(бр, порт, 1440, 900, True)
            for ш, в, ночь in ((390, 844, True), (1440, 900, False), (320, 640, False), (768, 1024, False), (390, 600, False)):
                только_вёрстка(бр, порт, ш, в, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: у своего пресета — значок «Мой пресет» (облако, экран без связи, глобус с замком у опубликованного) и карточка "
          "во вкладках; «Мои / Общие» в обе стороны, открытие замка из «Моих» переводит в «Общие»; «⋯» → подтверждение в карточке → "
          "снятие; журнал только этого пресета листается и ведёт в полный журнал с фильтром; проверка по чек-листу с переходом к разделу; "
          "чужой общий серым — на 320, 390, 768 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
