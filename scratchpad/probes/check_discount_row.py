#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба строки спец. цены в своде: подпись и процент складываются в сотню.

Константин 19.09.2026: «тут когда скидка 2,4 % — итоговый процент должен быть
97,6 тогда». В строке стояло 98 %: процент считался отдельно от денег и
округлялся до целого, тогда как подпись округлена до десятых. Две цифры в
одной строке жили каждая своей жизнью.

Проба не сверяет числа с написанными в ней самой: она читает из строки её же
подпись и её же процент и складывает их. Так она переживёт смену вида строки
и поймает не опечатку, а расхождение — в том числе там, где скидка задана
суммой и процент получается дробным сам собой.

    python3 check_discount_row.py
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

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

# Проценты, на которых проверяем: целый, с десятой, с сотой (её подпись
# округлит до десятых — процент в строке обязан округлиться так же).
ПРОЦЕНТЫ = [2, 2.4, 2.45, 0.5, 12.7]

ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "Проба 6×4", "name": "Проба 6×4",
        "price_100": 3086292, "price_150": 3500000, "price_200": 3900000,
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


def число(т):
    м = re.search(r"-?\d+(?:[.,]\d+)?", т or "")
    return float(м.group(0).replace(",", ".")) if м else None


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
            стр.evaluate("""async () => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              const и = PROJECTS.findIndex(p => p && p[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
            }""")
            for проц in ПРОЦЕНТЫ:
                м = стр.evaluate("""async (проц) => {
                  const поле = document.getElementById('discountPctInput');
                  поле.value = String(проц);
                  поле.dispatchEvent(new Event('input', { bubbles: true }));
                  calc();
                  await new Promise(r => setTimeout(r, 300));
                  const стр2 = document.querySelector('.bd-discount');
                  if (!стр2) return { нет: true };
                  return {
                    подпись: (стр2.querySelector('.bd-name') || {}).textContent || '',
                    процент: (стр2.querySelector('.bd-pct') || {}).textContent || '',
                  };
                }""", проц)
                if not м or м.get("нет"):
                    плохо = f"при скидке {проц} % строки спец. цены нет в своде"
                    НАХОДКИ.append(плохо)
                    continue
                вПодписи = число(м["подпись"])
                вСтроке = число(м["процент"])
                if вПодписи is None or вСтроке is None:
                    НАХОДКИ.append(f"при скидке {проц} % не разобрать строку: "
                                   f"«{м['подпись'].strip()}» / «{м['процент'].strip()}»")
                    continue
                сумма = abs(вПодписи) + вСтроке
                if abs(сумма - 100) > 0.05:
                    НАХОДКИ.append(
                        f"скидка {проц} %: в подписи −{abs(вПодписи)} %, в строке {вСтроке} % — "
                        f"вместе {round(сумма, 2)} вместо 100")
            # Снимок строки — её и читает человек.
            стр.evaluate("""async () => {
              const п = document.getElementById('discountPctInput');
              п.value = '2.4'; п.dispatchEvent(new Event('input', { bubbles: true }));
              calc();
              await new Promise(r => setTimeout(r, 300));
              const с = document.querySelector('.bd-discount');
              if (с) с.scrollIntoView({ block: 'center' });
            }""")
            стр.wait_for_timeout(400)
            for тема in ('модерн', 'бланк'):
                стр.evaluate("(т) => document.body.classList.toggle('ui-blank', т === 'бланк')", тема)
                стр.wait_for_timeout(250)
                try:
                    стр.locator('.breakdown-wrap, #breakdownCard').first.screenshot(
                        path=str(pathlib.Path(__file__).parent / f"свод-скидка-{тема}.png"), timeout=5000)
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
    print("Чисто: в строке спец. цены подпись и процент складываются в сотню "
          "на всех проверенных скидках, включая дробные.")


if __name__ == "__main__":
    главная()
