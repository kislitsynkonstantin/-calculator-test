#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Строка комплектации в боковой панели: появляется, гаснет и не врёт.

Константин 20.09.2026, двумя снимками: «если выбрана комплектация, в боковом
меню добавляй строчку с её названием».

Строка называет набор, по которому собран расчёт, — значит, ошибиться она
может дорого: назвать «Комфорт» там, где менеджер уже снял половину позиций,
и показать клиенту набор, которого в смете нет. Поэтому проба смотрит не на
появление строки, а на три вещи разом:

  • комплектацию применили — строка появилась и назвала ту же, что отметка
    над итогом в расчёте;
  • в расчёте тронули позицию — отметка погасла, и строка погасла вместе с
    ней, а не осталась висеть;
  • комплектации нет — строки нет вовсе, а не пустой промежуток в шапке.

Отдельно меряется место: строка стоит между надзаголовком и названием
проекта, не липнет к соседям и не висит в пустоте.

    python3 check_sidenav_kit.py
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
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

ТАБЛИЦЫ_JS = (
    "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};"
    "window.__ТАБЛИЦЫ.pricing_projects = [1,2].map(и => ({"
    "  product: 'frame', sort: и, slug: 'Проба ' + и, name: 'Проба ' + и,"
    "  price_100: 1000000, price_150: 1200000, price_200: 1400000,"
    "  floors: 1, roof_type: 'двускатная', warm: true,"
    "  open_area: 10, closed_area: 20, facade_area: 60,"
    "  paint_area: 60, roof_area: 40 }));")


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


ВИД = """() => {
  const с = document.getElementById('snHeadKit');
  const отметка = document.getElementById('kitBadge');
  const надзаг = document.querySelector('.sn-head .sn-h-k');
  const имя = document.getElementById('snHeadName');
  const видна = с ? getComputedStyle(с).display !== 'none' : null;
  const к = с ? с.getBoundingClientRect() : null;
  let сверху = null, снизу = null;
  if (к && надзаг && имя) {
    сверху = к.top - надзаг.getBoundingClientRect().bottom;
    снизу = имя.getBoundingClientRect().top - к.bottom;
  }
  return {
    естьВРазметке: !!с,
    видна,
    текст: с ? (с.textContent || '').trim() : null,
    отметка: отметка && отметка.style.display !== 'none'
      ? (отметка.textContent || '').trim() : null,
    доНадзаголовка: сверху, доИмени: снизу,
    подНадзаголовком: (к && надзаг) ? к.top >= надзаг.getBoundingClientRect().bottom - 1 : null,
    надИменем: (к && имя) ? к.bottom <= имя.getBoundingClientRect().top + 1 : null,
  };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)

            стр.evaluate("""async () => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              // Шапка панели — только «Бланк»: в «Модерне» она скрыта стилями,
              // и мерить в нём нечего.
              document.body.classList.add('ui-blank');
              const и = PROJECTS.findIndex(x => x && x[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 1000));
              if (typeof openSideNav === 'function') openSideNav();
              await new Promise(r => setTimeout(r, 500));
            }""")

            # ── 1. Комплектации нет — строки нет ──
            в1 = стр.evaluate(ВИД)
            if not в1["естьВРазметке"]:
                плохо("строки комплектации нет в разметке панели вовсе")
                raise SystemExit(печать())
            if в1["видна"]:
                плохо("комплектация не выбрана, а строка в панели видна — "
                      f"в ней «{в1['текст']}»")

            # ── 2. Применили комплектацию ──
            применили = стр.evaluate("""async () => {
              // Отметку ставит сам калькулятор, когда набор применён. Здесь
              // зовём его же путь, а не рисуем отметку руками: проба должна
              // мерить то, что случится у менеджера.
              if (typeof showKitBadge !== 'function') return false;
              showKitBadge('Комфорт');
              await new Promise(r => setTimeout(r, 400));
              return true;
            }""")
            if not применили:
                плохо("отметку комплектации поставить нечем — showKitBadge нет")
            в2 = стр.evaluate(ВИД)
            if not в2["видна"]:
                плохо("комплектацию применили, а строки в панели не появилось")
            elif "Комфорт" not in (в2["текст"] or ""):
                плохо(f"строка в панели говорит «{в2['текст']}» — "
                      "названия комплектации в ней нет")
            if в2["отметка"] and в2["текст"] and в2["отметка"] != в2["текст"]:
                плохо(f"панель и расчёт называют комплектацию по-разному: "
                      f"«{в2['текст']}» против «{в2['отметка']}»")
            if в2["подНадзаголовком"] is False:
                плохо("строка комплектации встала выше надзаголовка «Спецификация»")
            if в2["надИменем"] is False:
                плохо("строка комплектации встала ниже названия проекта — "
                      "просили строкой над ним")
            for подпись, d in (("надзаголовка", в2["доНадзаголовка"]),
                               ("названия проекта", в2["доИмени"])):
                if d is None:
                    continue
                if d < 2:
                    плохо(f"строка комплектации приклеена к {подпись}: {round(d)} px")
                if d > 26:
                    плохо(f"строка комплектации висит в пустоте: до {подпись} "
                          f"{round(d)} px")

            # ── 3. Тронули расчёт — отметка гаснет, строка обязана погаснуть ──
            стр.evaluate("""async () => {
              showKitBadge(null);      // так калькулятор гасит отметку сам
              await new Promise(r => setTimeout(r, 400));
            }""")
            в3 = стр.evaluate(ВИД)
            if в3["видна"]:
                плохо(f"отметка комплектации погасла, а строка в панели осталась: "
                      f"«{в3['текст']}» — панель называет набор, которого в "
                      "расчёте уже нет")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    печать()


def печать():
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: строка комплектации появляется вместе с отметкой в расчёте, "
          "называет ту же комплектацию, стоит между надзаголовком и проектом "
          "и гаснет вместе с отметкой.")


if __name__ == "__main__":
    главная()
