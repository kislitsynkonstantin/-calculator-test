#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимок: сообщение «Открыт общий пресет» вместе со значком в углу.

    BM_ROOT=<сборка> python3 shot_toast_chip.py <папка> <подпись>
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def главная():
    куда, подпись = pathlib.Path(sys.argv[1]), sys.argv[2]
    куда.mkdir(parents=True, exist_ok=True)
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а): pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
        for ш, в in ((390, 844), (1440, 900)):
            for низ in (False, True):
                стр = бр.new_page(viewport={"width": ш, "height": в}, device_scale_factor=2)
                стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                стр.evaluate("""async (низ) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
                  applyUiStyle('blank', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
                  _sharedPresets.length = 0;
                  _sharedPresets.push({ short_code: '111222', id: '111222', name: 'Хай-Тек Баня «Виттен» 9×5 + терраса 30 м2 · 01.09.26',
                    author_name: 'Максим Г.', author_id: 'u-другой', is_public: true, locked: true, state: {} });
                  _activeSharedCode = '111222'; updateSharedModeIndicator();
                  await new Promise(r => setTimeout(r, 900));
                  if (низ) { window.scrollTo(0, document.body.scrollHeight); await new Promise(r => setTimeout(r, 900)); }
                  showToast('Открыт общий пресет: Хай-Тек Баня «Виттен» 9×5 + терраса 30 м2 · 01.09.26', 60000); }""", низ)
                стр.wait_for_timeout(1200)
                стр.screenshot(path=str(куда / f"toast-{ш}{'-strip' if низ else ''}-{подпись}.png"))
                стр.close()
        бр.close()
    с.shutdown()


if __name__ == "__main__":
    главная()
