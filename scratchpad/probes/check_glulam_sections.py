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
  • каркас для душа — при внутренней отделке, для парного — когда в «Парном
    отделении» отмечена хоть одна опция (Константин 25.09.2026); обе строки
    стоят в стеновом комплекте с галочкой, без галочки строки не видно, а
    нажатием её не снять;
  • каркас — часть базы: «База … · опции …» и строка базы разбивки его несут;
  • базовая внутренняя отделка снята целиком — нет ни её доли, ни каркаса душа;
  • ручной проект «Без отделки» — каркаса душа нет;
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
        "pricing_options": [опция("kb_" + р, р) for р in разделы] + [опция("kb_int2", "interior"),
                            опция("kb_steam1", "steam", False)],
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
            ОСТ = БАЗА * (1 - доли_сумма)
            СТРОКИ = """() => ['kb_float_steam', 'kb_float_shower'].map(ид => {
              const л = document.getElementById('lbl_' + ид), ч = document.getElementById('chk_' + ид);
              return { есть: !!л, видна: !!(л && л.getClientRects().length), галочка: !!(ч && ч.checked) }; })"""
            def замер(шаг, ждём_стен, душ, парная):
                з = стр.evaluate("() => Object.assign({}, _secTotalsCache)")
                с = стр.evaluate(СТРОКИ)
                база = стр.evaluate("() => [document.getElementById('baseDisplay').textContent, [...document.querySelectorAll('#breakdownCard .bd-row')].find(r => /Базовая стоимость/.test(r.textContent))?.querySelector('.bd-amt')?.textContent || '']")
                if not близко(з.get("frame", 0), ждём_стен):
                    плохо(f"{шаг}: стеновой {з.get('frame'):.0f} ≠ {ждём_стен:.0f}")
                for (имя, ждём_стр), ст in zip((("парного", парная), ("душа", душ)), с):
                    if not ст["есть"]:
                        плохо(f"{шаг}: строки каркаса для {имя} нет в стеновом комплекте")
                    elif ст["видна"] != ждём_стр or ст["галочка"] != ждём_стр:
                        плохо(f"{шаг}: строка каркаса для {имя}: видна {ст['видна']}, галочка {ст['галочка']}, ждали {ждём_стр}")
                каркас = (КАРКАС["steam"] if парная else 0) + (КАРКАС["shower"] if душ else 0)
                б = re.sub(r"\D", "", база[1])
                if б != str(round(БАЗА + каркас)):
                    плохо(f"{шаг}: строка базы в разбивке {база[1]!r}, ждали {БАЗА + каркас}")
                if str(round(БАЗА + каркас)) not in re.sub(r"[\s\u00a0\u202f]", "", база[0]):
                    плохо(f"{шаг}: «{база[0]}» — база без каркаса")
                print(f"  {шаг}: стеновой {з.get('frame'):.0f}, строки {[ст['галочка'] for ст in с]}, «{база[0]}»")
                return з

            з = замер("с отделкой, без парной", ОСТ + КАРКАС["shower"], True, False)
            for к, в in ДОЛИ.items():
                if not близко(з.get(к, 0), БАЗА * в):
                    плохо(f"раздел {к} {з.get(к)} ≠ {БАЗА * в:.0f}")
            if not близко(sum(з.values()), БАЗА + КАРКАС["shower"]):
                плохо(f"сумма разделов {sum(з.values()):.0f} ≠ база + каркас душа")
            # Нажатие по строке каркаса ничего не меняет.
            стр.evaluate("() => { toggleOpt('kb_float_shower'); }")
            if not стр.evaluate("() => !!checkedOptions['kb_float_shower']"):
                плохо("нажатие сняло строку каркаса для душа")
            # Опция в парном отделении — появляется каркас для парного.
            стр.evaluate("() => { checkedOptions['kb_steam1'] = true; calc(); }")
            стр.wait_for_timeout(300)
            з = замер("с отделкой и парной", ОСТ + ПЛАВ, True, True)
            ждём = {к: БАЗА * в for к, в in ДОЛИ.items()}
            ждём["frame"] = ОСТ + ПЛАВ
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
            # В наборах парной нет — опции набора сброшены, — значит только каркас душа.
            if not близко(кк[0], БАЗА - ждём["interior"]) or not близко(кк[1], БАЗА + КАРКАС["shower"]):
                плохо(f"комплектации: без отделки {кк[0]} (ждали {БАЗА - ждём['interior']:.0f}), с отделкой {кк[1]} (ждали {БАЗА + КАРКАС['shower']})")
            # Внутренняя отделка снята целиком.
            стр.evaluate("() => { OPTIONS.filter(o => o.included && o.section === 'interior').forEach(o => { checkedOptions[o.id] = false; }); calc(); }")
            стр.wait_for_timeout(300)
            з2 = замер("внутренняя отделка снята, парная есть", ОСТ + КАРКАС["steam"], False, True)
            if not близко(з2.get("interior", 0), 0):
                плохо(f"без отделки: внутренняя {з2.get('interior')} — доля осталась")
            # Ручной проект «Без отделки».
            стр.evaluate("() => { OPTIONS.filter(o => o.included && o.section === 'interior').forEach(o => { checkedOptions[o.id] = true; }); selectedProject._params = { noFinish: true }; calc(); }")
            стр.wait_for_timeout(300)
            замер("ручной «Без отделки», парная есть", ОСТ + КАРКАС["steam"], False, True)
            стр.evaluate("() => { checkedOptions['kb_steam1'] = false; calc(); }")
            стр.wait_for_timeout(200)
            замер("ручной «Без отделки», без парной", ОСТ, False, False)
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
    print("Чисто: разделы бруса — база × доля, стеновой — остаток и плавающий каркас: душ при "
          "внутренней отделке, парная при опциях парного отделения; строки ставит правило и базу они "
          "несут; печать и комплектации считают так же; у каркаса надбавки нет.")


if __name__ == "__main__":
    главная()
