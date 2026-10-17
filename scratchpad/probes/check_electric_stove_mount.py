#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Монтаж электрической печи — строка без цены у каркаса и бруса и пункт «Проверки».

Константин 17.10.2026, снимком строки разбора «Электропечи без монтажа»:
«Добавь опцию по монтажу электрической печи в каркас и брус. Просто оставь её
без цены. И чтобы проверка проверяла наличие этой опции отмеченной и
перекидывала на неё, а там уже дальше менеджер вручную вбивает цену».

Держит, у каркаса и у бруса:
  • строка «Монтаж электрической печи» есть в разделе «Печь», без цены — с полем
    «введите сумму»; у бруса — сразу за электрическими печами;
  • электропечь отмечена, монтажа нет — пункт «Проверки» ведёт к строке
    монтажа и просит сначала цену: без суммы строка не отмечается (так
    устроены все строки без цены); сумма вписана и строка отмечена — тихо, и
    сумма идёт в итог; сумму стёрли после отметки — пункт просит её снова;
  • электропечь своей позицией тоже требует монтажа; монтаж своей позицией
    требование снимает; без электропечи — тихо;
  • вписанная сумма живёт в расчёте (porValues).
Цены и названия в пробе выдуманы: репозиторий публичный.

    python3 check_electric_stove_mount.py
