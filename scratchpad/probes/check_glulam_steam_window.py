#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно в парную 500×500 у клеёного бруса — строкой «Окон и дверей», когда есть парная.

Константин 14.10.2026, снимком разбора проверки: «Окно в парную в брусе также
добавь 500х500 в раздел Окна и двери, если есть парная». У каркаса окно — строка
базы (w7): парная у каркаса есть всегда. У бруса парная собирается опциями, и
строки окна не было вовсе: «Проверка» просила «Добавить окно в парную 500×500»,
а отметить было нечего.

Держит, на брусе:
  • без парной строка окна есть в «Окнах и дверях», но скрыта и не отмечена;
  • отмечена опция парной — строка видна, отмечена, названа как у каркаса,
    своей цены у неё нет: итог от неё не меняется;
  • нажатие по строке её не снимает — её ставит правило;
  • «Проверка» больше не просит окно 500×500;
  • парную сняли — строка снова скрыта и не отмечена;
  • старый расчёт с парной, где строки окна ещё не было, открывается с ней;
на каркасе — строка базы w7 на месте, строки бруса нет.

    python3 check_glulam_steam_window.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ФИКСТУРА["pricing_options"].append({"product": "glulam", "option_id": "kb_s1", "name": "Сборка парного отделения на плавающем каркасе (учебная)",
                                    "section": "steam", "included": False, "price": 250000, "formula": None, "status": None, "sort": 950})
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


СОСТ = """() => { const л = document.getElementById('lbl_kb_steam_window'); const список = л && л.closest('[id^="list_"]');
  return { есть: !!л, видна: !!л && л.getClientRects().length > 0, отмечена: checkedOptions.kb_steam_window === true,
    раздел: список ? список.id : '', имя: (getOpt('kb_steam_window') || {}).name || '', w7: (FRAME_OPTIONS.find(o => o.id === 'w7') || {}).name || '',
    итог: al2ИтогДо(), просит: проверкаПоЧекЛисту().замечания.some(з => /окно в парную 500/i.test(з.т)) }; }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 1000})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }""")
    стр.wait_for_timeout(600)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    д = стр.evaluate(СОСТ)
    факт(д["есть"] and д["раздел"] == "list_windows", f"строка окна стоит в «Окнах и дверях»: {д['раздел'] or 'строки нет'}")
    факт(not д["видна"] and not д["отмечена"], f"без парной строка скрыта и не отмечена: видна {д['видна']}, отмечена {д['отмечена']}")
    без = д["итог"]
    стр.evaluate("() => { document.getElementById('lbl_kb_s1').click(); calc(); }"); стр.wait_for_timeout(400)
    д = стр.evaluate(СОСТ)
    факт(д["видна"] and д["отмечена"], f"с парной строка видна и отмечена: видна {д['видна']}, отмечена {д['отмечена']}")
    факт(bool(д["имя"]) and д["имя"] == д["w7"], f"названа как строка каркаса: «{д['имя']}»")
    парная = стр.evaluate("() => { const ф = плавающийКаркасСостав(true); return (getOpt('kb_s1').price || 0) + (ф.steam ? (Number(((_ставкиРучного.glulam || {}).floating_frame || {}).steam) || 0) : 0); }")
    факт(д["итог"] - без == парная, f"своей цены у окна нет: итог вырос на {д['итог'] - без}, парная с каркасом — {парная}")
    факт(not д["просит"], "«Проверка» не просит окно 500×500 при парной")
    стр.evaluate("() => { const л = document.getElementById('lbl_kb_steam_window'); if (л) л.click(); calc(); }"); стр.wait_for_timeout(300)
    факт(стр.evaluate(СОСТ)["отмечена"], "нажатие по строке окна её не снимает")
    # Старый расчёт: парная отмечена, строки окна в нём нет.
    сост = стр.evaluate("() => { const с = collectState(); delete с.checkedOptions.kb_steam_window; return с; }")
    стр.evaluate("() => { document.getElementById('lbl_kb_s1').click(); calc(); }"); стр.wait_for_timeout(400)
    д = стр.evaluate(СОСТ)
    факт(not д["видна"] and not д["отмечена"] and д["итог"] == без, f"парную сняли — строка скрыта, итог прежний: видна {д['видна']}, итог {д['итог']}")
    стр.evaluate("(с) => { restoreState(с); calc(); }", сост); стр.wait_for_timeout(700)
    д = стр.evaluate(СОСТ)
    факт(д["видна"] and д["отмечена"], f"старый расчёт с парной открывается с окном: видна {д['видна']}, отмечена {д['отмечена']}")
    # Каркас — строка базы на месте, строки бруса нет.
    стр.evaluate("async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }")
    стр.wait_for_timeout(600)
    к = стр.evaluate("() => { const л = document.getElementById('lbl_w7'); return { w7: !!л && л.getClientRects().length > 0 && checkedOptions.w7 === true, бруса: !!document.getElementById('lbl_kb_steam_window') }; }")
    факт(к["w7"] and not к["бруса"], f"на каркасе строка базы w7 на месте, строки бруса нет: {к}")
    факт(not ошибки, f"ошибок страницы нет: {ошибки[:2]}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: у бруса окно в парную 500×500 стоит в «Окнах и дверях», когда есть парная; без парной его нет; каркас прежний.")
