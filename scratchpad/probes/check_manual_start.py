#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка открывается на журнале обновлений.

Константин 27.09.2026: «При нажатии справки первым открывай Журнал
обновлений». Справка одна на тест и бой — она лежит в базе, — поэтому главу
называет калькулятор признаком `data-start` на корне документа, а оболочка
лишь слушается признака. Без него справка открывается на обзоре, как прежде.

Проба на 390 и 1440 держит:
  • на экране глава «Журнал обновлений», в меню отмечен её пункт, текущий
    выпуск раскрыт, страница стоит в начале;
  • на телефоне меню разделов поверх журнала само не выезжает;
  • журнал засчитан просмотренным: отметка ушла в профиль, точка «есть
    новое» рядом с пунктом не горит — и после позднего ответа калькулятора;
  • переход на другую главу из меню работает;
  • оболочка без признака открывается на обзоре, а на телефоне — с меню:
    пока калькулятор признак не шлёт, в бою ничего не меняется.

    python3 check_manual_start.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []

ЦЕНЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "проба", "name": "Проба 6×4",
        "price_100": 100000, "price_150": 150000, "price_200": 200000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
}
ШУМ = ("favicon", "jsdelivr", "supabase.co", "ERR_TUNNEL_CONNECTION_FAILED",
       "ERR_CERT_AUTHORITY_INVALID", "ERR_NAME_NOT_RESOLVED", "[цены]")


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


def ряды():
    return [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"],
             "staff_only": ч["staff_only"], "html": ч["html"]}
            for ч in справка.части("manual") if not ч["staff_only"]]


СОСТОЯНИЕ = """() => {
  const д = document;
  const гл = д.querySelector('.ch.on');
  const пункт = д.querySelector('.sb-a.on');
  const точка = д.getElementById('updDot');
  const первый = д.querySelector('#ch-updates .upd');
  return { глава: гл ? гл.id : null, глав: д.querySelectorAll('.ch.on').length,
           пункт: пункт ? пункт.textContent.trim() : null,
           видна: гл ? getComputedStyle(гл).display !== 'none' : false,
           меню: !!д.querySelector('.sb.mob-open'),
           точка: точка ? getComputedStyle(точка).display : null,
           выпуск: первый ? первый.classList.contains('open') : null,
           сверху: Math.round(scrollY) };
}"""


def через_калькулятор(бр, порт, ш):
    н = f"[калькулятор {ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(ряды(), ensure_ascii=False) + ";\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ЦЕНЫ, ensure_ascii=False) + ");\n"
        "window.addEventListener('DOMContentLoaded', function () {\n"
        "  window._sbProfile = { role: 'manager', updates_seen: 'v0.0.0' };\n"
        "});")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    стр.evaluate("() => openManual()")
    кадр = None
    for _ in range(40):
        стр.wait_for_timeout(200)
        кадр = стр.frame_locator("#manualFrame")
        if кадр.locator(".ch").count():
            break
    # Ответ калькулятора о точке приходит и через 300 мс после открытия — ждём его.
    стр.wait_for_timeout(900)
    р = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
    отметка = стр.evaluate("() => ({ было: (window._sbProfile || {}).updates_seen, версия: appReleaseVersion() })")
    print("  " + н, json.dumps(р, ensure_ascii=False), json.dumps(отметка, ensure_ascii=False))
    if р["глава"] != "ch-updates" or not р["видна"] or р["глав"] != 1:
        плохо(f"{н} справка открылась не на журнале: {р['глава']} (видна {р['видна']}, открытых глав {р['глав']})")
    if not р["пункт"] or "Журнал обновлений" not in р["пункт"]:
        плохо(f"{н} в меню отмечен не журнал: {р['пункт']}")
    if р["выпуск"] is not True:
        плохо(f"{н} текущий выпуск журнала не раскрыт")
    if р["сверху"] > 2:
        плохо(f"{н} страница открылась не с начала: {р['сверху']} px")
    if р["меню"]:
        плохо(f"{н} меню разделов выехало поверх журнала")
    if р["точка"] not in ("none", None):
        плохо(f"{н} точка «есть новое» горит, хотя журнал на экране")
    if отметка["было"] != отметка["версия"]:
        плохо(f"{н} журнал не засчитан просмотренным: в профиле {отметка['было']}, версия {отметка['версия']}")
    стр.screenshot(path=str(СНИМКИ / f"manual-start-{ш}.png"))
    # переход из меню
    кадр.locator("body").evaluate("() => go('presets')")
    стр.wait_for_timeout(200)
    п = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
    if п["глава"] != "ch-presets":
        плохо(f"{н} переход на «Пресеты» не сработал: {п['глава']}")
    for о in [о for о in ошибки if not any(ш_ in о for ш_ in ШУМ)][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def без_признака(бр, порт, ш):
    """Оболочка сама по себе — так её сегодня открывает боевой калькулятор."""
    н = f"[без признака {ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    # Со своего адреса, а не about:blank: там справке закрыт localStorage.
    адрес = f"http://127.0.0.1:{порт}/__manual-probe.html"
    стр.route(адрес, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8",
                                         body=справка.достать("manual")))
    стр.goto(адрес, wait_until="load")
    стр.wait_for_timeout(400)
    р = стр.evaluate(СОСТОЯНИЕ)
    print("  " + н, json.dumps(р, ensure_ascii=False))
    if р["глава"] != "ch-overview":
        плохо(f"{н} без признака справка открылась не на обзоре: {р['глава']}")
    if ш <= 720 and not р["меню"]:
        плохо(f"{н} без признака на телефоне меню разделов не выехало")
    for о in ошибки[:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                через_калькулятор(бр, порт, ш)
                без_признака(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: справка открывается на журнале обновлений — пункт отмечен, выпуск раскрыт, меню не "
          "выезжает, журнал засчитан просмотренным; без признака — обзор, как прежде. На 390 и 1440.")


if __name__ == "__main__":
    главная()
