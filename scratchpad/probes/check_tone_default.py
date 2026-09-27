#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цвет оформления по умолчанию — «Зелёный-графит».

Константин 27.09.2026: «по умолчанию поставь цветовую тему „Зелёный-графит“».
Бирюза прежде стояла по умолчанию и записывалась в настройки сама; на этот день
цвет в аккаунте выбрал только администратор. Поэтому бирюза без выбора
переезжает на «Зелёный-графит» один раз, а выбранную потом бирюзу не трогаем.

Проба держит, на 390 и 1440:
  • новый человек (в браузере пусто, в аккаунте цвета нет) — «Зелёный-графит»
    с первого кадра и после загрузки, отметка переезда уехала в аккаунт;
  • в браузере бирюза из прежнего умолчания, в аккаунте цвета нет —
    «Зелёный-графит» с первого кадра, без бирюзового кадра;
  • бирюза, выбранная уже после переезда (отметка стоит), — остаётся бирюзой;
  • другой выбранный цвет («Слива») — остаётся;
  • в настройках выбран «Зелёный-графит», когда он стоит по умолчанию.

    python3 check_tone_default.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
НАХОДКИ = []

СЛУЧАИ = [
    # имя, настройки в браузере, настройки в аккаунте, какой тон ждём ('' — бирюза)
    ("новый человек", None, {}, "bmsk"),
    ("бирюза из прежнего умолчания", {"tone": "teal"}, {}, "bmsk"),
    ("бирюза выбрана после переезда", {"tone": "teal", "toneMigratedToBmsk": True}, {"tone": "teal", "toneMigratedToBmsk": True}, ""),
    ("выбрана «Слива»", {"tone": "plum"}, {"tone": "plum"}, "plum"),
]


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


def прогон(бр, порт, ш, имя, местные, профиль, ждём):
    н = f"[{ш}, {имя}]"
    к = бр.new_context(viewport={"width": ш, "height": 900})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
                        "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: "
                        + json.dumps(профиль) + " }];")
    if местные is not None:
        # только при первом открытии: дальше браузер хранит то, что записала страница
        стр.add_init_script("try { if (window === window.top && !sessionStorage.getItem('__проба')) { sessionStorage.setItem('__проба', '1'); "
                            "localStorage.setItem('appSettings_v1', " + json.dumps(json.dumps(местные)) + "); } } catch (e) {}")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="commit")
    стр.wait_for_selector(".header", state="attached")
    первый = стр.evaluate("() => document.documentElement.dataset.tone || ''")
    стр.wait_for_load_state("load"); стр.wait_for_timeout(3000)
    р = стр.evaluate("""() => ({ тон: document.documentElement.dataset.tone || '', настройка: appSettings.tone,
      отметка: appSettings.toneMigratedToBmsk,
      профиль: ((window.__ТАБЛИЦЫ.profiles || [])[0] || {}).app_settings || {} })""")
    if первый != ждём:
        НАХОДКИ.append(f"{н} в первом кадре тон «{первый or 'бирюза'}», ждали «{ждём or 'бирюза'}»")
    if р["тон"] != ждём:
        НАХОДКИ.append(f"{н} после загрузки тон «{р['тон'] or 'бирюза'}», ждали «{ждём or 'бирюза'}»: {р}")
    if not р["отметка"] or not р["профиль"].get("toneMigratedToBmsk"):
        НАХОДКИ.append(f"{н} отметка переезда не стоит или не уехала в аккаунт: {р}")
    if ждём == "bmsk" and ш == 390:
        стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; openSettings(); }")
        стр.wait_for_timeout(400)
        выбран = стр.evaluate("() => { const в = document.getElementById('stToneSelect'); return в ? в.value : null; }")
        if выбран != "bmsk":
            НАХОДКИ.append(f"{н} в настройках выбран «{выбран}», а не «Зелёный-графит»")
    # Второй заход: переезд не повторяется и выбор держится
    стр.reload(wait_until="load"); стр.wait_for_timeout(2500)
    второй = стр.evaluate("() => document.documentElement.dataset.tone || ''")
    if второй != ждём:
        НАХОДКИ.append(f"{н} после перезагрузки тон «{второй or 'бирюза'}», ждали «{ждём or 'бирюза'}»")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    к.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for случай in СЛУЧАИ:
                    прогон(бр, порт, ш, *случай)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: по умолчанию «Зелёный-графит» с первого кадра; бирюза прежнего умолчания переезжает на него один раз, "
          "отметка в аккаунте; выбранная потом бирюза и другой выбранный цвет остаются — на 390 и 1440.")


if __name__ == "__main__":
    главная()
