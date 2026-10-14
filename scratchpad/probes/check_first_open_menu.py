#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка — оглавлением, база знаний — главным списком; обе без бокового меню.

Константин 27.09.2026, двумя снимками телефона — справка и база знаний с
выдвинутым меню: «Нажатие первое базы знаний и справки после перезагрузки
чтобы вот так открывало с боковой панелью навигации».

Калькулятор открывается под адресом тестового домена, база знаний — под своим
(обе отдаются из локальных репозиториев): база принимает сообщения только от
калькулятора, и под адресом 127.0.0.1 она бы их не слушала.

Проба держит:
  • 390: справка открывается оглавлением и без меню — и в первый раз, и во
    второй (Константин 13.10.2026: «И тогда сразу открытую боковую панель
    (как сейчас) не нужно показывать» — оглавление само показывает главы);
  • 390: база знаний открывается главным списком и без меню — и в первый
    раз, и во второй (Константин 14.10.2026: «Базу и справку открывать на
    главном списке без бокового меню»; с 27.09.2026 до того первое открытие
    выдвигало меню). Меню не выезжает и тогда, когда калькулятор по-старому
    просит его сообщением «openMenu» — так делает боевой 2.5.17;
  • 1440: меню не выдвигается — на широком экране оно и так стоит сбоку.

    python3 check_first_open_menu.py
