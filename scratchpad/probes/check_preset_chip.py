#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок пресета в правом нижнем углу вместо двух нижних полосок.

Константин 27.09.2026: «test.calculator.baniamsk.ru/mockups/bottom-chip-motion-v1.html
— внедряй по этому шаблону для сохранения пресета и общего пресета окна»;
«Позже» — «прятать до следующей правки»; «цвет делай по теме».

Проба держит, на 390 и 1440, в «Бланке» и «Модерне», днём и ночью:
  • прежних полосок нет: ни «Пресет не сохранён» по центру, ни полосы общего пресета;
  • выбран проект — значок «Не сохранён» у правого края, в кадре, над полоской
    итога и не касается её; нажатие раскрывает карточку в пределах экрана;
  • «Позже» прячет значок на три минуты — правки и нажатия его не возвращают; потом
    карточка «Сохранить / Позже» возвращается при первом нажатии или возврате на
    вкладку, но не при скрытой вкладке;
  • «Сохранить» → имя → значок говорит «Сохранено» и тает;
  • свой общий пресет — «Общий · ваш», замок нажимается и отвечает сразу
    (мерцает, пока база молчит), потом надпись «Замок снят…» и никакого
    сообщения внизу экрана; карточка называет имя, автора «вы», код и кнопку замка;
  • чужой общий — «Общий · Имя Ф.», замок не нажимается, в карточке полное имя
    автора и «Заблокирован — только просмотр»;
  • цвет общего значка — акцент оформления и тона, а не зашитая бирюза;
  • сообщение внизу экрана встаёт над значком, а не на него;
  • на 1024–1920 значок в углу калькулятора, а не экрана: правый край — как у суммы
    в полоске итога, карточка растёт из того же угла, открытая боковая панель его не накрывает.

    python3 check_preset_chip.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а): pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ВИД = """() => {
  const з = document.getElementById('presetChip'), к = document.getElementById('presetChipCard');
  const вид = э => !!э && getComputedStyle(э).display !== 'none' && parseFloat(getComputedStyle(э).opacity) > 0.5 && э.getBoundingClientRect().width > 0;
  const стар = [document.getElementById('saveReminder'), document.getElementById('sharedModeIndicator')].filter(вид).map(э => э.id);
  const р = э => { const б = э.getBoundingClientRect(); return { l: Math.round(б.left), t: Math.round(б.top), r: Math.round(б.right), b: Math.round(б.bottom), h: Math.round(б.height) }; };
  const полоса = document.getElementById('totalStrip');
  return { значок: вид(з), класс: з ? з.className : '', надпись: з ? ((з.querySelector('.pc-lbl') || {}).textContent || '') : '',
    рамка: з ? р(з) : null, замок: з && з.querySelector('.pc-lk') ? { есть: true, выкл: з.querySelector('.pc-lk').disabled, ш: Math.round(з.querySelector('.pc-lk').getBoundingClientRect().width) } : null,
    карточка: вид(к), рамкаК: к ? р(к) : null, текстК: к ? к.innerText.replace(/\\s+/g, ' ') : '',
    полоса: полоса && полоса.classList.contains('on') ? р(полоса) : null, старые: стар,
    ширина: innerWidth, высота: innerHeight, цвет: з ? getComputedStyle(з).borderTopColor : '' };
}"""


def ждать(стр, мс):
    стр.wait_for_timeout(мс)


