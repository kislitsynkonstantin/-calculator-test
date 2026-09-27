#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Мои»: пока пресеты идут из базы — полоска загрузки, а не «Нет пресетов».

Константин 27.09.2026, снимком пустой вкладки «Мои» с надписью «Нет
сохранённых пресетов. Нажмите „Сохранить как новый“»: «Пока база грузится,
тут пишет так. Тоже поставь полоску загрузки».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • после входа синхронизация пресетов доходит до конца — иначе полоска
    стояла бы вечно;
  • пока «Мои» из базы не пришли, пустой список показывает полоску загрузки
    и слова «Пресеты загружаются…», а не «Нет сохранённых пресетов»;
  • набранный поиск при этом отвечает как прежде — полоска его не глушит;
  • когда синхронизация кончилась, пустой список говорит «Нет сохранённых
    пресетов».

    python3 check_my_loading.py
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


ОСМОТР = """() => { const с = document.getElementById('presetList');
  return { полоска: !!с.querySelector('.plist-load .bm-load'), текст: с.textContent.replace(/\\s+/g, ' ').trim().slice(0, 80) }; }"""


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
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(3500)
                    дошла = стр.evaluate("() => typeof _моиИзБазы !== 'undefined' && _моиИзБазы === true")
                    if not дошла:
                        плохо(f"{н} после входа синхронизация пресетов не отметилась — полоска стояла бы вечно")
                    стр.evaluate("""async (ui) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
                      applyUiStyle(ui, false); saveAllPresets({}); _моиИзБазы = false;
                      openPresetPanel(); await new Promise(r => setTimeout(r, 300)); switchPresetTab('my'); renderPresetList(); }""", ui)
                    р = стр.evaluate(ОСМОТР)
                    print("  " + н, "до базы", json.dumps(р, ensure_ascii=False))
                    if not р["полоска"] or "загружаются" not in р["текст"]:
                        плохо(f"{н} пока «Мои» не пришли из базы, в списке «{р['текст']}» без полоски")
                    стр.screenshot(path=str(СНИМКИ / f"my-loading-{ui}-{ш}.png"))
                    стр.fill("#presetSearchInput", "абвгд"); стр.wait_for_timeout(300)
                    п = стр.evaluate(ОСМОТР)
                    if п["полоска"] or "Ничего не найдено" not in п["текст"]:
                        плохо(f"{н} поиск при загрузке ответил «{п['текст']}»")
                    стр.fill("#presetSearchInput", ""); стр.wait_for_timeout(200)
                    стр.evaluate("async () => { window.__ТАБЛИЦЫ.presets = []; saveAllPresets({}); await sbSyncPresets(true); }"); стр.wait_for_timeout(400)
                    к = стр.evaluate(ОСМОТР)
                    print("  " + н, "после базы", json.dumps(к, ensure_ascii=False))
                    if к["полоска"] or "Нет сохранённых пресетов" not in к["текст"]:
                        плохо(f"{н} после синхронизации в пустом списке «{к['текст']}»")
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
    print("Чисто: пока «Мои» идут из базы — полоска «Пресеты загружаются…», поиск отвечает как прежде, после "
          "синхронизации пустой список говорит «Нет сохранённых пресетов» — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
