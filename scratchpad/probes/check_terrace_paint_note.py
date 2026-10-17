#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Примечание «Покраска террасы не входит в расчёт» — у каркаса и бруса.

Константин 17.10.2026, снимком строки «Покраска террасы (5-7, 7-9)» из разбора
проверок: «Это сделай: добавь автоматизацию на примечание и добавь в брусе».

Держит, у каркаса и у клеёного бруса:
  • примечание стоит в разделе «Покраска»; у бруса — последним, и прежние три
    примечания раздела на своих местах: скрытое глазом помнится по номеру
    строки, и вставка выше сдвинула бы его в сохранённых расчётах;
  • отметили покраску террасной доски — примечание скрыто глазом, сняли —
    вернулось; у бруса так же через общую с каркасом строку, а снятая своя
    строка бруса в старом расчёте тоже скрывает;
  • своя позиция покраски террасы в «Покраске» скрывает примечание;
  • покраска выбрана, а примечание видно (вернули глазом или своя позиция в
    другом разделе) — «Проверка» просит убрать примечание и ведёт к нему;
    скрыли — пункт ушёл; покраски нет — пункта нет.
Названия опций и цены в пробе выдуманы: репозиторий публичный.

    python3 check_terrace_paint_note.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
for продукт, ид, имя, статус, общая, п in [
        ("frame", "p18", "Учебная покраска террасной доски маслом", None, None, 901),
        ("glulam", "kb_p20", "Учебная покраска террасной доски маслом (общая)", "legacy", "p18", 902),
        ("glulam", "kb_p8", "Учебная покраска террасной доски маслом (своя, снятая)", None, None, 903)]:
    ФИКСТУРА["pricing_options"].append({"product": продукт, "option_id": ид, "name": имя, "section": "paint", "included": False,
                                        "price": 1000, "formula": None, "status": статус, "sort": п, "shared_option": общая})
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
ПРИМ = "Покраска террасы не входит в расчёт"
ПРЕЖНИЕ_БРУСА = ["Покраска строения не входит в расчёт",
                 "Лессирующий состав краски может удорожать стоимость покраски. Согласовывается при выборе цвета и состава перед началом окрашивания",
                 "Покраска перголы и ограждений на террасе не входит в расчёт"]
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


СОСТ = """(прим) => { const список = SECTION_NOTES.paint || [], место = список.indexOf(прим);
  const ключ = место === -1 ? '' : ключПримечания('paint', место), узел = ключ && document.getElementById('fixedNote_' + ключ);
  const п = проверкаПоЧекЛисту().замечания.find(з => /Покраска террасы не входит/.test(з.т));
  return { список, место, ключ, узел: !!узел, скрыто: !!ключ && hiddenNotes.has(ключ), узелСкрыт: !!узел && узел.classList.contains('note-hidden'),
    пункт: п ? { т: п.т, эл: п.эл, р: п.раздел } : null }; }"""
