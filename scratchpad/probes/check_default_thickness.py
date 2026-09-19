#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба толщины утепления: 150 мм всегда, настройки на это нет.

Константин 19.09.2026: «эту настройку убери. Просто по умолчанию поставь
150 мм утеплитель в каркасе».

Держатся три вещи:
  • в «Настройках» нет ни строки «Утепление по умолчанию», ни кнопок 100/150/
    200 — настройка снята целиком, а не спрятана;
  • новый расчёт открывается на 150 мм, и активна средняя кнопка толщины;
  • «Сбросить всё» возвращает 150 мм, даже если до того стояло 200.

Проверяется отрисовка: толщина читается из активной кнопки, как её видит
человек, а не из переменной — переменная может разойтись с тем, что нарисовано.

    python3 check_default_thickness.py
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

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "Проба 6×4", "name": "Проба 6×4",
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)

            м = стр.evaluate("""async () => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              const и = PROJECTS.findIndex(p => p && p[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              const активная = () => {
                const к = [...document.querySelectorAll('.thick-btn')].find(б => б.classList.contains('active'));
                return к ? к.textContent.replace(/\\s+/g, ' ').trim() : null;
              };
              const приСтарте = активная();
              // Ставим 200 и сбрасываем: настройки на толщину нет, значит
              // «Сбросить всё» обязан вернуть именно 150.
              setThickness(2);
              await new Promise(r => setTimeout(r, 300));
              const послеПеревода = активная();
              resetEverything();
              await new Promise(r => setTimeout(r, 500));
              const послеСброса = активная();
              // Настройки: строки про утепление нет вовсе.
              openSettings();
              await new Promise(r => setTimeout(r, 500));
              const тело = document.getElementById('settingsBody');
              const текст = тело ? тело.innerText : '';
              const кнопки = тело
                ? [...тело.querySelectorAll('.st-theme-btn')].map(б => б.textContent.trim())
                : [];
              return { приСтарте, послеПеревода, послеСброса, текст,
                       кнопкиНастроек: кнопки,
                       ключ: (typeof appSettings === 'object' && appSettings)
                         ? ('defaultThickness' in appSettings) : null };
            }""")
            if not м:
                НАХОДКИ.append("страница не ответила")
            else:
                if м["приСтарте"] != "150 мм":
                    НАХОДКИ.append(f"новый расчёт открылся на «{м['приСтарте']}», а не на 150 мм")
                if м["послеПеревода"] != "200 мм":
                    НАХОДКИ.append(f"переключение на 200 мм не сработало: «{м['послеПеревода']}» — "
                                   "проверять сброс не на чем")
                if м["послеСброса"] != "150 мм":
                    НАХОДКИ.append(f"после «Сбросить всё» толщина «{м['послеСброса']}», а не 150 мм")
                if "Утепление по умолчанию" in (м["текст"] or ""):
                    НАХОДКИ.append("в настройках осталась строка «Утепление по умолчанию»")
                лишние = [к for к in м["кнопкиНастроек"] if "мм" in к]
                if лишние:
                    НАХОДКИ.append(f"в настройках остались кнопки толщины: {', '.join(лишние)}")
                if м["ключ"]:
                    НАХОДКИ.append("ключ defaultThickness остался в настройках — "
                                   "он ничего не делал и до того, но хранится и сбивает с толку")
            for тема in ('модерн', 'бланк'):
                стр.evaluate("(т) => document.body.classList.toggle('ui-blank', т === 'бланк')", тема)
                стр.wait_for_timeout(250)
                стр.evaluate("""() => {
                  const т = [...document.querySelectorAll('#settingsBody .st-section-title')]
                    .find(э => /Калькулятор/i.test(э.textContent));
                  if (т) т.scrollIntoView({ block: 'start' });
                }""")
                стр.wait_for_timeout(300)
                try:
                    стр.locator('#settingsBody').screenshot(
                        path=str(pathlib.Path(__file__).parent / f"настройки-{тема}.png"), timeout=5000)
                except Exception as e:
                    print('снимок', тема, 'не вышел:', str(e).split(chr(10))[0][:80])

            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: расчёт открывается на 150 мм, «Сбросить всё» возвращает 150 мм, "
          "настройки утепления в окне нет.")


if __name__ == "__main__":
    главная()
