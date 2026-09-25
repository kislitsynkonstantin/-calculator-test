#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: разбивка базы по разделам и плавающий каркас.

25.09.2026 Константин прислал таблицу расчёта: вкладка «Клеёный брус» делит
базу долями по разделам, стеновой комплект берёт остаток. Ответы на вопросы:
окна и двери — 8,1 % (в таблице раздел брал 8,1, а остаток стен считался
как от 7,1, и база прибавлялась на 1 %); плавающий каркас парной и душа —
«да, если есть внутренняя отделка»; доли — для всех.

Доли и суммы здесь выдуманные, той же формы, что в базе: настоящие цены в
публичный репозиторий не кладутся. Проба держит:

  • каждый раздел с долей получает базу × долю, стеновой комплект — остаток
    плюс плавающий каркас; сумма разделов = база + каркас, ни рубля сверху;
  • базовая внутренняя отделка снята целиком — нет ни её доли, ни каркаса;
  • ручной проект «Без отделки» — каркаса нет;
  • лист печати показывает ту же сумму стенового комплекта, что и расчёт;
  • карточка комплектации считает тем же правилом: без отделки — без каркаса;
  • у каркасной технологии надбавки нет.

    python3 check_glulam_sections.py
"""
import functools, http.server, json, os, pathlib, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []
БАЗА = 2200000
ДОЛИ = {"insulation": 0.03, "exterior": 0.05, "windows": 0.07, "roof": 0.06, "interior": 0.08, "extra": 0.01}
КАРКАС = {"steam": 111000, "shower": 55000}
ПЛАВ = sum(КАРКАС.values())


def опция(ид, раздел, включена=True):
    return {"product": "glulam", "option_id": ид, "name": "Проба " + ид, "section": раздел,
            "included": включена, "price": None if включена else 10000, "formula": None, "status": None, "sort": 1}


def таблицы():
    пр = lambda продукт, имя: {"product": продукт, "sort": 1, "slug": имя, "name": имя,
            "price_100": 2000000, "price_150": БАЗА, "price_200": 2500000, "floors": "1",
            "roof_type": "двускатная", "warm": 36, "open_area": None, "closed_area": None,
            "facade_area": None, "paint_area": None, "roof_area": None}
    разделы = ["frame", "insulation", "exterior", "windows", "roof", "interior", "extra"]
    return {
        "pricing_projects": [пр("frame", "Каркас проба 6×4"), пр("glulam", "Брус проба 6×6")],
        "pricing_matrix": [],
        "pricing_options": [опция("kb_" + р, р) for р in разделы] + [опция("kb_int2", "interior")],
        "pricing_sections": [{"product": "glulam", "section_key": к, "pct": в, "fixed": 0} for к, в in ДОЛИ.items()],
        "pricing_rates": [{"product": "glulam", "key": "floating_frame", "value": КАРКАС}],
        "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
        "custom_projects": [], "events": [],
    }


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


def плохо(т):
    НАХОДКИ.append(т)


def близко(а, б):
    return abs(а - б) < 1.5


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 1000})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                                + json.dumps(таблицы(), ensure_ascii=False) + ");"
                                "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("""async () => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
              await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
              selectProjectOption(PROJECTS.findIndex(p => p[0] === 'Брус проба 6×6'));
              setThickness(1); calc(); }""")
            стр.wait_for_timeout(400)
            доли_сумма = sum(ДОЛИ.values())
            ждём = {к: БАЗА * в for к, в in ДОЛИ.items()}
            ждём["frame"] = БАЗА * (1 - доли_сумма) + ПЛАВ
            з = стр.evaluate("() => Object.assign({}, _secTotalsCache)")
            for к, в in ждём.items():
                if not близко(з.get(к, 0), в):
                    плохо(f"с отделкой: раздел {к} {з.get(к)} ≠ {в:.0f}")
            всего = sum(з.values())
            if not близко(всего, БАЗА + ПЛАВ):
                плохо(f"сумма разделов {всего:.0f} ≠ база + каркас {БАЗА + ПЛАВ}")
            print(f"  с отделкой: стеновой {з.get('frame'):.0f}, внутренняя {з.get('interior'):.0f}, итого {всего:.0f}")
            # Лист печати — та же сумма стенового комплекта.
            лист = стр.evaluate("() => { openPrintPreview(); setPrintStyle('blank', true); return document.getElementById('printDoc').innerText; }")
            стр.evaluate("() => { try { closePrintPreview(); } catch (e) {} }")
            цифры = {int(re.sub(r"\D", "", м)) for м in re.findall(r"\d[\d\s  ]{3,}\d", лист)}
            if round(ждём["frame"]) not in цифры:
                плохо(f"в листе печати нет суммы стенового комплекта {round(ждём['frame'])}")
            # Карточки комплектаций: без внутренней отделки — без каркаса.
            кк = стр.evaluate("""() => {
              const внутр = OPTIONS.filter(o => o.included && o.section === 'interior').map(o => o.name);
              const был = KOMPL_BASE_OFF.econom; KOMPL_BASE_OFF.econom = new Set(внутр);
              const был2 = KOMPL_BASE_OFF.standart; KOMPL_BASE_OFF.standart = new Set();
              const р = [calcKomplPrice('econom'), calcKomplPrice('standart')];
              KOMPL_BASE_OFF.econom = был; KOMPL_BASE_OFF.standart = был2; return р; }""")
            if not близко(кк[0], БАЗА - ждём["interior"]) or not близко(кк[1], БАЗА + ПЛАВ):
                плохо(f"комплектации: без отделки {кк[0]} (ждали {БАЗА - ждём['interior']:.0f}), с отделкой {кк[1]} (ждали {БАЗА + ПЛАВ})")
            # Внутренняя отделка снята целиком.
            стр.evaluate("() => { OPTIONS.filter(o => o.included && o.section === 'interior').forEach(o => { checkedOptions[o.id] = false; }); calc(); }")
            стр.wait_for_timeout(300)
            з2 = стр.evaluate("() => Object.assign({}, _secTotalsCache)")
            if not близко(з2.get("interior", 0), 0) or not близко(з2.get("frame", 0), БАЗА * (1 - доли_сумма)):
                плохо(f"без отделки: внутренняя {з2.get('interior')}, стеновой {з2.get('frame')} — каркас или доля остались")
            print(f"  без отделки: стеновой {з2.get('frame'):.0f}, внутренняя {з2.get('interior'):.0f}")
            # Ручной проект «Без отделки».
            стр.evaluate("() => { OPTIONS.filter(o => o.included && o.section === 'interior').forEach(o => { checkedOptions[o.id] = true; }); selectedProject._params = { noFinish: true }; calc(); }")
            стр.wait_for_timeout(300)
            з3 = стр.evaluate("() => Object.assign({}, _secTotalsCache)")
            if not близко(з3.get("frame", 0), БАЗА * (1 - доли_сумма)):
                плохо(f"ручной «Без отделки»: стеновой {з3.get('frame')} — каркас остался")
            стр.evaluate("() => { delete selectedProject._params; calc(); }")
            # Каркасная технология — надбавки нет.
            н = стр.evaluate("async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 300)); return typeof плавающийКаркас === 'function' ? плавающийКаркас(true) : 0; }")
            if н:
                плохо(f"у каркасной технологии надбавка {н}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: разделы бруса — база × доля, стеновой — остаток и плавающий каркас при внутренней "
          "отделке; без отделки каркаса нет; печать и комплектации считают так же; у каркаса надбавки нет.")


if __name__ == "__main__":
    главная()