def прогон(бр, порт, ш, ui, ночь):
    н = f"[{ш} {ui}{' ночь' if ночь else ''}]"
    стр = бр.new_page(viewport={"width": ш, "height": 844 if ш < 900 else 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); ждать(стр, 2500)
    стр.evaluate("""([ui, ночь]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle(ui, false); document.body.classList.toggle('dark', ночь);
      window.__тосты = []; const был = window.showToast; window.showToast = function (т) { window.__тосты.push(String(т)); return был.apply(this, arguments); }; }""", [ui, ночь])
    # ── не сохранён ──
    стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }")
    в = стр.evaluate(ВИД)
    if в["старые"]:
        плохо(f"{н} видна прежняя полоска: {в['старые']}")
    if not в["значок"] or "Не сохранён" not in в["надпись"]:
        плохо(f"{н} после выбора проекта нет значка «Не сохранён»: {в['класс']} «{в['надпись']}»"); стр.close(); return
    р = в["рамка"]
    if р["r"] > в["ширина"] - 8 or р["l"] < 8 or р["b"] > в["высота"]:
        плохо(f"{н} значок не у правого края в кадре: {р}")
    if р["h"] < 38:
        плохо(f"{н} значок ниже 38 px: {р['h']}")
    # над полоской итога и не касается её
    стр.evaluate("() => { window.scrollTo(0, document.body.scrollHeight); }"); ждать(стр, 700)
    в = стр.evaluate(ВИД)
    if в["полоса"] and в["рамка"]["b"] > в["полоса"]["t"] - 6:
        плохо(f"{н} значок касается полоски итога или лежит на ней: значок {в['рамка']}, полоса {в['полоса']}")
    стр.screenshot(path=str(СНИМКИ / f"chip-unsaved-{ш}-{ui}{'-n' if ночь else ''}.png"))
    стр.locator("#presetChip .pc-body").click(); ждать(стр, 350)
    в = стр.evaluate(ВИД)
    к = в["рамкаК"]
    if not в["карточка"] or "Сохранить" not in в["текстК"] or "Позже" not in в["текстК"]:
        плохо(f"{н} карточка сохранения не открылась: {в['текстК'][:80]}")
    elif к["l"] < 4 or к["r"] > в["ширина"] - 4 or к["t"] < 4:
        плохо(f"{н} карточка выходит за экран: {к}")
    # Поле нажатия: значок и кнопки карточки рисуются 36–40 px, а нажимаются
    # на 44 — невидимым полем, и поля соседних кнопок не перекрываются.
    поля = стр.evaluate("""() => { const п = э => { const b = э.getBoundingClientRect(), с = getComputedStyle(э, '::before');
        const d = н => parseFloat(с[н]) || 0; return { l: b.left + d('left'), r: b.right - d('right'), t: b.top + d('top'), b: b.bottom - d('bottom'), имя: э.className || э.tagName }; };
      return [document.querySelector('#presetChip .pc-body'), ...document.querySelectorAll('#presetChipCard .pc-row button')].filter(Boolean).map(п); }""")
    for а in поля:
        if а["b"] - а["t"] < 43.5:
            плохо(f"{н} поле нажатия «{а['имя']}» {round(а['b'] - а['t'])} px — меньше 44")
    for i, а in enumerate(поля[1:], 1):
        for б in поля[i + 1:]:
            if а["r"] > б["l"] + 0.5 and а["l"] < б["r"] - 0.5 and а["b"] > б["t"] and а["t"] < б["b"]:
                плохо(f"{н} поля нажатия «{а['имя']}» и «{б['имя']}» перекрываются")
    стр.screenshot(path=str(СНИМКИ / f"chip-card-{ш}-{ui}{'-n' if ночь else ''}.png"))
    # «Позже» — на три минуты; потом карточка возвращается при первом признаке
    # работы или при возврате на вкладку (Константин, 27.09.2026)
    стр.locator("#presetChipCard .pc-later").click(); ждать(стр, 400)
    if стр.evaluate(ВИД)["значок"]:
        плохо(f"{н} «Позже» не спрятал значок")
    срок = стр.evaluate("() => Math.round((_позжеДо - Date.now()) / 1000)")
    if not (170 <= срок <= 180):
        плохо(f"{н} «Позже» откладывает не на три минуты: {срок} с")
    правка = стр.evaluate("""() => { const ч = [...document.querySelectorAll('input[id^="chk_"]')].find(e => !e.checked && !e.disabled && e.closest('.opt-item') && e.closest('.opt-item').offsetParent);
      if (!ч) return null; toggleOpt(ч.id.slice(4)); return ч.id; }""")
    if not правка:
        плохо(f"{н} не нашлась свободная опция для правки")
    ждать(стр, 500)
    стр.mouse.click(10, 300); ждать(стр, 300)
    if стр.evaluate(ВИД)["значок"]:
        плохо(f"{н} правка и нажатие до истечения трёх минут вернули значок — «Позже» ничего не отложило")
    # срок вышел, вкладка скрыта: карточка не выскакивает в пустоту
    стр.evaluate("""() => { _позжеДо = Date.now() - 1; window.__вид = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState');
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
      document.dispatchEvent(new Event('visibilitychange')); document.body.dispatchEvent(new Event('pointerdown', { bubbles: true })); }""")
    ждать(стр, 300)
    if стр.evaluate(ВИД)["значок"]:
        плохо(f"{н} напоминание вернулось при скрытой вкладке")
    # вернулся на вкладку — значок и карточка «Сохранить / Позже»
    стр.evaluate("() => { delete document.visibilityState; document.dispatchEvent(new Event('visibilitychange')); }")
    ждать(стр, 450)
    в = стр.evaluate(ВИД)
    if not в["значок"] or not в["карточка"] or "Позже" not in в["текстК"]:
        плохо(f"{н} по сроку при возврате не вернулась карточка «Сохранить / Позже»: значок {в['значок']}, карточка {в['карточка']}")
    # и при непрерывной работе: срок вышел — первое нажатие возвращает карточку
    стр.locator("#presetChipCard .pc-later").click(); ждать(стр, 400)
    стр.evaluate("() => { _позжеДо = Date.now() - 1; }")
    стр.mouse.click(10, 300); ждать(стр, 450)
    в = стр.evaluate(ВИД)
    if not в["значок"] or not в["карточка"]:
        плохо(f"{н} по сроку при работе не вернулась карточка: значок {в['значок']}, карточка {в['карточка']}")
    стр.locator("#presetChipCard .pc-x").click(); ждать(стр, 300)
    # сохранение
    стр.locator("#presetChip .pc-body").click(); ждать(стр, 300)
    стр.locator("#presetChipCard .pc-save").click(); ждать(стр, 300)
    if стр.locator("#presetNameDialog input").count():
        стр.locator("#presetNameDialog input").press("Enter")
    ждать(стр, 250)
    в = стр.evaluate(ВИД)
    if "Сохранено" not in в["надпись"]:
        плохо(f"{н} после сохранения значок не сказал «Сохранено»: «{в['надпись']}» {в['класс']}")
    ждать(стр, 1800)
    if стр.evaluate(ВИД)["значок"]:
        плохо(f"{н} значок «Сохранено» не растаял")
    # ── свой общий ──
    стр.evaluate("""() => { const я = _sbUser && _sbUser.id;
      window.__RPC = window.__RPC || {};
      window.__RPC.set_preset_lock = () => new Promise(r => setTimeout(() => r(true), 1200));  // с запасом: нажатие под нагрузкой бывает дольше 400 мс
      _sharedPresets.length = 0;
      _sharedPresets.push({ short_code: '235788', id: '235788', name: 'Баня «Берлин» 6×8 · 24.09.26', author_name: 'Проба',
        author_id: я, is_public: true, visibility: 'public', locked: true, created_at: '2026-09-24T08:40:00Z', updated_at: '2026-09-24T08:40:00Z',
        state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 4600000, tech: 'frame' } },
        { short_code: '111222', id: '111222', name: 'Баня «Лейпциг» 5×7 · 22.09.26', author_name: 'Ирина Васильевна',
        author_id: 'u-другой', is_public: true, visibility: 'public', locked: true, created_at: '2026-09-22T13:05:00Z', updated_at: '2026-09-22T13:05:00Z',
        state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 4600000, tech: 'frame' } });
      _activeSharedCode = '235788'; updateSharedModeIndicator(); window.__тосты.length = 0; }""")
    ждать(стр, 400)
    в = стр.evaluate(ВИД)
    if в["старые"]:
        плохо(f"{н} у общего пресета видна прежняя полоса: {в['старые']}")
    if not в["значок"] or в["надпись"] != "Общий · ваш" or not в["замок"] or в["замок"]["выкл"]:
        плохо(f"{н} свой общий пресет: значок {в['класс']} «{в['надпись']}», замок {в['замок']}")
    ждём = стр.evaluate("() => getComputedStyle(document.body).getPropertyValue('--pc-acc').trim()")
    цвет_акцента = стр.evaluate("(ц) => { const s = document.createElement('span'); s.style.color = ц; document.body.appendChild(s); const r = getComputedStyle(s).color; s.remove(); return r; }", ждём)
    if в["цвет"] != цвет_акцента:
        плохо(f"{н} рамка значка не цвета акцента темы: {в['цвет']} против {цвет_акцента}")
    лк = стр.evaluate("""() => { const э = document.querySelector('#presetChip .pc-lk'), т = document.querySelector('#presetChip .pc-body');
      const b = э.getBoundingClientRect(), с = getComputedStyle(э, '::before'), bt = т.getBoundingClientRect(), ст = getComputedStyle(т, '::before');
      return { в: b.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0),
               стык: (b.left + (parseFloat(с.left) || 0)) - (bt.right - (parseFloat(ст.right) || 0)) }; }""")
    if лк["в"] < 43.5:
        плохо(f"{н} поле нажатия замка {round(лк['в'])} px — меньше 44")
    if лк["стык"] < -0.5:
        плохо(f"{н} поле замка заходит на тело значка на {-round(лк['стык'])} px — нажатие у стыка уйдёт соседу")
    вид_закрыт = стр.evaluate("() => { const с = getComputedStyle(document.getElementById('presetChip')); return [с.backgroundColor, с.borderTopColor, с.borderTopStyle, с.color]; }")
    стр.locator("#presetChip .pc-lk").click(); ждать(стр, 150)
    # дужка откинута как у карточек и проигрывает открытие, а перерисовка после
    # ответа базы анимацию не обрывает (Константин, 27.09.2026)
    дужка = стр.evaluate("""() => { const д = document.querySelector('#presetChip .lk-sh');
      return д ? { d: д.getAttribute('d'), кл: д.getAttribute('class'), идёт: д.getAnimations().length } : null; }""")
    if not дужка or not дужка["d"].startswith("M14 11") or "lk-open" not in дужка["кл"] or not дужка["идёт"]:
        плохо(f"{н} замок значка не откинул дужку или не проиграл открытие: {дужка}")
    ждать(стр, 400)   # переходы цвета значка доиграли
    вид_открыт = стр.evaluate("() => { const с = getComputedStyle(document.getElementById('presetChip')); return [с.backgroundColor, с.borderTopColor, с.borderTopStyle, с.color]; }")
    if вид_открыт != вид_закрыт:
        # открытый выглядит как закрытый, отличается только дужка (Константин, 27.09.2026)
        плохо(f"{н} значок с открытым замком выглядит иначе, чем с закрытым: {вид_открыт} против {вид_закрыт}")
    рамка = стр.evaluate("() => getComputedStyle(document.getElementById('presetChip')).borderTopStyle")
    if рамка != "solid":
        плохо(f"{н} рамка значка открытого общего пресета «{рамка}» — нужна обычная, без пунктира")
    в = стр.evaluate(ВИД)
    if "pc-wait" not in в["класс"] or "pc-open" not in в["класс"]:
        плохо(f"{н} замок не ответил сразу (ждём мерцание и открытый вид): {в['класс']}")
    ждать(стр, 800)
    в = стр.evaluate(ВИД)
    if "Замок снят" not in в["надпись"]:
        плохо(f"{н} после снятия замка значок не сказал, что это значит: «{в['надпись']}»")
    if any("Замок" in т for т in стр.evaluate("() => window.__тосты")):
        плохо(f"{н} при замке из значка выскочило и сообщение внизу экрана")
    стр.locator("#presetChip .pc-body").click(); ждать(стр, 350)
    в = стр.evaluate(ВИД)
    if not в["карточка"] or "Баня «Берлин»" not in в["текстК"] or "вы" not in в["текстК"] or "235 788" not in в["текстК"] or "Закрыть замок" not in в["текстК"]:
        плохо(f"{н} карточка своего общего пресета неполная: {в['текстК'][:140]}")
    стр.screenshot(path=str(СНИМКИ / f"chip-own-{ш}-{ui}{'-n' if ночь else ''}.png"))
    стр.locator("#presetChipCard .pc-x").click(); ждать(стр, 300)
    # ── чужой общий ──
    стр.evaluate("() => { _activeSharedCode = '111222'; updateSharedModeIndicator(); }"); ждать(стр, 300)
    в = стр.evaluate(ВИД)
    if в["надпись"] != "Общий · Ирина В." or not в["замок"] or not в["замок"]["выкл"]:
        плохо(f"{н} чужой общий пресет: «{в['надпись']}», замок {в['замок']}")
    стр.locator("#presetChip .pc-body").click(); ждать(стр, 350)
    в = стр.evaluate(ВИД)
    if "Ирина Васильевна" not in в["текстК"] or "Заблокирован — только просмотр" not in в["текстК"]:
        плохо(f"{н} карточка чужого пресета неполная: {в['текстК'][:140]}")
    стр.screenshot(path=str(СНИМКИ / f"chip-other-{ш}-{ui}{'-n' if ночь else ''}.png"))
    стр.locator("#presetChipCard .pc-x").click(); ждать(стр, 300)
    # сообщение внизу экрана — над значком
    стр.evaluate("() => showToast('Проба сообщения')"); ждать(стр, 400)
    т = стр.evaluate("""() => { const т = document.getElementById('toastMsg'), з = document.getElementById('presetChip');
      if (!т || !з) return null; const а = т.getBoundingClientRect(), б = з.getBoundingClientRect();
      const пересек = а.left < б.right && а.right > б.left && а.top < б.bottom && а.bottom > б.top; return { пересек }; }""")
    if т and т["пересек"]:
        плохо(f"{н} сообщение внизу экрана легло на значок")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def угол(бр, порт):
    """Значок стоит в углу калькулятора, а не экрана: правый край — там же, где сумма
    в полоске итога (Константин, 27.09.2026: «угол калькулятора ставь, а не угол
    всего экрана»). И не ложится на боковую панель, открытую за краем расчёта."""
    for ш in (1024, 1280, 1440, 1920):
        for ui in ("blank", "light"):
            стр = бр.new_page(viewport={"width": ш, "height": 900})
            стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); ждать(стр, 2500)
            р = стр.evaluate("""async (ui) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
              applyUiStyle(ui, false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
              window.scrollTo(0, document.body.scrollHeight); await new Promise(r => setTimeout(r, 700));
              const з = document.getElementById('presetChip').getBoundingClientRect();
              const с = document.querySelector('#totalStrip .ts-inner'); const сс = с ? с.getBoundingClientRect() : null;
              const л = document.querySelector('.page-wrap').getBoundingClientRect();
              document.querySelector('#presetChip .pc-body').click(); await new Promise(r => setTimeout(r, 350));
              const к = document.getElementById('presetChipCard').getBoundingClientRect();
              закрытьКарточкуЗначка(); try { openSideNav(); } catch (e) {} await new Promise(r => setTimeout(r, 500));
              const п = document.getElementById('sideNav'); const пп = п && getComputedStyle(п).display !== 'none' ? п.getBoundingClientRect() : null;
              const з2 = document.getElementById('presetChip').getBoundingClientRect();
              return { з: з.right, лев: з.left, полоса: сс && сс.width ? сс.right : null, лист: л.right, к: к.right,
                       панель: пп && пп.width > 0 && пп.left < innerWidth ? [пп.left, пп.right, пп.top, пп.bottom] : null,
                       з2: [з2.left, з2.right, з2.top, з2.bottom] }; }""", ui)
            н = f"[угол {ш} {ui}]"
            if р["полоса"] is not None and abs(р["з"] - р["полоса"]) > 1.5:
                плохо(f"{н} правый край значка {р['з']:.0f}, а суммы в полоске итога {р['полоса']:.0f} — значок не в углу калькулятора")
            if р["з"] > р["лист"] + 0.5:
                плохо(f"{н} значок заходит за край калькулятора: {р['з']:.0f} > {р['лист']:.0f}")
            if abs(р["к"] - р["з"]) > 1.5:
                плохо(f"{н} карточка не из угла значка: {р['к']:.0f} против {р['з']:.0f}")
            if р["панель"]:
                л, п_, в, н_ = р["панель"]; зл, зп, зв, зн = р["з2"]
                if зл < п_ and зп > л and зв < н_ and зн > в:
                    плохо(f"{н} значок лёг на открытую боковую панель: значок {р['з2']}, панель {р['панель']}")
            стр.close()


