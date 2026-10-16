#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цифры итога в печати «Бланк» — шрифтом главного экрана, Unbounded.

Константин 16.10.2026, снимками листа печати и главного экрана: «поставь шрифт
цифр как тут» — итог на экране набран Unbounded, а в печати был Geologica.
Утверждён макет mockups/print-total-font-v1.html: «Супер, делай».

Держит, в печати «Бланк» со спец. ценой за наличные, на 390 и 1440 px:
  • общая стоимость в шапке листа и в полоске итога — Unbounded 800, спец. цена —
    Unbounded 700, как #totalDisplay и спец. цена на главном экране;
  • шрифт на самом деле лёг: ширина суммы в Unbounded отличается от той же
    строки в Geologica (document.fonts.check отвечает «да» и при подмене);
  • общая стоимость в шапке — 18pt (на телефоне 15pt): в 21pt чёрная сумма
    Unbounded давила на шапку («Чёрный кажется слишком большим»);
  • спец. цена в полоске итога — 14pt (на телефоне 11pt): «Это чуть крупнее
    сделай, основная же цена»;
  • знак ₽ в шапке остаётся мелким Geologica — меняются только цифры;
  • полоска итога не вылезает: верхняя строка не шире себя; на 1440 обе колонки
    стоят рядом, лесенкой полоска складывается только на телефоне.

    python3 check_print_total_font.py
"""
import functools, http.server, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
ФИКСТУРА = (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8")
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + ФИКСТУРА + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


ЗАМЕР = """() => { const д = document.getElementById('printDoc');
  const шр = с => { const э = д.querySelector(с); if (!э) return null; const к = getComputedStyle(э);
    const чис = (э.firstChild && э.firstChild.nodeType === 3 ? э.firstChild.textContent : э.textContent).trim();
    const пр = document.createElement('span'); пр.textContent = чис; пр.style.cssText = 'position:absolute;white-space:nowrap;font-size:' + к.fontSize + ';font-weight:' + к.fontWeight + ';letter-spacing:' + к.letterSpacing;
    document.body.appendChild(пр); пр.style.fontFamily = к.fontFamily; const а = пр.getBoundingClientRect().width;
    пр.style.fontFamily = 'Geologica'; const б = пр.getBoundingClientRect().width; пр.remove();
    return { кегль: к.fontSize, семья: к.fontFamily.split(',')[0].replace(/['"]/g, ''), вес: к.fontWeight, разница: Math.round(а - б), чис }; };
  const руб = д.querySelector('.bl-total-v small');
  const пол = д.querySelector('.bl-strip'), верх = д.querySelector('.bl-strip-top');
  return { шапка: шр('.bl-total-v'), спец: шр('.bl-disc-v'), полоса: шр('.bl-strip-v'), полосаСпец: шр('.bl-strip-disc'),
    рубль: руб ? getComputedStyle(руб).fontFamily.split(',')[0].replace(/['"]/g, '') : null,
    вылез: верх ? верх.scrollWidth - верх.clientWidth : null, лесенка: !!пол && пол.classList.contains('is-stack-top') }; }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш, в in ((1440, 1000), (390, 844)):
        стр = бр.new_page(viewport={"width": ш, "height": в})
        ошибки = []
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
        стр.add_init_script(ЗАГЛУШКА)
        стр.add_init_script(ЦЕНЫ)
        стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
        стр.wait_for_timeout(2500)
        стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; selectProjectOption(0); calc();
          const п = document.getElementById('discountPctInput'); п.value = '2.7'; п.dispatchEvent(new Event('input', { bubbles: true }));
          const н = document.getElementById('cashDiscountCheck'); if (!н.checked) н.click(); calc(); }""")
        стр.wait_for_timeout(500)
        стр.evaluate("() => openPrintPreview()")
        стр.wait_for_timeout(1500)
        д = стр.evaluate(ЗАМЕР)
        for имя, ключ, вес in (("общая стоимость в шапке", "шапка", "800"), ("спец. цена в шапке", "спец", "700"),
                               ("общая стоимость в полоске", "полоса", "800"), ("спец. цена в полоске", "полосаСпец", "700")):
            з = д[ключ]
            факт(bool(з) and з["семья"] == "Unbounded" and з["вес"] == вес,
                 f"{ш}: {имя} — Unbounded {вес}: {з and (з['семья'] + ' ' + з['вес'])}")
            факт(bool(з) and abs(з["разница"]) >= 4, f"{ш}: {имя} — шрифт лёг, ширина «{з and з['чис']}» отличается от Geologica на {з and з['разница']} px")
        кегль = {1440: "24px", 390: "20px"}[ш]
        кс = {1440: 18.67, 390: 14.67}[ш]
        з = д["полосаСпец"]
        факт(bool(з) and abs(float(з["кегль"][:-2]) - кс) < 0.1, f"{ш}: спец. цена в полоске — {кс} px (14pt на листе, 11pt на телефоне): {з and з['кегль']}")
        факт(д["шапка"] and д["шапка"]["кегль"] == кегль, f"{ш}: общая стоимость в шапке — {кегль} (18pt на листе, 15pt на телефоне), не крупнее: {д['шапка'] and д['шапка']['кегль']}")
        факт(д["рубль"] == "Geologica", f"{ш}: знак ₽ в шапке — прежний Geologica: {д['рубль']}")
        факт(д["вылез"] is not None and д["вылез"] <= 1, f"{ш}: верхняя строка полоски не вылезает: лишних {д['вылез']} px")
        if ш == 1440:
            факт(not д["лесенка"], f"{ш}: на листе обе колонки полоски рядом, без лесенки")
        факт(not ошибки, f"{ш}: ошибок страницы нет: {ошибки[:2]}")
        стр.close()
    бр.close()
с.shutdown()

print("\n".join("    ок  " + т for т in ОТЧЁТ)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + т for т in НАХОДКИ) if НАХОДКИ else "Чисто: цифры итога в печати — Unbounded, как на главном экране; ₽ прежний, полоска не вылезает.")
raise SystemExit(1 if НАХОДКИ else 0)
