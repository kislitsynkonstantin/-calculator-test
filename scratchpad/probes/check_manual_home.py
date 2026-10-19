#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка открывается оглавлением.

Константин 13.10.2026, снимком варианта 03 макета manual-home-v1: «Это делаем.
И тогда сразу открытую боковую панель (как сейчас) не нужно показывать».

Справка одна на тест и бой (лежит в базе), поэтому оглавление стоит в обёртке
теста, а главу открытия называет калькулятор признаком data-start. Проба держит:

  через калькулятор (тест), на 390 и 1440, днём и ночью:
  • справка открывается на оглавлении, в меню отмечен пункт «Главная»; меню
    разделов на телефоне не выезжает — ни при первом открытии после загрузки,
    ни при повторном;
  • в оглавлении разделы меню по порядку, в каждом — главы со значком,
    названием и строкой «о чём»; ни журнала, ни «Лога развития» среди глав нет
    (и у администратора тоже); под оглавлением нет ссылки «Дальше»;
  • сверху «Что нового: Версия … — N изменений» по верхней карточке журнала,
    с точкой «есть новое», пока журнал не открыт; журнал не засчитан
    просмотренным, пока его не открыли; нажатие на строку открывает журнал,
    гасит точку и засчитывает журнал;
  • на компьютере три колонки рядом, на телефоне — одна; ничего не вылезает и
    не обрезано, строка главы на телефоне не ниже 44 px; глава из оглавления
    и пункт «Главная» в меню открываются;
  • в печати оглавления нет;

  в бою (оболочка с ?contour=prod и признаками боевого калькулятора) — с
  выпуска 2.5.17 так же, как на тесте:
  • оглавление и пункт «Главная» есть, справка открывается на оглавлении,
    меню на телефоне не выезжает; возврат из статьи о выпуске — на журнал.

    python3 check_manual_home.py
