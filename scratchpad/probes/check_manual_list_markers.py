#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка и статьи о выпусках: точки маркированных списков — тёмным цветом темы.

Константин 17.10.2026, снимком списка из документа с цветными точками: «В базе
знаний и справке в документах, где обычные тут чёрные точки маркированного
списка, поставь тёмные в цвет темы».

Справка открывается так, как её открывает калькулятор, — кадром srcdoc внутри
страницы с адресом теста; статья о выпуске — сама по себе. Днём и ночью мерится
точка списка в главе («Пресеты»), в логе развития и в плашке предупреждения:
  • точка в главе и в логе — цвета темы (оттенок бирюзы), не текста и не
    серая; днём — тёмная бирюза (светлота не больше 30 %), ночью — светлее,
    иначе тёмное на тёмном не видно; контраст с фоном не меньше 3 : 1;
  • в плашке предупреждения точка — цвета её черты: плашка тёплая;
  • в статьях о выпусках то же для точки в тексте статьи.

Двусторонняя: BM_MANUAL_SRC на прежнюю папку справки — проба краснеет.
"""
import colorsys
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


ЗАМЕР = """(выборы) => {
  const к = s => { const м = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?/.exec(s || '');
    if (м) return { c: [+м[1], +м[2], +м[3]], a: м[4] == null ? 1 : +м[4] };
    const с = /color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?/.exec(s || '');
    return с ? { c: [с[1], с[2], с[3]].map(x => Math.round(+x * 255)), a: с[4] == null ? 1 : +с[4] } : null; };
  const фон = э => { for (let у = э; у; у = у.parentElement) { const ц = к(getComputedStyle(у).backgroundColor); if (ц && ц.a > 0.5) return ц.c; }
    return к(getComputedStyle(document.documentElement).backgroundColor).c || [255, 255, 255]; };
  const цвет = (знач, где) => { const и = document.createElement('i'); и.style.color = знач; где.appendChild(и); const ц = к(getComputedStyle(и).color).c; и.remove(); return ц; };
  const р = {};
  for (const [имя, выбор] of Object.entries(выборы)) {
    const л = document.querySelector(выбор);
    р[имя] = л ? { точка: к(getComputedStyle(л, '::marker').color).c, текст: к(getComputedStyle(л).color).c, фон: фон(л),
                   черта: л.closest('.warn') ? цвет('var(--warn-border)', л) : null } : null;
  }
  return р;
}"""


def hls(rgb):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb))
    return h * 360, l, s


def яркость(rgb):
    л = [((x / 255) / 12.92 if x / 255 <= 0.03928 else (((x / 255) + 0.055) / 1.055) ** 2.4) for x in rgb]
    return 0.2126 * л[0] + 0.7152 * л[1] + 0.0722 * л[2]


def контраст(а, б):
    я = sorted([яркость(а), яркость(б)], reverse=True)
    return (я[0] + 0.05) / (я[1] + 0.05)


def оценить(где, ночь, з):
    if not з:
        факт(False, f"{где}: пункта списка нет")
        return
    h, l, s = hls(з["точка"])
    к = контраст(з["точка"], з["фон"])
    тема = 170 <= h <= 200 and s >= 0.25 and з["точка"] != з["текст"]
    тон = l >= 0.4 if ночь else l <= 0.30
    факт(тема and тон and к >= 3,
         f"{где}: точка {з['точка']} — оттенок {h:.0f}°, светлота {l:.2f}, контраст {к:.2f} с фоном {з['фон']}; текст {з['текст']}")


def родитель(html):
    return ("<!doctype html><meta charset=utf-8><body style='margin:0'>"
            "<iframe id=f style='width:1200px;height:900px;border:0'></iframe><script>"
            "document.getElementById('f').srcdoc=" + json.dumps(html).replace("</", "<\\/") + ";</script>")


ВЫБОРЫ = {"глава": "#ch-presets ul li", "лог": "#ch-tasks .tsk ul li", "плашка": "#ch-tasks .warn ul li"}

with sync_playwright() as p:
    б = p.chromium.launch(executable_path=хром())
    адрес = "https://test.calculator.baniamsk.ru/"
    for ночь in (False, True):
        стр = б.new_page(viewport={"width": 1280, "height": 900})
        ошибки = []
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.route(адрес, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=родитель(справка.достать())))
        стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        стр.goto(адрес, wait_until="load")
        стр.wait_for_function("() => { const f = document.getElementById('f'); return f && f.contentWindow && typeof f.contentWindow.doSearch === 'function'; }")
        кадр = стр.frames[1]
        if ночь:
            кадр.evaluate("() => { document.body.classList.remove('light'); document.body.classList.add('dark'); }")
        з = кадр.evaluate(ЗАМЕР, ВЫБОРЫ)
        режим = "ночь" if ночь else "день"
        оценить(f"справка, {режим}, глава", ночь, з["глава"])
        оценить(f"справка, {режим}, лог развития", ночь, з["лог"])
        пл = з["плашка"]
        факт(bool(пл) and пл["точка"] == пл["черта"], f"справка, {режим}, плашка предупреждения: точка {пл and пл['точка']} цвета черты {пл and пл['черта']}")
        факт(not ошибки, f"справка, {режим}: ошибок скрипта нет {ошибки[:2]}")
        стр.close()
    for ч in [ч for ч in справка.части("release")]:
        for ночь in (False, True):
            стр = б.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark" if ночь else "light")
            стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            стр.route("**/*.png", lambda r: r.abort())
            стр.set_content(ч["html"], wait_until="domcontentloaded")
            з = стр.evaluate(ЗАМЕР, {"статья": ".main ul li"})
            if з["статья"] is None:
                стр.close()
                continue
            оценить(f"статья {ч['part']}, {'ночь' if ночь else 'день'}", ночь, з["статья"])
            стр.close()
    б.close()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: точки списков в справке и статьях о выпусках — тёмная бирюза днём, светлая ночью; в плашке предупреждения — цвета черты.")