ОТМЕТИТЬ_JS = "([ид, надо]) => { if (!!checkedOptions[ид] !== надо) { const л = document.getElementById('lbl_' + ид); if (л) л.click(); else toggleOpt(ид); } calc(); }"
ГЛАЗ = "(ключ) => { toggleNoteVisibility(ключ); calc(); }"
СВОЯ = """([раздел, имя, надо]) => { customOptions[раздел] = (customOptions[раздел] || []).filter(co => co.id !== 'тер1');
  if (надо) customOptions[раздел].push({ id: 'тер1', name: имя, price: 0, checked: true }); calc(); }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def ждать(стр, мс=400):
    стр.wait_for_timeout(мс)


def отметить(стр, ид, надо):
    стр.evaluate(ОТМЕТИТЬ_JS, [ид, надо]); ждать(стр)


def пройти(стр, т, строка):
    """Общий ход для обеих технологий: строка — та, что менеджер видит."""
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(д["место"] != -1 and д["узел"], f"{т}: примечание стоит в разделе «Покраска» и нарисовано: место {д['место']}, узел {д['узел']}")
    if д["место"] == -1:
        return
    факт(not д["скрыто"] and not д["пункт"], f"{т}: без покраски террасы примечание видно, пункта нет: {д}")
    отметить(стр, строка, True)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(д["скрыто"] and д["узелСкрыт"] and not д["пункт"], f"{т}: отметили покраску террасы — примечание скрыто глазом, пункта нет: {д}")
    стр.evaluate(ГЛАЗ, д["ключ"]); ждать(стр)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(not д["скрыто"] and bool(д["пункт"]) and д["пункт"]["т"] == "Убрать примечание «Покраска террасы не входит в расчёт» — покраска террасы выбрана"
         and д["пункт"]["эл"] == "fixedNote_" + д["ключ"] and д["пункт"]["р"] == "paint",
         f"{т}: примечание вернули глазом при покраске — «Проверка» просит убрать и ведёт к нему: {д['пункт']}")
    стр.evaluate(ГЛАЗ, д["ключ"]); ждать(стр)
    факт(not стр.evaluate(СОСТ, ПРИМ)["пункт"], f"{т}: скрыли снова — пункт ушёл")
    отметить(стр, строка, False)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(not д["скрыто"] and not д["пункт"], f"{т}: сняли покраску террасы — примечание вернулось само, пункта нет: {д}")
    стр.evaluate(СВОЯ, ["paint", "Покраска террасы маслом (своя)", True]); ждать(стр)
    факт(стр.evaluate(СОСТ, ПРИМ)["скрыто"], f"{т}: своя позиция покраски террасы в «Покраске» скрывает примечание")
    стр.evaluate(СВОЯ, ["paint", "", False]); ждать(стр)
    факт(not стр.evaluate(СОСТ, ПРИМ)["скрыто"], f"{т}: свою позицию сняли — примечание вернулось")
    стр.evaluate(СВОЯ, ["extra", "Обработка террасы маслом (своя)", True]); ждать(стр)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(not д["скрыто"] and bool(д["пункт"]), f"{т}: своя покраска террасы в другом разделе — примечание видно, «Проверка» просит убрать: {д['пункт']}")
    стр.evaluate(СВОЯ, ["extra", "", False]); ждать(стр)
    факт(not стр.evaluate(СОСТ, ПРИМ)["пункт"], f"{т}: своя позиция снята — пункта нет")


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
    ждать(стр, 600)

    пройти(стр, "каркас", "p18")

    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }")
    ждать(стр, 700)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    список = стр.evaluate("() => (SECTION_NOTES.paint || []).slice()")
    факт(список[:3] == ПРЕЖНИЕ_БРУСА and список[-1:] == [ПРИМ], f"брус: прежние примечания покраски на своих местах, новое — последним: {список}")
    видна = стр.evaluate("() => { const о = getOpt('kb_p20'); return { есть: !!о, общая: о && о.общаяС, видна: !!о && isOptionVisible(о), строка: !!document.getElementById('lbl_kb_p20') }; }")
    факт(видна["есть"] and видна["видна"] and видна["строка"], f"брус: покраска террасы — общая с каркасом строка, видна: {видна}")
    пройти(стр, "брус", "kb_p20")
    # Старый расчёт бруса: отмечена снятая своя строка.
    стр.evaluate("() => { checkedOptions.kb_p8 = true; calc(); }"); ждать(стр)
    факт(стр.evaluate(СОСТ, ПРИМ)["скрыто"], "брус: снятая своя строка покраски террасы в старом расчёте тоже скрывает примечание")
    стр.evaluate("() => { checkedOptions.kb_p8 = false; calc(); }"); ждать(стр)
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
print("Чисто: «Покраска террасы не входит в расчёт» — у каркаса и бруса, уходит с покраской террасы, а видное при покраске просит убрать «Проверка».")