"""
import functools, http.server, json, os, pathlib, re, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))


def опция(продукт, ид, раздел, имя, цена, порядок, общая=None):
    ФИКСТУРА["pricing_options"].append({"product": продукт, "option_id": ид, "name": имя, "section": раздел, "included": False,
                                        "price": цена, "formula": None, "status": None, "sort": порядок, "shared_option": общая})


опция("frame", "st3", "stove", "x", 64700, 901)
опция("frame", "st4", "stove", "x", 66660, 902)
опция("glulam", "kb_st21", "stove", "Учебная печь дровяная до 18 м³", 20000, 1270)
опция("glulam", "kb_st38", "stove", "Угловая печь для сауны (учебная)", 64700, 1280, "st3")
опция("glulam", "kb_st39", "stove", "Подвесная электрическая печь (учебная)", 66660, 1285, "st4")
опция("glulam", "kb_st40", "stove", "Учебный дымоход", 15000, 1290)
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


ПУНКТЫ = """() => проверкаПоЧекЛисту().замечания.filter(х => /монтаж|электропеч/i.test(х.т)).map(х => ({ т: х.т, эл: х.эл, р: х.раздел }))"""
СТРОКА = """(ид) => { const л = document.getElementById('lbl_' + ид); if (!л) return null;
  const ном = OPTIONS.findIndex(o => o.id === ид);
  return { имя: (л.querySelector('.opt-name') || {}).textContent || '', раздел: (getOpt(ид) || {}).section, поле: !!document.getElementById('por_' + ид),
           отмечена: !!checkedOptions[ид], до: (OPTIONS[ном - 1] || {}).id, видна: л.getClientRects().length > 0 }; }"""
ОТМЕТИТЬ = "([ид, надо]) => { if (!!checkedOptions[ид] !== надо) toggleOpt(ид); calc(); }"
СВОЯ = "([раздел, имя]) => { customOptions[раздел] = (customOptions[раздел] || []).concat([{ id: 'п' + Date.now(), name: имя, price: 0, checked: true }]); calc(); }"
СБРОС_СВОИХ = "() => { customOptions.stove = []; calc(); }"
ВПИСАТЬ = "([ид, сумма]) => { const п = document.getElementById('por_' + ид); п.value = сумма; п.dispatchEvent(new Event('input', { bubbles: true })); calc(); }"

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def ждать(стр, мс=300):
    стр.wait_for_timeout(мс)


def прогон(стр, тех, печь, монтаж, ждём_после):
    п = стр.evaluate(СТРОКА, монтаж)
    факт(bool(п) and п["имя"] == "Монтаж электрической печи" and п["раздел"] == "stove" and п["поле"] and not п["отмечена"] and п["видна"],
         f"[{тех}] строка «Монтаж электрической печи» в разделе «Печь», без цены — с полем суммы, не отмечена: {п}")
    if ждём_после:
        факт(bool(п) and п["до"] == ждём_после, f"[{тех}] строка стоит сразу за электропечью {ждём_после}: {п and п['до']}")
    if not п:
        return
    факт(not стр.evaluate(ПУНКТЫ), f"[{тех}] электропечи нет — пунктов о монтаже нет: {стр.evaluate(ПУНКТЫ)}")
    стр.evaluate(ОТМЕТИТЬ, [печь, True]); ждать(стр)
    д = стр.evaluate(ПУНКТЫ)
    без = {"т": "Электропечь без монтажа — вписать цену в строке «Монтаж электрической печи» и отметить её", "эл": "lbl_" + монтаж, "р": "stove"}
    факт(д == [без], f"[{тех}] электропечь без монтажа — пункт ведёт к строке монтажа: {д}")
    итог0 = стр.evaluate("() => Math.round(al2ИтогДо())")
    стр.evaluate(ОТМЕТИТЬ, [монтаж, True]); ждать(стр)
    факт(not стр.evaluate("(и) => !!checkedOptions[и]", монтаж) and стр.evaluate(ПУНКТЫ) == [без],
         f"[{тех}] без суммы строка не отмечается, пункт остаётся: {стр.evaluate(ПУНКТЫ)}")
    стр.evaluate(ВПИСАТЬ, [монтаж, "25000"]); стр.evaluate(ОТМЕТИТЬ, [монтаж, True]); ждать(стр)
    итог1 = стр.evaluate("() => Math.round(al2ИтогДо())")
    факт(стр.evaluate("(и) => !!checkedOptions[и]", монтаж) and not стр.evaluate(ПУНКТЫ), f"[{тех}] сумма вписана, строка отмечена — тихо: {стр.evaluate(ПУНКТЫ)}")
    факт(итог1 - итог0 == 25000, f"[{тех}] вписанные 25 000 ₽ идут в итог: {итог0} → {итог1}")
    сост = стр.evaluate("() => collectState()")
    факт(str((сост.get("porValues") or {}).get(монтаж, "")).replace(" ", "").replace(" ", "") == "25000",
         f"[{тех}] сумма монтажа сохраняется в расчёте: {(сост.get('porValues') or {}).get(монтаж)}")
    стр.evaluate(ВПИСАТЬ, [монтаж, ""]); ждать(стр)
    отм = стр.evaluate("(и) => !!checkedOptions[и]", монтаж)
    ждём = [{"т": "Вписать цену монтажа электрической печи", "эл": "lbl_" + монтаж, "р": "stove"}] if отм else [без]
    факт(стр.evaluate(ПУНКТЫ) == ждём, f"[{тех}] сумму стёрли после отметки (строка {'отмечена' if отм else 'снята'}) — пункт снова: {стр.evaluate(ПУНКТЫ)}")
    стр.evaluate(ОТМЕТИТЬ, [монтаж, False]); стр.evaluate(ОТМЕТИТЬ, [печь, False]); ждать(стр)
    стр.evaluate(СВОЯ, ["stove", "Электрическая печь Harvia учебная"]); ждать(стр)
    факт(bool(стр.evaluate(ПУНКТЫ)), f"[{тех}] электропечь своей позицией — тоже просит монтаж: {стр.evaluate(ПУНКТЫ)}")
    стр.evaluate(СВОЯ, ["stove", "Монтаж и подключение электропечи"]); ждать(стр)
    факт(not стр.evaluate(ПУНКТЫ), f"[{тех}] монтаж своей позицией снимает требование: {стр.evaluate(ПУНКТЫ)}")
    стр.evaluate(СБРОС_СВОИХ); ждать(стр)


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
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; selectProjectOption(0); calc(); }")
    ждать(стр, 500)
    прогон(стр, "каркас", "st4", "st35", "st5")
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 800)); selectProjectOption(0); calc(); }")
    ждать(стр, 600)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    прогон(стр, "брус", "kb_st39", "kb_st_electric_mount", "kb_st39")
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
print("Чисто: монтаж электрической печи — строка без цены у каркаса и бруса; «Проверка» ведёт к ней, пока она не отмечена и без суммы.")
