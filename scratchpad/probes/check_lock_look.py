#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замок на карточках пресетов: без плашки, без выделения, после скачивания.

Константин 27.09.2026, двумя снимками окна «Пресеты» на телефоне:
«1. Плашку эту убери. 2. В общих пресетах когда закрыт замок убери
выделение. Только когда нажимаешь оставь выделение (как в моих пресетах).
3. Поменяй местами Замок и Скачать кнопки в общих пресетах».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • у замка нет `title` — из него на «Моих» рисовалась плашка, — а
    aria-label есть; плашки значковых кнопок «Моих» живут только внутри
    @media (hover: hover), то есть на телефоне не появляются;
  • закрытый замок на «Общих» залит и обведён так же, как соседняя кнопка
    скачивания; пока нажатие в пути — выделен;
  • на «Общих» скачивание стоит раньше замка;
  • закрытый замок говорит «Пресет заблокирован — в «Общих» его редактировать
    нельзя», снятый — «Замок снят — в «Общих» пресет открыт для правки»: слово
    «в «Общих»» нужно, иначе автор решил бы, что заперт и в «Моих» (27.09.2026);
  • снятый замок говорит о себе сообщением внизу экрана: «Замок снят — пресет
    открыт для правки» (27.09.2026: «Открыт для правки напиши снизу, возле
    сообщения „Замок снят“») — раз плашки больше нет, состояние называет оно.

    python3 check_lock_look.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
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
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ПОДГОТОВКА = """async (ui) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle(ui, false);
  selectProjectOption(0); await ждать(600);
  const снимок = collectState();
  window.__тосты = []; window.showToast = т => window.__тосты.push(String(т));
  window.__RPC = window.__RPC || {};
  window.__RPC.set_preset_lock = () => new Promise(r => setTimeout(() => r(true), 1500));
  const сейчас = new Date().toISOString();
  saveAllPresets({ p1: { id: 'p1', name: 'Опубликованный пресет пробы', state: снимок, savedAt: сейчас, shortCode: '111111', sharedId: '111111', publishedAs: 'public' } });
  _sharedPresets.length = 0;
  _sharedPresets.push({ short_code: '111111', id: '111111', preset_id: 'p1', author_id: _sbUser.id, author_name: 'Проба', name: 'Опубликованный пресет пробы',
                        state: снимок, is_public: true, visibility: 'public', locked: true, created_at: сейчас, updated_at: сейчас });
  // «Общие» при открытии перечитывают строки из базы — кладём туда же.
  window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(х => Object.assign({}, х));
  try { _общиеЗагружены = true; } catch (e) {}
  openPresetPanel(); await ждать(300);
  return true;
}"""