def тон(бр, порт):
    """Цвет значка идёт за тоном: у «Зелёного-графита» он не бирюзовый."""
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); ждать(стр, 2500)
    цвета = стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const я = _sbUser && _sbUser.id; _sharedPresets.length = 0;
      _sharedPresets.push({ short_code: '235788', id: '235788', name: 'Проба', author_id: я, is_public: true, locked: true, state: {} });
      _activeSharedCode = '235788'; updateSharedModeIndicator(); await new Promise(r => setTimeout(r, 300));
      const ц = () => getComputedStyle(document.getElementById('presetChip')).borderTopColor;
      const бирюза = ц(); applyTone('bmsk', false); await new Promise(r => setTimeout(r, 300)); return [бирюза, ц()]; }""")
    if цвета[0] == цвета[1]:
        плохо(f"[тон] цвет значка не сменился с тоном: {цвета}")
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for ui in ("blank", "light"):
                    for ночь in (False, True):
                        прогон(бр, порт, ш, ui, ночь)
            тон(бр, порт)
            угол(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: вместо двух полосок — значок в правом нижнем углу: «Не сохранён» с карточкой, «Позже» на три минуты с возвратом карточки "
          "при работе или возврате на вкладку, «Сохранено» после записи; общий — «Общий · автор», замок отвечает сразу и объясняет себя надписью; "
          "цвет от темы и тона; сообщения встают над значком; на широком экране — в углу калькулятора, мимо боковой панели — на 390 и 1440, «Бланк» и «Модерн», день и ночь.")


if __name__ == "__main__":
    главная()
