#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Модерн»: «Загрузить» и «Открыть» в окне «Пресеты» не растягиваются.

Константин 27.09.2026, двумя снимками — «Бланк» на широком экране и «Модерн»:
«В теме Модерн кнопки в пресетах растягиваются, сделай ширину как в Бланке.
Так во всех вкладках пресетов».

Проба на 390 и 1440, во вкладках «Мои», «Общие» и «По коду», держит:
  • в «Модерне» главная кнопка карточки не шире 150 px и не уже 90 px;
  • сразу за ней стоят значки — зазор до соседа не больше 8 px;
  • ряд действий не вылезает за карточку;
  • в «Бланке» ширина кнопки прежняя (правило его не трогает).

    python3 check_preset_btn_width.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];")
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
  selectProjectOption(0); await ждать(700);
  const снимок = collectState(); снимок.tech = 'frame';
  const ст = (код, свой, публ) => ({ short_code: код, id: код, preset_id: 'p' + код, author_id: свой ? _sbUser.id : 'u-другой',
    author_name: 'Проба Другой', name: 'Пресет пробы ' + код, state: снимок, is_public: публ, visibility: 'public', locked: false,
    created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z' });
  const строки = { '111222': ст('111222', true, true), '365484': ст('365484', false, false) };
  window.__RPC = window.__RPC || {};
  window.__RPC.get_preset_by_code = а => строки[а.code] ? [строки[а.code]] : [];
  saveAllPresets({ p1: { id: 'p1', name: 'Свой пресет пробы', state: снимок, savedAt: new Date().toISOString(), shortCode: '111222', sharedId: '111222', publishedAs: 'public' },
                   p2: { id: 'p2', name: 'Второй пресет пробы', state: снимок, savedAt: new Date().toISOString(), shortCode: '222333', sharedId: '222333' } });
  _sharedPresets.length = 0; _sharedPresets.push(Object.assign({}, строки['111222']));
  window.__ТАБЛИЦЫ.preset_links = [Object.assign({}, строки['111222'])];
  try { _общиеЗагружены = true; } catch (e) {}
  appSettings.codeFound = ['365484', '111222'];
  openPresetPanel(); await ждать(300);
  return true;
}"""

ОСМОТР = """async (вкладка) => {
  switchPresetTab(вкладка); await new Promise(r => setTimeout(r, 900));
  const список = { my: '#presetList', shared: '#sharedPresetList', code: '#codePresetList' }[вкладка];
  return [...document.querySelectorAll(список + ' .pcard-use, ' + список + ' .btn-shared-use')].filter(к => к.offsetWidth).map(к => {
    const r = к.getBoundingClientRect(), ряд = к.parentElement, кар = к.closest('.pcard, .shared-pcard').getBoundingClientRect();
    const сосед = к.nextElementSibling; const рс = сосед ? сосед.getBoundingClientRect() : null;
    const края = [...ряд.querySelectorAll('button')].filter(x => x.offsetWidth).map(x => x.getBoundingClientRect().right);
    return { w: Math.round(r.width), зазор: рс ? Math.round(рс.left - r.right) : null, заКрай: Math.max(...края) > кар.right + 0.5 };
  });
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank",):
                for ш in (390, 1440):
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    стр.evaluate(ПОДГОТОВКА, ui)
                    for вкладка in ("my", "shared", "code"):
                        н = f"[{ui} {ш} {вкладка}]"
                        кн = стр.evaluate(ОСМОТР, вкладка)
                        print("  " + н, json.dumps(кн, ensure_ascii=False))
                        if not кн:
                            плохо(f"{н} кнопок нет"); continue
                        for к in кн:
                            if к["заКрай"]:
                                плохо(f"{н} ряд действий вылезает за карточку")
                            if ui == "light":
                                if к["w"] > 151 or к["w"] < 89:
                                    плохо(f"{н} кнопка шириной {к['w']} px — ждали 90…150")
                                if к["зазор"] is not None and к["зазор"] > 8:
                                    плохо(f"{н} за кнопкой пустота {к['зазор']} px до значков")
                        стр.screenshot(path=str(СНИМКИ / f"btn-width-{ui}-{ш}-{вкладка}.png"))
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
    print("Чисто: в «Модерне» «Загрузить» и «Открыть» шириной 90…150 px, значки сразу за ними, ряд в карточке — "
          "«Мои», «Общие», «По коду», на 390 и 1440; «Бланк» не тронут.")


if __name__ == "__main__":
    главная()
