#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Названия позиций в файле — без опечаток и с единым написанием размеров.

Константин 13.10.2026, разбором раздела «Парное отделение» бруса: «Проверь на
опечатки в брусе». Опечатки нашлись в строках базы («тены и потолок», «на
липа», «парного отделение», «элемонтаж», «светолиодного», «на учаскте»,
«защитный воском») — их поправили запросом с условием на прежний текст; проба
базу не видит. А в файле у бруса свои названия — стеновой комплект по
сечению («клееного … 125х185» с русской «х»), и их держит эта проба.

Держит, во всех названиях позиций файла — опций каркаса, базовой
комплектации бруса по сечению и примечаний разделов:
  • размер пишется знаком «×», а не буквой «х»/«Х» и не «*»;
  • нет известных опечаток из разбора и «клееного» без «ё»;
  • стеновой комплект бруса называет своё сечение: 125, 160, 205 × 185 мм.

    python3 check_glulam_names.py
"""
import functools, http.server, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
        + (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8") + ");")
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

СБОР = r"""() => {
  const имена = [];
  (typeof FRAME_OPTIONS !== 'undefined' ? FRAME_OPTIONS : []).forEach(o => имена.push(['опция ' + o.id, o.name]));
  Object.entries(KB_BASE_ITEMS_BY_THICKNESS).forEach(([ид, сп]) => сп.forEach((н, i) => имена.push([ид + ' сечение ' + i, н])));
  [typeof FRAME_NOTES !== 'undefined' ? FRAME_NOTES : {}, typeof KB_SECTION_NOTES !== 'undefined' ? KB_SECTION_NOTES : {}].forEach(п =>
    Object.entries(п).forEach(([к, сп]) => (сп || []).forEach(н => имена.push(['примечание ' + к, typeof н === 'string' ? н : (н && н.text) || '']))));
  return { имена, стены: KB_BASE_ITEMS_BY_THICKNESS.kb_bp_fr_1 };
}"""
ОПЕЧАТКИ = ("тены и потолок", "на липа", "парного отделение", "элемонтаж", "светолиод", "учаскте",
            "защитный воском", "замены доски", "вятяжн", "мечном", "клееного")

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(1500)
    д = стр.evaluate(СБОР)
    бр.close()
с.shutdown()

import re
размер = re.compile(r"\d\s?[хХ*]\s?\d")
плохие_размеры = [f"{где}: «{н}»" for где, н in д["имена"] if н and размер.search(н)]
факт(not плохие_размеры, f"размеры знаком «×» во всех {len(д['имена'])} названиях: {плохие_размеры[:4]}")
опечатки = [f"{где}: «{н}»" for где, н in д["имена"] if н and any(о in н.lower() for о in ОПЕЧАТКИ)]
факт(not опечатки, f"известных опечаток нет: {опечатки[:4]}")
стены = д["стены"]
факт(len(стены) == 3 and all(f"{с_}×185 мм" in н for с_, н in zip(("125", "160", "205"), стены)),
     f"стеновой комплект по сечению: {стены}")

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: названия позиций в файле без опечаток, размеры знаком «×».")
