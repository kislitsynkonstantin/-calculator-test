#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Оформление одно — «Бланк».

Константин 27.09.2026: «стиль интерфейса оставь только Бланк — Модерн дальше
не поддерживаем».

Проба держит, на 390 и 1440:
  • в настройках нет строки «Стиль интерфейса» и кнопок «Бланк» / «Модерн»;
  • «Модерн», сохранённый в браузере, не рисуется и в первом кадре — до общего
    скрипта страница уже в «Бланке»;
  • «Модерн», сохранённый в профиле, и у того, кто выбрал его сам после
    прежнего переезда на «Бланк», открывается «Бланком»;
  • вызов applyUiStyle('light') «Модерн» не включает.

    python3 check_blank_only.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
НАХОДКИ = []

# Профиль с «Модерном», выбранным руками уже после прежнего переезда на «Бланк».
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', "
              "app_settings: { uiStyle: 'light', uiStyleMigratedToBlank: true } }];")
# «Модерн» в памяти браузера — до загрузки страницы.
ДО_ЗАГРУЗКИ = "try { localStorage.setItem('appSettings_v1', JSON.stringify({ uiStyle: 'light', uiStyleMigratedToBlank: true })); } catch (e) {}"


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


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS); стр.add_init_script(ДО_ЗАГРУЗКИ)
    # Класс темы в первом кадре: снимаем, как только появилась шапка калькулятора.
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="commit")
    стр.wait_for_selector(".header", state="attached")
    первый = стр.evaluate("() => document.body.className")
    if "ui-light" in первый or "ui-blank" not in первый:
        НАХОДКИ.append(f"{н} в первом кадре не «Бланк»: body.class = «{первый}»")
    стр.wait_for_load_state("load"); стр.wait_for_timeout(3000)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    р = стр.evaluate("() => ({ кл: document.body.className, стиль: appSettings.uiStyle })")
    if "ui-light" in р["кл"] or "ui-blank" not in р["кл"]:
        НАХОДКИ.append(f"{н} «Модерн» из профиля и браузера включился после загрузки: {р}")
    стр.evaluate("() => { try { applyUiStyle('light'); } catch (e) {} }"); стр.wait_for_timeout(200)
    кл = стр.evaluate("() => document.body.className")
    if "ui-light" in кл or "ui-blank" not in кл:
        НАХОДКИ.append(f"{н} applyUiStyle('light') включил «Модерн»: «{кл}»")
    стр.evaluate("() => openSettings()"); стр.wait_for_timeout(500)
    н_ = стр.evaluate("""() => { const т = document.getElementById('settingsBody');
      return { строка: /Стиль интерфейса/.test(т.innerText), кнопки: т.querySelectorAll('.st-ui-btn').length,
               модерн: /Модерн/.test(т.innerText), цвет: /Цвет оформления/.test(т.innerText) }; }""")
    if н_["строка"] or н_["кнопки"] or н_["модерн"]:
        НАХОДКИ.append(f"{н} в настройках остался выбор стиля: {н_}")
    if not н_["цвет"]:
        НАХОДКИ.append(f"{н} вместе со стилем пропал и «Цвет оформления»: {н_}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: оформление одно — «Бланк»: в настройках выбора стиля нет, «Модерн» из браузера и профиля "
          "не включается ни в первом кадре, ни после загрузки, ни вызовом — на 390 и 1440.")


if __name__ == "__main__":
    главная()
