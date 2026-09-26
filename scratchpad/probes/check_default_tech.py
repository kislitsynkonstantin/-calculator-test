#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба цвета примечаний в настройках.

Часть про «Технологию по умолчанию» снята 26.09.2026 вместе со строкой в
настройках: технология запоминается выбором в поле «Технология», её держит
check_tech_remembered.py.

Константин 19.09.2026: «салатовый убери из цветов подсветки примечаний» и
«добавь в настройки „Технология по умолчанию" (Каркас/Клеёный брус). Хранится
пусть в аккаунте, между устройствами».

Цвет:
  • салатового (#f0f4ee) среди кружков нет;
  • у кого он был выбран — переводится на мятный, иначе подпись показывала бы
    «—», ни один кружок не был бы отмечен, а примечания красились цветом,
    которого в списке уже нет.

Технология:
  • строка есть, кнопки две, выбранная отмечена;
  • выбор ложится в `appSettings` — а этот объект целиком уезжает в
    `profiles.app_settings`, поэтому настройка и есть аккаунтная;
  • выбор в настройках технологию сейчас же не переключает: человек пришёл в
    настройки, а не считать, и переключение стёрло бы его расчёт;
  • при старте настройка применяется, но только если расчёт ещё не начат —
    профиль приезжает с задержкой, и переключение поверх начатой работы её бы
    стёрло;
  • брус не открыт — строки нет вовсе и настройка из аккаунта заслон не обходит.

    python3 check_default_tech.py
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
САЛАТОВЫЙ = "#f0f4ee"

ТАБЛИЦЫ = {
    # Проектов два нарочно. С одним калькулятор выбирает его сам («Auto-select
    # if exactly one result»), и «пустой расчёт» в пробе оказывался начатым —
    # проверка того, что настройка срабатывает на пустом, мерила бы вхолостую.
    "pricing_projects": [{
        "product": "frame", "sort": и, "slug": "Проба %d×4" % (5 + и),
        "name": "Проба %d×4" % (5 + и),
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    } for и in (1, 2)],
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


def страница(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""() => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
    }""")
    return стр


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = страница(бр, порт)

            # ── цвет примечаний ──
            цв = стр.evaluate("""async (салатовый) => {
              appSettings.noteHighlightColor = салатовый;
              openSettings();
              await new Promise(r => setTimeout(r, 500));
              const тело = document.getElementById('settingsBody');
              const кружки = [...тело.querySelectorAll('.st-swatch')]
                .map(э => (э.getAttribute('style') || '').match(/background:\\s*([^;]+)/));
              return {
                цвета: кружки.map(м => м ? м[1].trim() : ''),
                текущий: appSettings.noteHighlightColor,
                отмечено: тело.querySelectorAll('.st-swatch.on').length,
              };
            }""", САЛАТОВЫЙ)
            if not цв:
                НАХОДКИ.append("настройки не открылись")
            else:
                if any(САЛАТОВЫЙ in ц for ц in цв["цвета"]):
                    НАХОДКИ.append("салатовый остался среди кружков подсветки")
                if цв["текущий"].lower() == САЛАТОВЫЙ:
                    НАХОДКИ.append("выбранный салатовый не переведён на другой цвет — "
                                   "подпись покажет «—», и ни один кружок не отмечен")
                if цв["отмечено"] != 1:
                    НАХОДКИ.append(f"отмеченных кружков {цв['отмечено']}, а должен быть один")

            # Технологии по умолчанию в настройках больше нет (26.09.2026):
            # технология запоминается выбором в поле — см. check_tech_remembered.py.
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: салатового в подсветке нет, выбранный салатовый переведён на другой цвет.")


if __name__ == "__main__":
    главная()
