#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Технология запоминается выбором в поле «Технология».

Константин 26.09.2026: «вот эту настройку убери. Просто запоминай последнюю
открытую технологию (именно через поле выбора). Если выбрали КБ, но загрузили
пресет каркас — при следующей загрузке также КБ. А если выбрали каркас в меню
выбора технологии, то при следующей загрузке каркас».

Проба держит:
  • строки «Технология по умолчанию» в настройках нет;
  • выбор бруса в поле ложится в настройки аккаунта, выбор каркаса — тоже;
  • открытый пресет другой технологии запомненное не меняет;
  • при старте без открытого пресета калькулятор открывается запомненной
    технологией, приехавшей с аккаунтом;
  • закрытый для роли брус выбором не запоминается и не включается.

    python3 check_tech_remembered.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
НАХОДКИ = []


def таблицы(настройки):
    return ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
            "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: "
            + json.dumps(настройки, ensure_ascii=False) + " }];")


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


def страница(бр, порт, настройки):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.ошибки = []
    стр.on("pageerror", lambda e: стр.ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(таблицы(настройки))
    # Проба идёт не на тестовом домене: брус открыт роли явно, как в бою.
    стр.add_init_script("window.addEventListener('DOMContentLoaded', () => { window.GLULAM_ROLES = ['admin', 'editor', 'manager']; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(3000)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    return стр


ХОД = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  openSettings(); await ждать(400);
  const строка = /Технология по умолчанию/.test(document.getElementById('settingsBody').innerText);
  closeSettings && closeSettings();
  selectTech('glulam'); await ждать(600);
  const послеБруса = { тех: currentTech, запомнено: appSettings.defaultTech };
  // Пресет каркаса, открытый из бруса.
  await switchTech('frame'); await ждать(300);
  selectProjectOption(0); calc(); await ждать(100);
  const снимок = collectState();
  await switchTech('glulam'); await ждать(300);
  window._пресеты = { pf: { id: 'pf', name: 'Каркасный', savedAt: new Date().toISOString(), shortCode: '123123', state: снимок } };
  loadPreset('pf'); await ждать(1200);
  const послеПресета = { тех: currentTech, запомнено: appSettings.defaultTech };
  setActivePreset(null);
  selectTech('frame'); await ждать(600);
  const послеКаркаса = { тех: currentTech, запомнено: appSettings.defaultTech };
  return { строка, послеБруса, послеПресета, послеКаркаса };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = страница(бр, порт, {})
            р = стр.evaluate(ХОД)
            print("  " + json.dumps(р, ensure_ascii=False))
            if р["строка"]: плохо("в настройках осталась строка «Технология по умолчанию»")
            if р["послеБруса"] != {"тех": "glulam", "запомнено": "glulam"}: плохо(f"выбор бруса не запомнен: {р['послеБруса']}")
            if р["послеПресета"]["тех"] != "frame": плохо("каркасный пресет не открылся каркасом — сценарий не сработал")
            if р["послеПресета"]["запомнено"] != "glulam": плохо(f"открытый каркасный пресет сбил запомненный брус: {р['послеПресета']}")
            if р["послеКаркаса"] != {"тех": "frame", "запомнено": "frame"}: плохо(f"выбор каркаса не запомнен: {р['послеКаркаса']}")
            стр.close()
            # Старт: запомненный брус приезжает с аккаунтом и включается.
            стр = страница(бр, порт, {"defaultTech": "glulam"})
            стр.wait_for_timeout(1500)
            т = стр.evaluate("() => currentTech")
            if т != "glulam": плохо(f"на старте без открытого пресета не включилась запомненная технология: {т}")
            стр.close()
            # Брус закрыт для роли — выбор не запоминается.
            стр = страница(бр, порт, {})
            з = стр.evaluate("""async () => { window.IS_TEST_DOMAIN = false; window.GLULAM_ROLES = ['admin'];
              const было = appSettings.defaultTech; selectTech('glulam'); await new Promise(r => setTimeout(r, 400));
              return { тех: currentTech, запомнено: appSettings.defaultTech, было }; }""")
            if з["тех"] == "glulam" or (з["запомнено"] == "glulam" and з["было"] != "glulam"):
                плохо(f"закрытый брус включился или запомнился: {з}")
            for о in [о for о in стр.ошибки if "supabase.co" not in о][:3]:
                плохо("ошибка страницы: " + о[:160])
            стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: строки «Технология по умолчанию» нет; выбор в поле запоминается в аккаунте — и брус, и каркас; "
          "открытый пресет другой технологии его не сбивает; на старте включается запомненная; закрытый брус не запоминается.")


if __name__ == "__main__":
    главная()
