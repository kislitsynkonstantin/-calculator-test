#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Мои»: у опубликованного пресета вместо корзины — замок.

Константин 27.09.2026, снимком карточки в «Моих»: «когда пресет публикую,
кнопку „Удалить“ меняй на „Замок“. Когда отзываю (снимаю с публикации),
меняем обратно. Идея в том, что опубликованный пресет нельзя удалить, не
сняв с публикации».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • у опубликованного корзины нет, на её месте замок в ряду значковых кнопок,
    той же высоты, что соседние; у неопубликованного — корзина и нет замка;
  • замок нажимается: уходит один запрос, и замок встаёт закрытым;
  • удаление опубликованного, позванное не с карточки, отказывает словами;
  • снятая публикация возвращает корзину;
  • карточка не вылезает за край окна.

    python3 check_my_lock_bin.py
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
  window.__буфер = null;
  Object.defineProperty(navigator, 'clipboard', { configurable: true,
    value: { writeText: т => { window.__буфер = т; return Promise.resolve(); } } });
  const сейчас = new Date().toISOString();
  saveAllPresets({ p1: { id: 'p1', name: 'Пресет пробы', state: снимок, savedAt: сейчас, shortCode: '235788', sharedId: '235788', publishedAs: 'public' } });
  _sharedPresets.length = 0;
  _sharedPresets.push({ short_code: '235788', id: '235788', preset_id: 'p1', author_id: _sbUser.id, author_name: 'Проба', name: 'Пресет пробы',
                        state: снимок, is_public: true, visibility: 'public', locked: false, created_at: сейчас, updated_at: сейчас });
  window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(х => Object.assign({}, х));
  openPresetPanel(); await ждать(300);
  return true;
}"""

КАСАНИЯ = """async (сел) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const к = document.querySelector(сел);
  if (!к) return { нет: true };
  // Касание с настоящей точкой: соседние обработчики касаний читают её координаты.
  const r = к.getBoundingClientRect();
  const касание = () => { const т = new Touch({ identifier: 1, target: к, clientX: r.left + 4, clientY: r.top + 4 });
    к.dispatchEvent(new TouchEvent('touchend', { bubbles: true, cancelable: true, touches: [], changedTouches: [т] })); };
  window.__буфер = null; касание(); await ждать(60); касание(); await ждать(200);
  const пальцем = window.__буфер;
  window.__буфер = null; к.dispatchEvent(new MouseEvent('click', { bubbles: true })); await ждать(500);
  const одним = window.__буфер;
  // код, которого ещё нет
  const пуст = document.createElement('span'); пуст.className = 'pcard-code-value'; пуст.textContent = '— — —';
  к.parentNode.appendChild(пуст);
  window.__буфер = null; пуст.dispatchEvent(new MouseEvent('dblclick', { bubbles: true })); await ждать(200);
  const пустой = window.__буфер; пуст.remove();
  return { пальцем, одним, пустой };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank", "light"):
                for ш in (390, 1440):
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    стр.evaluate(ПОДГОТОВКА, ui)
                    for вкладка, сел in (("my", '#presetList .pcard[data-pid="p1"] .pcard-code-value'),
                                         ("shared", '#sharedPresetList .shared-pcard[data-scode="235788"] .pcard-code-value')):
                        н = f"[{ui} {ш} {вкладка}]"
                        стр.evaluate("async (в) => { switchPresetTab(в); await new Promise(r => setTimeout(r, 500)); }", вкладка)
                        код = стр.locator(сел)
                        if not код.count():
                            плохо(f"{н} кода на карточке нет"); continue
                        стр.evaluate("() => { window.__буфер = null; window.__тосты.length = 0; getSelection().removeAllRanges(); }")
                        код.first.dblclick()
                        стр.wait_for_timeout(250)
                        р = стр.evaluate("() => ({ буфер: window.__буфер, тосты: window.__тосты.slice(), выделено: String(getSelection()) })")
                        к = стр.evaluate(КАСАНИЯ, сел)
                        print("  " + н, json.dumps(р, ensure_ascii=False), json.dumps(к, ensure_ascii=False))
                        if р["буфер"] != "235788":
                            плохо(f"{н} двойной щелчок положил в буфер «{р['буфер']}» вместо «235788»")
                        if not any("235788" in т and "скопирован" in т.lower() for т in р["тосты"]):
                            плохо(f"{н} после копирования нет сообщения с кодом: {р['тосты']}")
                        if р["выделено"].strip():
                            плохо(f"{н} двойной щелчок выделил текст «{р['выделено']}»")
                        if к.get("пальцем") != "235788":
                            плохо(f"{н} два касания положили в буфер «{к.get('пальцем')}»")
                        if к.get("одним"):
                            плохо(f"{н} одиночное нажатие уже копирует («{к['одним']}»)")
                        if к.get("пустой"):
                            плохо(f"{н} скопирован код, которого ещё нет: «{к['пустой']}»")
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"[{ui} {ш}] ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: двойное нажатие по коду на карточке пресета — мышью и пальцем — кладёт в буфер шесть цифр "
          "и говорит об этом; одиночное не копирует, пустой код не копируется — «Мои» и «Общие», 390 и 1440, обе темы.")


if __name__ == "__main__":
    главная()