"""
import functools
import http.server
import json
import os
import pathlib
import re
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ, ОТЧЁТ = [], []
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
        + (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8") + ");")
ШУМ = ("favicon", "jsdelivr", "supabase.co", "ERR_TUNNEL_CONNECTION_FAILED",
       "ERR_CERT_AUTHORITY_INVALID", "ERR_NAME_NOT_RESOLVED", "[цены]")


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def ряды(админ=False):
    return [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"], "staff_only": ч["staff_only"], "html": ч["html"]}
            for ч in справка.части("manual") if админ or not ч["staff_only"]]


# Разделы и главы меню — по исходнику оболочки, как их видит менеджер.
def меню_ожидаемое():
    оболочка = (pathlib.Path("/home/user/vscode-workspace/docs/справка") / "manual--shell.html").read_text(encoding="utf-8")
    нав = оболочка[оболочка.index('<nav class="sb-nav">'):оболочка.index('</nav>')]
    после = нав[нав.index('<div class="sb-group"'):]
    разделы = []
    # Разделы стали сворачиваемыми (19.10.2026): заголовок — <div class="sb-group" …><span>Имя</span>.
    # Раздел только для теста («Статьи») в бою вырезается, но проба смотрит тест — он в счёте.
    for м in re.finditer(r'<div class="sb-group"[^>]*><span>([^<]+)</span>|go\(\'([a-z-]+)\'\)', после):
        if м.group(1):
            разделы.append([м.group(1).strip(), []])
        elif м.group(2):
            разделы[-1][1].append(м.group(2))
    return разделы


СОСТОЯНИЕ = """() => {
  const д = document, вид = э => !!э && э.getClientRects().length > 0 && getComputedStyle(э).display !== 'none';
  const гл = д.querySelector('.ch.on'), пункт = д.querySelector('.sb-a.on');
  const дом = д.getElementById('ch-home');
  const секции = дом ? [...дом.querySelectorAll('.hm-cols > section')] : [];
  const главы = дом ? [...дом.querySelectorAll('.hm-ch')] : [];
  const w = innerWidth;
  const видимые = дом && вид(дом) ? [...дом.querySelectorAll('*')].filter(вид) : [];
  const лево = секции.map(с => Math.round(с.getBoundingClientRect().left));
  const точка = д.getElementById('homeDot');
  return {
    глава: гл ? гл.id : null, глав: д.querySelectorAll('.ch.on').length, пункт: пункт ? [...пункт.childNodes].filter(у => у.nodeType === 3).map(у => у.textContent).join('').trim() : null,
    меню: !!д.querySelector('.sb.mob-open'), естьДом: !!дом, пунктДом: [...д.querySelectorAll('.sb-a')].some(а => (а.getAttribute('onclick') || '') === "go('home')"),
    разделы: секции.map(с => [с.querySelector('.hm-nm').textContent.trim(), [...с.querySelectorAll('.hm-ch')].map(г => г.getAttribute('data-go'))]),
    безЗначка: главы.filter(г => !г.querySelector('svg')).length, безОчём: главы.filter(г => !(г.querySelector('small') || {}).textContent).length,
    строка: ((дом && дом.querySelector('.hm-news .t')) || {}).textContent || '',
    точка: точка ? getComputedStyle(точка).display : null,
    дальше: дом ? дом.querySelectorAll('.next-ch').length : 0,
    колонок: new Set(лево).size,
    вылез: видимые.filter(э => { const б = э.getBoundingClientRect(); return б.width && (б.right > w + .5 || б.left < -.5); }).map(э => э.className || э.tagName).slice(0, 4),
    обрез: видимые.filter(э => /hm-/.test(э.className) || э.tagName === 'B' || э.tagName === 'SMALL').filter(э => э.scrollWidth > э.clientWidth + 1).map(э => э.className || э.tagName).slice(0, 4),
    вширь: д.documentElement.scrollWidth - д.documentElement.clientWidth,
    высота: главы.length ? Math.min(...главы.map(г => Math.round(г.getBoundingClientRect().height))) : 0,
    // «Журнал обновлений» в меню с горящей точкой — в одну строку, как соседние пункты.
    журналВменю: (() => { const ж = [...д.querySelectorAll('.sb-a')].find(а => (а.getAttribute('onclick') || '') === "go('updates')");
      const о = [...д.querySelectorAll('.sb-a')].find(а => (а.getAttribute('onclick') || '') === "go('overview')");
      return ж && о && вид(ж) ? [Math.round(ж.getBoundingClientRect().height), Math.round(о.getBoundingClientRect().height)] : null; })(),
    журнал: (() => { const к = д.querySelector('#ch-updates .upd'); if (!к) return null;
      return { вер: (к.querySelector('.upd-ver') || {}).textContent, правок: к.querySelectorAll('.upd-item').length }; })(),
  };
}"""


def кадр_справки(стр):
    for _ in range(50):
        стр.wait_for_timeout(200)
        к = стр.frame_locator("#manualFrame")
        if к.locator(".ch").count():
            return к
    return стр.frame_locator("#manualFrame")


def через_калькулятор(бр, порт, ш, ночь, админ=False):
    н = f"[калькулятор {ш} {'ночь' if ночь else 'день'}{' админ' if админ else ''}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900}, color_scheme="dark" if ночь else "light",
                      device_scale_factor=2 if ш == 1440 else 1)
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(ряды(админ), ensure_ascii=False) + ";\n"
        "window.addEventListener('DOMContentLoaded', function () {\n"
        "  window._sbProfile = Object.assign(window._sbProfile || {}, { role: '" + ("admin" if админ else "manager") + "', updates_seen: 'v0.0.0' });\n"
        "});")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("(ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';"
                 " window._sbProfile = Object.assign(window._sbProfile || {}, { role: '" + ("admin" if админ else "manager") + "', updates_seen: 'v0.0.0' });"
                 " try { applyThemeMode(ночь ? 'dark' : 'light', false); } catch (e) {} }", ночь)
    # Первое открытие после загрузки страницы — то, на котором прежде выезжало меню.
    стр.evaluate("() => openManual()")
    кадр = кадр_справки(стр)
    стр.wait_for_timeout(1200)
    р = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
    отметка = стр.evaluate("() => (window._sbProfile || {}).updates_seen")
    ждём = меню_ожидаемое()
    факт(р["глава"] == "ch-home" and р["глав"] == 1 and р["пункт"] == "Главная", f"{н} открылась на оглавлении, в меню «Главная»: {р['глава']}, {р['пункт']!r}")
    факт(not р["меню"], f"{н} меню разделов при первом открытии не выехало: {р['меню']}")
    факт(р["разделы"] == ждём, f"{н} разделы и главы — как в меню: {[(и, len(г)) for и, г in р['разделы']]}")
    факт(not р["безЗначка"] and not р["безОчём"], f"{н} у каждой главы значок и «о чём»: без значка {р['безЗначка']}, без «о чём» {р['безОчём']}")
    в_главах = {г for _, гг in р["разделы"] for г in гг}
    факт(not ({'updates', 'tasks', 'home'} & в_главах) and р["дальше"] == 0, f"{н} журнала, лога и «дальше» в оглавлении нет: {sorted({'updates', 'tasks', 'home'} & в_главах)}, дальше {р['дальше']}")
    ж = р["журнал"] or {}
    факт(ж and р["строка"].startswith("Версия " + (ж.get("вер") or "").lstrip("v")) and str(ж.get("правок")) in р["строка"],
         f"{н} «Что нового» по верхней карточке журнала: {р['строка']!r} / {ж}")
    факт(р["точка"] == "block" and отметка == "v0.0.0", f"{н} точка «есть новое» горит, журнал ещё не засчитан: точка {р['точка']}, отметка {отметка}")
    факт(р["колонок"] == (3 if ш == 1440 else 1), f"{н} колонок оглавления: {р['колонок']}")
    факт(not р["вылез"] and р["вширь"] <= 0 and not р["обрез"], f"{н} ничего не вылезает и не обрезано: {р['вылез']}, вширь {р['вширь']}, {р['обрез']}")
    if р["журналВменю"]:
        факт(р["журналВменю"][0] <= р["журналВменю"][1] + 10, f"{н} «Журнал обновлений» с точкой — в одну строку: {р['журналВменю'][0]} px против {р['журналВменю'][1]} у «Обзора»")
    if ш <= 720:
        факт(р["высота"] >= 44, f"{н} строка главы не ниже 44 px: {р['высота']}")
    стр.screenshot(path=str(СНИМКИ / f"manual-home-{ш}-{'night' if ночь else 'day'}{'-admin' if админ else ''}.png"))
    if not ночь and not админ and р["глава"] != "ch-home":
        факт(False, f"{н} оглавления нет — переходы из него проверить не на чем")
    elif not ночь and not админ:
        # глава из оглавления, «Главная» из меню, «Что нового»
        кадр.locator(".hm-ch[data-go='presets']").click()
        стр.wait_for_timeout(300)
        п = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
        факт(п["глава"] == "ch-presets", f"{н} «Пресеты» из оглавления открылись: {п['глава']}")
        if ш <= 720:
            кадр.locator("body").evaluate("() => toggleMobMenu()")
            стр.wait_for_timeout(300)
        # Справа в строке «Главная» — «Свернуть / Развернуть» (19.10.2026): нажимаем на само слово.
        кадр.locator(".sb-a[onclick=\"go('home')\"]").click(position={"x": 44, "y": 17})
        стр.wait_for_timeout(300)
        п = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
        факт(п["глава"] == "ch-home" and not п["меню"], f"{н} «Главная» в меню вернула оглавление: {п['глава']}, меню {п['меню']}")
        кадр.locator(".hm-news").click()
        стр.wait_for_timeout(700)
        п = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
        отметка = стр.evaluate("() => [(window._sbProfile || {}).updates_seen, appReleaseVersion()]")
        кадр.locator("body").evaluate("() => go('home')")
        стр.wait_for_timeout(200)
        т = кадр.locator("body").evaluate("() => getComputedStyle(document.getElementById('homeDot')).display")
        факт(п["глава"] == "ch-updates" and отметка[0] == отметка[1] and т == "none",
             f"{н} «Что нового» открыла журнал, он засчитан, точка погасла: {п['глава']}, {отметка}, точка {т}")
        # печать
        стр.emulate_media(media="print")
        печать = кадр.locator("body").evaluate("() => getComputedStyle(document.getElementById('ch-home')).display")
        стр.emulate_media(media="screen")
        факт(печать == "none", f"{н} в печати оглавления нет: {печать}")
        # повторное открытие
        стр.evaluate("async () => { closeManual(); await openManual(); }")
        кадр = кадр_справки(стр)
        стр.wait_for_timeout(800)
        п = кадр.locator("body").evaluate("() => (" + СОСТОЯНИЕ + ")()")
        факт(п["глава"] == "ch-home" and not п["меню"], f"{н} повторное открытие — снова оглавление без меню: {п['глава']}, меню {п['меню']}")
    for о in [о for о in ошибки if not any(ш_ in о for ш_ in ШУМ)][:3]:
        факт(False, f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def в_бою(бр, порт, ш):
    """Оболочка в бою: калькулятор с 2.5.17 шлёт data-start="home", а возврат из
    статьи о выпуске — data-start="updates". Обёрток контура у оглавления с
    выпуска нет, и бой обязан видеть его так же, как тест."""
    for старт, ждём in (("home", "ch-home"), ("updates", "ch-updates")):
        н = f"[бой {ш} {старт}]"
        стр = бр.new_page(viewport={"width": ш, "height": 900})
        ошибки = []
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        адрес = f"http://127.0.0.1:{порт}/__manual-probe.html?contour=prod"
        html = справка.достать("manual").replace("<html", f'<html data-start="{старт}"', 1)
        стр.route(адрес, (lambda h: lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=h))(html))
        стр.goto(адрес, wait_until="load")
        стр.wait_for_timeout(500)
        р = стр.evaluate(СОСТОЯНИЕ)
        факт(р["естьДом"] and р["пунктДом"], f"{н} оглавление и пункт «Главная» есть: {р['естьДом']}, {р['пунктДом']}")
        факт(р["глава"] == ждём and р["глав"] == 1, f"{н} справка открылась на {ждём}: {р['глава']}")
        факт(not р["меню"], f"{н} меню разделов не выехало: {р['меню']}")
        for о in ошибки[:3]:
            факт(False, f"{н} ошибка страницы: {о[:160]}")
        стр.close()


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for ночь in (False, True):
                    через_калькулятор(бр, порт, ш, ночь)
                в_бою(бр, порт, ш)
            через_калькулятор(бр, порт, 1440, False, админ=True)
            бр.close()
    finally:
        с.shutdown()
    print("\n".join("    ок  " + т for т in ОТЧЁТ))
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: справка открывается оглавлением без меню, «Что нового» с точкой ведёт в журнал; в бою — "
          "так же. На 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