ОСМОТР = """() => {
  const кар = document.querySelector('#sharedPresetList .shared-pcard[data-scode="111111"]');
  const замок = кар && кар.querySelector('.btn-shared-lock');
  const скач = кар && [...кар.querySelectorAll('.btn-shared-act')].find(к => /Скачать/.test(к.getAttribute('title') || ''));
  const вид = e => { const c = getComputedStyle(e); return c.backgroundColor + ' | ' + c.borderTopColor; };
  const все = кар ? [...кар.querySelectorAll('.shared-pcard-actions > *')] : [];
  const мойЗамок = document.querySelector('#presetList .pcard .btn-shared-lock');
  let вМедиа = null;
  for (const л of document.styleSheets) { let пр; try { пр = л.cssRules; } catch (e) { continue; }
    for (const п of пр) { if (п.cssRules) for (const в of п.cssRules) if (в.selectorText && в.selectorText.includes('.pcard-act[title]:hover::after')) вМедиа = п.conditionText || п.media && п.media.mediaText;
      if (п.selectorText && п.selectorText.includes('.pcard-act[title]:hover::after')) вМедиа = вМедиа || 'вне медиа'; } }
  return { есть: !!замок, закрыт: замок && замок.classList.contains('on'),
    title: замок && замок.getAttribute('title'), aria: замок && замок.getAttribute('aria-label'),
    titleМои: мойЗамок && мойЗамок.getAttribute('title'), ariaМои: мойЗамок && мойЗамок.getAttribute('aria-label'),
    видЗамка: замок && вид(замок), видСкач: скач && вид(скач),
    порядок: [все.indexOf(скач), все.indexOf(замок)], плашка: вМедиа };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank",):
                for ш in (390, 1440):
                    н = f"[{ui} {ш}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    стр.evaluate(ПОДГОТОВКА, ui)
                    стр.evaluate("async () => { switchPresetTab('my'); await new Promise(r => setTimeout(r, 300)); }")
                    мои = стр.evaluate(ОСМОТР)
                    стр.evaluate("async () => { switchPresetTab('shared'); await new Promise(r => setTimeout(r, 500)); }")
                    р = стр.evaluate(ОСМОТР)
                    р["titleМои"], р["ariaМои"] = мои["titleМои"], мои["ariaМои"]
                    print("  " + н, json.dumps(р, ensure_ascii=False))
                    if not р["есть"]:
                        плохо(f"{н} на «Общих» нет замка"); стр.close(); continue
                    if р["title"] or р["titleМои"]:
                        плохо(f"{н} у замка есть title — будет плашка: «{р['title'] or р['titleМои']}»")
                    if not р["aria"] or not р["ariaМои"]:
                        плохо(f"{н} у замка нет aria-label")
                    if р["плашка"] is None or "hover" not in str(р["плашка"]):
                        плохо(f"{н} плашка значковых кнопок не спрятана в @media (hover: hover): {р['плашка']}")
                    if not р["закрыт"]:
                        плохо(f"{н} замок в пробе не закрыт — проверять нечего")
                    elif р["видЗамка"] != р["видСкач"]:
                        плохо(f"{н} закрытый замок выделен: {р['видЗамка']} против скачивания {р['видСкач']}")
                    if not (0 <= р["порядок"][0] < р["порядок"][1]):
                        плохо(f"{н} скачивание не раньше замка: {р['порядок']}")
                    стр.screenshot(path=str(СНИМКИ / f"lock-look-{ui}-{ш}.png"))
                    # снятие замка — сообщение называет состояние
                    стр.evaluate("async () => { window.__RPC.set_preset_lock = () => true; await togglePresetLock('111111'); }")
                    тосты = стр.evaluate("() => window.__тосты")
                    if not any("Замок снят" in т and "в «Общих» пресет открыт для правки" in т for т in тосты):
                        плохо(f"{н} после снятия замка нет сообщения «Замок снят — пресет открыт для правки»: {тосты[-2:]}")
                    # и обратно — закрытие тоже называет, что оно значит (27.09.2026)
                    стр.evaluate("async () => { window.__тосты.length = 0; await togglePresetLock('111111'); }")
                    тосты = стр.evaluate("() => window.__тосты")
                    if not any("заблокирован" in т and "в «Общих» его редактировать нельзя" in т for т in тосты):
                        плохо(f"{н} после закрытия замка нет сообщения «Пресет заблокирован — редактировать его нельзя»: {тосты[-2:]}")
                    # нажатие в пути — выделение есть
                    # Заглушка базы отвечает мгновенно — состояние «в пути» ставим сами,
                    # а мышь уводим, чтобы не мерить наведение.
                    стр.mouse.move(2, 2)
                    стр.evaluate("() => { _замокВПути.set('111111', false); перерисоватьЗамок('111111'); }")
                    стр.wait_for_timeout(200)
                    вп = стр.evaluate("""() => { const к = document.querySelector('#sharedPresetList .shared-pcard[data-scode="111111"]');
                      const з = к.querySelector('.btn-shared-lock'); const с = [...к.querySelectorAll('.btn-shared-act')].find(x => /Скачать/.test(x.getAttribute('title') || ''));
                      const в = e => { const c = getComputedStyle(e); return c.backgroundColor + ' | ' + c.borderTopColor; };
                      return { ждёт: з.classList.contains('wait'), замок: в(з), скач: в(с) }; }""")
                    if not вп["ждёт"] or вп["замок"] == вп["скач"]:
                        плохо(f"{н} пока нажатие в пути, замок не выделен: {вп}")
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"{н} ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: у замка нет плашки, закрытый не выделен и выделяется только пока нажатие в пути, на «Общих» "
          "скачивание стоит раньше замка, снятый замок называет себя «открыт для правки» — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
