#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно базы знаний — ровно в видимый экран: низ кадра с кнопкой меню не уходит за край.

Константин 16.10.2026, снимками с телефона: на главной базы знаний нет круглой
кнопки меню, а в статье она есть. Кнопка в базе на месте — она стоит у нижнего
края кадра. Кадр же был высотой 100vh и ещё 12 px отступа сверху, а на iPhone
100vh выше видимого экрана: низ кадра уходил под панель браузера, и кнопку было
видно только в длинной статье, когда при прокрутке панель пряталась.

Держит, на 390 и 1440 px:
  • высота окна задана через 100dvh — видимый экран, а не наибольший;
  • низ кадра совпадает с низом экрана, не ниже;
  • у подложки окна нет своей прокрутки — двойной прокрутки нет;
  • кнопка у нижнего края кадра (как кнопка меню базы) целиком на экране.
Chromium в контейнере панелей браузера не рисует, и 100vh у него равно видимому,
поэтому на прежней сборке проба ловит выступ кадра на 12 px и прокрутку подложки,
а не саму пропажу кнопки; dvh проверяется по стилю.

    python3 check_kb_frame_fits.py
"""
import functools, http.server, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


КАДР = ('<!doctype html><html><body style="margin:0;height:100vh">'
        '<button id="fab" style="position:fixed;right:20px;bottom:20px;width:48px;height:48px;border-radius:50%">≡</button></body></html>')

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш, в in ((390, 844), (1440, 900)):
        стр = бр.new_page(viewport={"width": ш, "height": в})
        стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        стр.add_init_script(ЗАГЛУШКА)
        стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
        стр.wait_for_timeout(2000)
        стиль = стр.evaluate("() => document.getElementById('guidePanel').getAttribute('style') || ''")
        факт("100dvh" in стиль, f"{ш}: высота окна базы через 100dvh")
        стр.evaluate("""(к) => { const о = document.getElementById('guideOverlay'); о.style.display = 'block';
          const л = document.getElementById('guideLoader'); if (л) л.style.display = 'none';
          document.getElementById('guideFrame').srcdoc = к; }""", КАДР)
        стр.wait_for_timeout(600)
        д = стр.evaluate("""() => { const о = document.getElementById('guideOverlay'), ф = document.getElementById('guideFrame');
          const рф = ф.getBoundingClientRect(); const к = ф.contentDocument.getElementById('fab').getBoundingClientRect();
          return { низКадра: Math.round(рф.bottom), экран: innerHeight, прокрутка: о.scrollHeight - о.clientHeight,
                   низКнопки: Math.round(рф.top + к.bottom) }; }""")
        факт(д["низКадра"] <= д["экран"], f"{ш}: низ кадра {д['низКадра']} в пределах экрана {д['экран']}")
        факт(д["прокрутка"] <= 0, f"{ш}: у подложки окна нет своей прокрутки (лишних {д['прокрутка']} px)")
        факт(д["низКнопки"] <= д["экран"] - 8, f"{ш}: кнопка у нижнего края кадра видна целиком, низ {д['низКнопки']} из {д['экран']}")
        стр.close()
    бр.close()
с.shutdown()

print("\n".join("    ок  " + т for т in ОТЧЁТ)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + т for т in НАХОДКИ) if НАХОДКИ else "Замечаний нет")
raise SystemExit(1 if НАХОДКИ else 0)
