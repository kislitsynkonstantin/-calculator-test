#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Примечание «Отделка антресоли не входит в расчёт» — у каркаса и бруса.

Константин 18.10.2026: «люк на чердак больше не делаем; антресоль добавь по
умолчанию примечание в калькулятор бруса и каркаса: «Отделка антресоли не
входит в расчёт». Это будет ручная опция, добавь в автоматизацию, если
добавлена отделка антресоли, то это примечание убирать».

Держит, у каркаса и у клеёного бруса:
  • примечание стоит во «Внутренней отделке» последним, прежние примечания
    раздела на своих местах (скрытое глазом помнится по номеру строки);
  • своя позиция отделки антресоли — во «Внутренней отделке» или в любом
    другом разделе — скрывает примечание; сняли — вернулось;
  • своя позиция «Антресоль» без слова отделки (сама конструкция) примечание
    не трогает;
  • отделка добавлена, а примечание вернули глазом — «Проверка» просит его
    убрать и ведёт к нему; скрыли — пункт ушёл.
Названия позиций в пробе выдуманы: репозиторий публичный.

    python3 check_mezzanine_note.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
ПРИМ = "Отделка антресоли не входит в расчёт"
ПРЕЖНИЕ = {"каркас": ["Обшивка мокрых зон (душевая и сан узел) перед чистовым покрытием (плитка) не входит в расчёт"], "брус": []}
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


СОСТ = """(прим) => { const список = SECTION_NOTES.interior || [], место = список.indexOf(прим);
  const ключ = место === -1 ? '' : ключПримечания('interior', место), узел = ключ && document.getElementById('fixedNote_' + ключ);
  const п = проверкаПоЧекЛисту().замечания.find(з => /Отделка антресоли не входит/.test(з.т));
  return { список, место, ключ, узел: !!узел, скрыто: !!ключ && hiddenNotes.has(ключ),
    пункт: п ? { т: п.т, эл: п.эл, р: п.раздел } : null }; }"""
ГЛАЗ = "(ключ) => { toggleNoteVisibility(ключ); calc(); }"
СВОЯ = """([раздел, имя, надо]) => { Object.keys(customOptions).forEach(к => { customOptions[к] = (customOptions[к] || []).filter(co => co.id !== 'ант1'); });
  if (надо) { customOptions[раздел] = customOptions[раздел] || []; customOptions[раздел].push({ id: 'ант1', name: имя, price: 0, checked: true }); }
  if (typeof renderSection === 'function') try { renderSection(раздел); } catch (e) {} calc(); }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def ждать(стр, мс=400):
    стр.wait_for_timeout(мс)


def пройти(стр, т):
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(д["место"] != -1 and д["узел"], f"{т}: примечание стоит во «Внутренней отделке» и нарисовано: место {д['место']}, узел {д['узел']}")
    if д["место"] == -1:
        return
    факт(д["список"][:-1] == ПРЕЖНИЕ[т] and д["список"][-1] == ПРИМ, f"{т}: прежние примечания на своих местах, новое — последним: {д['список']}")
    факт(not д["скрыто"] and not д["пункт"], f"{т}: без отделки антресоли примечание видно, пункта нет")
    стр.evaluate(СВОЯ, ["interior", "Отделка антресоли вагонкой (учебная)", True]); ждать(стр)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(д["скрыто"] and not д["пункт"], f"{т}: своя отделка антресоли во «Внутренней отделке» скрывает примечание: {д}")
    стр.evaluate(ГЛАЗ, д["ключ"]); ждать(стр)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(not д["скрыто"] and bool(д["пункт"]) and д["пункт"]["эл"] == "fixedNote_" + д["ключ"] and д["пункт"]["р"] == "interior",
         f"{т}: примечание вернули глазом при отделке — «Проверка» просит убрать и ведёт к нему: {д['пункт']}")
    стр.evaluate(ГЛАЗ, д["ключ"]); ждать(стр)
    факт(not стр.evaluate(СОСТ, ПРИМ)["пункт"], f"{т}: скрыли снова — пункт ушёл")
    стр.evaluate(СВОЯ, ["interior", "", False]); ждать(стр)
    факт(not стр.evaluate(СОСТ, ПРИМ)["скрыто"], f"{т}: свою позицию сняли — примечание вернулось")
    стр.evaluate(СВОЯ, ["frame", "Обшивка антресоли имитацией бруса (учебная)", True]); ждать(стр)
    факт(стр.evaluate(СОСТ, ПРИМ)["скрыто"], f"{т}: своя обшивка антресоли в другом разделе тоже скрывает примечание")
    стр.evaluate(СВОЯ, ["frame", "", False]); ждать(стр)
    факт(not стр.evaluate(СОСТ, ПРИМ)["скрыто"], f"{т}: сняли — вернулось")
    стр.evaluate(СВОЯ, ["frame", "Антресоль 2×3 м (учебная)", True]); ждать(стр)
    д = стр.evaluate(СОСТ, ПРИМ)
    факт(not д["скрыто"] and not д["пункт"], f"{т}: сама антресоль без отделки примечание не трогает: {д}")
    стр.evaluate(СВОЯ, ["frame", "", False]); ждать(стр)


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
    пройти(стр, "каркас")
    ключ = стр.evaluate(СОСТ, ПРИМ)["ключ"]
    if ключ:
        стр.locator("#fixedNote_" + ключ).scroll_into_view_if_needed()
        стр.screenshot(path=str(pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp") / "mezzanine-note-1440.png"))
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }")
    ждать(стр, 700)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    пройти(стр, "брус")
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
print("Чисто: «Отделка антресоли не входит в расчёт» — у каркаса и бруса, уходит со своей позицией отделки антресоли в любом разделе, а видное при ней просит убрать «Проверка».")
