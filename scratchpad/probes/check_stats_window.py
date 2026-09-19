#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба окна аналитики: история берётся за срок, а не последней тысячей.

Константин 19.09.2026: «карта активности не хранит данные больше 2 недель. Тут
выбрано по всем аккаунтам». Данные хранились: в таблице событий лежало пять
месяцев и 2179 записей. Обрезал запрос — `.limit(1000)` при сортировке от
новых к старым. Тысяча свежих событий на пятерых — это пятнадцать дней, а
карта рисует тридцать четыре недели; из 147 сохранённых расчётов в окно
попадало 17.

Проба ставит в заглушку полторы тысячи событий за полгода и смотрит, доходят
ли до окна аналитики самые старые. Мерка не в числе строк, а в глубине: что
событие полугодовой давности видно. Так она переживёт и смену шага страницы,
и рост числа событий.

Отдельно держится постраничный обход: заглушка режет `range` по-настоящему,
поэтому забытая страница или повтор первой сразу видны по числу.

    python3 check_stats_window.py
"""
import datetime
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

СОБЫТИЙ = 1500          # больше одной страницы
ДНЕЙ = 180              # полгода


def события():
    из = []
    сейчас = datetime.datetime.now(datetime.timezone.utc)
    for н in range(СОБЫТИЙ):
        дн = (н * ДНЕЙ) / СОБЫТИЙ          # ровно размазаны по полугоду
        когда = сейчас - datetime.timedelta(days=дн, minutes=н % 60)
        из.append({
            "id": н + 1, "user_id": "u-%d" % (н % 5), "event_type": "preset_saved",
            "project_name": "Проба", "total_price": 1000000 + н,
            "options_count": 3, "thickness": 150, "discount": 0,
            "cash_discount": False, "checked_options": {},
            "created_at": когда.isoformat().replace("+00:00", "Z"),
            "details": {"obj": "Проба"},
        })
    return из


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
    СОБ = события()
    ТАБЛИЦЫ = {
        "events": СОБ,
        "profiles": [{"id": "u-0", "role": "admin", "full_name": "Проба",
                      "first_name": "Проба", "last_name": "", "email": "p@p"}],
        "pricing_projects": [], "pricing_matrix": [], "pricing_options": [],
        "pricing_sections": [], "preset_links": [], "presets": [],
    }
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
              _sbUser = { id: 'u-0' };
              window._sbProfile = { id: 'u-0', role: 'admin', full_name: 'Проба' };
              // Перехватываем то, что уходит в окно аналитики.
              window.__ушло = null;
              const кадр = document.getElementById('statsFrame');
              if (!кадр) return { нетКадра: true };
              const прежний = window.postMessage;
              // Сообщение шлют в contentWindow кадра — подменяем его приёмник.
              Object.defineProperty(кадр, 'contentWindow', {
                configurable: true,
                value: { postMessage: (с) => {
                  if (с && с.type === 'events') window.__ушло = с.events;
                } },
              });
              try { await openStats(); } catch (e) { return { сбой: String(e) }; }
              await new Promise(r => setTimeout(r, 1200));
              const е = window.__ушло;
              if (!Array.isArray(е)) return { нетСобытий: true };
              const даты = е.map(x => new Date(x.created_at).getTime());
              const ид = new Set(е.map(x => x.id));
              return {
                сколько: е.length,
                уникальных: ид.size,
                глубинаДней: Math.round((Date.now() - Math.min(...даты)) / 86400000),
              };
            }""")
            if not м:
                НАХОДКИ.append("страница не ответила")
            elif м.get("нетКадра"):
                НАХОДКИ.append("кадра аналитики нет в разметке")
            elif м.get("сбой"):
                НАХОДКИ.append("аналитика не открылась: " + м["сбой"][:120])
            elif м.get("нетСобытий"):
                НАХОДКИ.append("в окно аналитики не ушло ни одного события")
            else:
                # Глубина — главное: событие полугодовой давности обязано дойти.
                if м["глубинаДней"] < ДНЕЙ - 5:
                    НАХОДКИ.append(
                        f"в аналитику ушла история за {м['глубинаДней']} дней вместо {ДНЕЙ} — "
                        f"самое старое событие до окна не доехало "
                        f"({м['сколько']} из {СОБЫТИЙ} записей)")
                if м["сколько"] != СОБЫТИЙ:
                    НАХОДКИ.append(f"в аналитику ушло {м['сколько']} записей из {СОБЫТИЙ} — "
                                   "постраничный обход потерял страницу")
                if м["уникальных"] != м["сколько"]:
                    НАХОДКИ.append(f"среди ушедших записей повторы: {м['сколько']} строк, "
                                   f"{м['уникальных']} разных — страница прочитана дважды")
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print(f"Чисто: в аналитику уходит вся история за срок — {СОБЫТИЙ} записей "
          f"за {ДНЕЙ} дней, без потерь и повторов страниц.")


if __name__ == "__main__":
    главная()
