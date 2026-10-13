#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Название вкладки браузера — общее для всех технологий.

Константин 13.10.2026, снимком вкладки «Спецификация — Каркасные бани |
Баня-МСК» над расчётом клеёного бруса: «В подписи сверху убери „Каркасные
бани“, так как у нас теперь несколько технологий. Поставь общую подпись
Спецификация Баня-МСК».

Проба держит: у загруженной страницы и после смены технологии в обе стороны
заголовок вкладки — «Спецификация Баня-МСК», без названия технологии.

    python3 check_page_title.py
"""
import functools, http.server, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
        + (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8") + ");")
ЖДЁМ = "Спецификация Баня-МСК"
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2000)
    т = стр.title()
    факт(т == ЖДЁМ, f"заголовок загруженной страницы: {т!r}")
    for тех in ("glulam", "frame"):
        стр.evaluate("async (т) => { try { await switchTech(т); } catch (e) {} }", тех)
        стр.wait_for_timeout(600)
        т = стр.title()
        факт(т == ЖДЁМ and "аркас" not in т and "брус" not in т, f"после смены технологии на {тех}: {т!r}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print(f"Чисто: вкладка браузера называется «{ЖДЁМ}» при любой технологии.")
