#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Площадь открытой террасы — из проекта; сетка от грызунов у бруса — опцией.

Константин 13.10.2026, ответом на два вопроса после разбора бруса:
«Сетку от грызунов у разделе 8 убери. В базе тоже убери, оставь как опцию
только» и «по террасе брать, когда есть откуда».

Держит, на каркасе (опция «Устройство открытой террасы», 144 000 ₽ за 12 м²):
  • проект с открытой террасой 20 м² — площадь опции 20, цена 240 000 ₽;
  • проект без открытой террасы — 12 м², 144 000 ₽, как прежде;
  • вписанная руками площадь сильнее проекта и не сбрасывается сменой проекта;
  • расчёт, сохранённый до правки (без признака qtyFromProject), с отмеченной
    террасой открывается с 12 м² — сумма та же, что была;
  • новый сохранённый расчёт открывается с площадью проекта;
и на брусе:
  • строки «Защитная сетка от грызунов» в базовой комплектации нет;
  • опция сетки стоит в разделе 2 «Стеновой комплект и перекрытия», а не в 8;
  • старый расчёт, где строка базы отмечена, открывается без неё.

    python3 check_terrace_from_project.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
# Первому проекту каркаса — открытая терраса 20 м²; у бруса — строки сетки,
# как в базе: строка базы в разделе 2 и платная опция в разделе 8.
ФИКСТУРА["pricing_projects"][0]["open_area"] = 20
ФИКСТУРА["pricing_options"] += [
    {"product": "glulam", "option_id": "kb_bp_fr_13", "name": "Защитная сетка от грызунов", "section": "frame",
     "included": True, "price": None, "formula": None, "status": None, "sort": 220},
    {"product": "glulam", "option_id": "kb_i3", "name": "Защитная сетка от грызунов", "section": "interior",
     "included": False, "price": 12006, "formula": None, "status": None, "sort": 860},
]
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
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

ТЕРРАСА = """() => { const о = getOpt('e10'), п = document.getElementById('qtyval_e10'), ц = document.getElementById('optprice_e10');
  const и = document.querySelector('#lbl_e10 .opt-name');
  return { кол: getOptQty(о), поле: п ? String(п.value ?? п.textContent).trim() : '', цена: ц ? ц.textContent.replace(/\\s/g, ' ').trim() : '',
           имя: и ? и.textContent.replace(/\\s+/g, ' ').trim() : '',
           проект: selectedProject ? selectedProject[0] : null }; }"""

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
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      const о = getOpt('e10'); if (о) о.price = 144000; }""")

    def проект(имя):
        стр.evaluate("(и) => { selectProjectOption(PROJECTS.findIndex(p => p[0] === и)); renderOptionSections(); calc(); }", имя)
        стр.wait_for_timeout(400)
        return стр.evaluate(ТЕРРАСА)

    д = проект("Проба дом 8×8")
    факт(д["кол"] == 20 and д["поле"] == "20" and "240 000" in д["цена"] and д["имя"].endswith("20 м²"), f"[каркас] проект с террасой 20 м², и в названии 20 м²: {д}")
    д = проект("Проба дом 6×6")
    факт(д["кол"] == 12 and д["поле"] == "12" and "144 000" in д["цена"] and д["имя"].endswith("12 м²"), f"[каркас] проект без открытой террасы — 12 м²: {д}")
    стр.evaluate("() => { задатьКоличество('e10', '15'); }"); стр.wait_for_timeout(300)
    д = проект("Проба дом 8×8")
    факт(д["кол"] == 15 and "180 000" in д["цена"], f"[каркас] вписанные 15 м² не сбрасываются сменой проекта: {д}")

    # Старый расчёт: без признака, терраса отмечена, площадь не вписана.
    стр.evaluate("() => { formulaOverrides = {}; toggleOpt('e10'); calc(); }"); стр.wait_for_timeout(300)
    сост = стр.evaluate("() => collectState()")
    факт(сост.get("qtyFromProject") is True and сост["checkedOptions"].get("e10"), f"[каркас] новый расчёт сохраняется с признаком: {сост.get('qtyFromProject')}")
    старый = dict(сост); старый.pop("qtyFromProject", None)
    стр.evaluate("(с) => { restoreState(с); renderOptionSections(); calc(); }", старый); стр.wait_for_timeout(600)
    д = стр.evaluate(ТЕРРАСА)
    факт(д["кол"] == 12 and "144 000" in д["цена"], f"[каркас] расчёт, сохранённый до правки, — по-прежнему 12 м²: {д}")
    стр.evaluate("(с) => { restoreState(с); renderOptionSections(); calc(); }", сост); стр.wait_for_timeout(600)
    д = стр.evaluate(ТЕРРАСА)
    факт(д["кол"] == 20 and "240 000" in д["цена"], f"[каркас] новый расчёт открывается с площадью проекта: {д}")

    # Брус: сетка от грызунов — в чистой странице, без расчёта каркаса.
    стр.close()
    стр = бр.new_page(viewport={"width": 1440, "height": 1000})
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }")
    стр.wait_for_timeout(700)
    б = стр.evaluate("""() => { const вид = э => !!э && э.getClientRects().length > 0;
      const база = document.getElementById('lbl_kb_bp_fr_13'), оп = document.getElementById('lbl_kb_i3');
      const о = getOpt('kb_i3');
      return { база: вид(база), опция: вид(оп), раздел: оп ? (оп.closest('[id^=sec_opts_]') || {}).id : null,
               включена: !!checkedOptions.kb_i3, вСумме: !!checkedOptions.kb_bp_fr_13,
               тех: currentTech, вДанных: о ? [о.section, о.price, isOptionVisible(о)] : null }; }""")
    факт(not б["база"] and not б["вСумме"], f"[брус] в базовой комплектации сетки нет: {б}")
    факт(б["опция"] and б["раздел"] == "sec_opts_frame" and not б["включена"], f"[брус] сетка — опцией в разделе 2: {б}")
    с2 = стр.evaluate("() => { const с = collectState(); с.checkedOptions = Object.assign({}, с.checkedOptions, { kb_bp_fr_13: true }); return с; }")
    стр.evaluate("(с) => { restoreState(с); calc(); }", с2); стр.wait_for_timeout(600)
    б = стр.evaluate("() => ({ отмечена: !!checkedOptions.kb_bp_fr_13, видна: !!document.getElementById('lbl_kb_bp_fr_13') && document.getElementById('lbl_kb_bp_fr_13').getClientRects().length > 0 })")
    факт(not б["отмечена"] and not б["видна"], f"[брус] старый расчёт со строкой базы открывается без неё: {б}")
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
print("Чисто: площадь террасы — из проекта, когда есть; старые расчёты — по 12 м²; сетка от грызунов у бруса — опцией в разделе 2.")