"""
import json, os, pathlib, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
БАЗА = pathlib.Path(os.environ.get("BM_KB") or "/home/user/knowledge-baniamsk")
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
КАЛЬК = "https://test.calculator.baniamsk.ru"
# Названия придуманы: настоящее оглавление базы закрыто.
# Уроки ложатся в готовые места страницы базы (lesson-1-3, lesson-3-1…):
# урок без своего места не встаёт, и база пишет «Материалы не загрузились».
БЛОКИ = [dict(id="b1", num=1, ord=1, name_ru="Компания", name_en="Company", sub_ru="Кто мы", sub_en="Who we are"),
         dict(id="b3", num=3, ord=3, name_ru="Продажи", name_en="Sales", sub_ru="От заявки до договора", sub_en="From request to contract")]
УРОКИ = [dict(id=f"lesson-{б}-{о}", block=б, ord=о, status="ready", title_ru=f"Урок {б}.{о}", title_en=f"Lesson {б}.{о}",
              nav_ru=f"Урок {б}.{о}", nav_en=f"Lesson {б}.{о}", sub_ru="", sub_en="",
              body_html=f'<div id="lesson-{б}-{о}"><h2>Урок {б}.{о}</h2></div>') for б, о in ((1, 3), (3, 1), (3, 2))]


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


ТИПЫ = {".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css",
        ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".json": "application/json"}


def отдать(корень):
    def обработать(route):
        путь = route.request.url.split("://", 1)[1].split("/", 1)[1].split("?")[0] or "index.html"
        ф = корень / путь
        if ф.is_dir():
            ф = ф / "index.html"
        if not ф.exists():
            return route.fulfill(status=404, body="")
        route.fulfill(status=200, body=ф.read_bytes(), headers={"content-type": ТИПЫ.get(ф.suffix, "application/octet-stream")})
    return обработать


def ряды():
    return [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"], "staff_only": ч["staff_only"], "html": ч["html"]}
            for ч in справка.части("manual")]


МЕНЮ_СПРАВКИ = """() => { const д = document.getElementById('manualFrame').contentDocument;
  const гл = д && д.querySelector('.ch.on'); return { глава: гл ? гл.id : null, меню: !!(д && д.querySelector('.sb.mob-open')) }; }"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
        for ш in (390, 1440):
            н = f"[{ш}]"
            кон = бр.new_context(viewport={"width": ш, "height": 900}, has_touch=ш < 900, is_mobile=ш < 900)
            кон.route(КАЛЬК + "/**", отдать(КОРЕНЬ))
            кон.route("https://knowledge.baniamsk.ru/**", отдать(БАЗА))
            стр = кон.new_page()
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
                                "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(ряды(), ensure_ascii=False) + ";\n"
                                "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];\n"
                                # Учебные уроки базы: без них база пишет «Материалы не загрузились»,
                                # и главного списка, который проверяется, нет.
                                "window.__ТАБЛИЦЫ.kb_blocks = " + json.dumps(БЛОКИ, ensure_ascii=False) + ";\n"
                                "window.__ТАБЛИЦЫ.kb_lessons = " + json.dumps(УРОКИ, ensure_ascii=False) + ";\n"
                                "window.__ТАБЛИЦЫ.kb_lesson_progress = [];")
            стр.goto(КАЛЬК + "/index.html", wait_until="load")
            стр.wait_for_timeout(3000)
            стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
            # ── справка ──
            стр.evaluate("() => openManual()"); стр.wait_for_timeout(1500)
            с1 = стр.evaluate(МЕНЮ_СПРАВКИ)
            стр.screenshot(path=str(СНИМКИ / f"first-menu-manual-{ш}.png"))
            стр.evaluate("() => closeManual()"); стр.wait_for_timeout(200)
            стр.evaluate("() => openManual()"); стр.wait_for_timeout(1500)
            с2 = стр.evaluate(МЕНЮ_СПРАВКИ)
            стр.evaluate("() => closeManual()")
            print("  " + н, "справка", с1, с2)
            if с1["глава"] != "ch-home" or с2["глава"] != "ch-home":
                плохо(f"{н} справка открылась не на оглавлении: {с1['глава']}, {с2['глава']}")
            if с1["меню"]:
                плохо(f"{н} первое открытие справки выдвинуло меню поверх оглавления")
            if с2["меню"]:
                плохо(f"{н} повторное открытие справки снова с меню")
            if ш >= 900 and с1["меню"]:
                плохо(f"{н} на широком экране у справки выдвинуто меню")
            # ── база знаний ──
            стр.evaluate("() => openGuide()")
            for _ in range(40):
                стр.wait_for_timeout(250)
                if стр.evaluate("() => !!window._kbReady"):
                    break
            стр.wait_for_timeout(600)
            кадр = стр.frame_locator("#guideFrame")
            б1 = кадр.locator("body").evaluate("() => !!document.querySelector('#sidebar.mob-open')")
            главный = кадр.locator("body").evaluate("() => { const с = document.querySelector('.hs-list'); return !!с && с.getClientRects().length > 0; }")
            # Просьба старого калькулятора — база её не выполняет.
            стр.evaluate("() => { const ф = document.getElementById('guideFrame'); ф.contentWindow.postMessage({ type: 'openMenu' }, window.KB_ORIGIN); }")
            стр.wait_for_timeout(400)
            б_старый = кадр.locator("body").evaluate("() => !!document.querySelector('#sidebar.mob-open')")
            готова = стр.evaluate("() => !!window._kbReady")
            стр.screenshot(path=str(СНИМКИ / f"first-menu-kb-{ш}.png"))
            кадр.locator("body").evaluate("() => closeMobMenu()")
            стр.evaluate("() => closeGuide()"); стр.wait_for_timeout(200)
            стр.evaluate("() => openGuide()"); стр.wait_for_timeout(800)
            б2 = кадр.locator("body").evaluate("() => !!document.querySelector('#sidebar.mob-open')")
            print("  " + н, "база", {"готова": готова, "первое": б1, "главный": главный, "по просьбе": б_старый, "второе": б2})
            if not готова:
                плохо(f"{н} база знаний не сказала, что готова — проверять нечего")
            elif б1:
                плохо(f"{н} первое открытие базы знаний выдвинуло меню")
            if готова and not главный:
                плохо(f"{н} база знаний открылась не главным списком")
            if б_старый:
                плохо(f"{н} база выдвинула меню по просьбе старого калькулятора («openMenu»)")
            if б2:
                плохо(f"{н} повторное открытие базы знаний снова выдвинуло меню")
            if ш >= 900 and б1:
                плохо(f"{н} на широком экране у базы знаний выдвинуто меню")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                плохо(f"{н} ошибка страницы: {о[:160]}")
            кон.close()
        бр.close()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: справка открывается оглавлением, база знаний — главным списком; обе без бокового меню, "
          "и база не выдвигает его даже по просьбе старого калькулятора.")


if __name__ == "__main__":
    главная()
