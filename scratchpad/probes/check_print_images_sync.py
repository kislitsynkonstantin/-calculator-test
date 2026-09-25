#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимки в документе: один выключатель, два места, и они не расходятся.

Константин 20.09.2026: «кнопку отображения изображений в режиме печати
зазеркаль в Параметры в режиме печати… Чтобы синхронно было: убрали в печати,
в калькуляторе тоже поменялось и наоборот».

Два вида одного состояния расходятся тихо: подпись правят в одном месте, а
галочку в другом забывают, и менеджер видит «вкл» на кнопке при пустом
документе. Поэтому проба меряет не переменную, а то, что видно:

  • нажали кнопку в карточке — галочка в «Параметрах» переехала следом;
  • нажали пункт в «Параметрах» — подпись на кнопке переехала следом;
  • снимки уходят из документа и возвращаются в него — по обоим путям;
  • окно печати, открытое после правки, показывает галочку по состоянию,
    а не по разметке;
  • снимков нет — пункта в меню нет: выключатель, которому нечего
    выключать, читается как поломка.

    python3 check_print_images_sync.py
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

# Однопиксельный png — снимок, которого хватает, чтобы документ его показал.
КАРТИНКА = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
            "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


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


# Что видно на экране, а не что лежит в переменной. В листе считаем только
# свои снимки: там есть и логотип, и он в документе всегда — подсчёт всех
# картинок подряд никогда не давал бы нуля, и проверка была бы вечно зелёной.
ФОТО = "?stored-photo"
ВИД = """(картинка) => {
  const ФОТО_В_ХРАНИЛИЩЕ = '?stored-photo';
  const кн = document.getElementById('btnTogglePrintImages');
  const гл = document.getElementById('printParamsImagesCheck');
  const пункт = document.getElementById('printParamsImagesItem');
  const лист = document.getElementById('printDoc');
  return {
    подпись: кн ? (кн.textContent || '').trim() : null,
    тусклая: кн ? (getComputedStyle(кн).opacity !== '1') : null,
    галочка: гл ? getComputedStyle(гл).opacity === '1' : null,
    пунктВиден: пункт ? getComputedStyle(пункт).display !== 'none' : null,
    снимковВЛисте: лист ? [...лист.querySelectorAll('img')]\n        .filter(и => и.getAttribute('src') === картинка || (и.getAttribute('src') || '').endsWith(ФОТО_В_ХРАНИЛИЩЕ)).length : null,
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
            # Снимки уходят в хранилище, как только расчёт сохранён пресетом, а
            # с (34) это случается уже при открытии окна печати. Заглушка отдаёт
            # за них адрес логотипа — того самого, что в листе всегда, — и счёт
            # по адресу их бы не нашёл. Здесь у них свой адрес, опознаваемый.
            стр.add_init_script("""(function () { const с = window.supabase.createClient;
              window.supabase.createClient = function () { const к = с.apply(this, arguments); const хр = к.storage.from;
                к.storage.from = function () { const о = хр.apply(this, arguments);
                  о.getPublicUrl = () => ({ data: { publicUrl: '/assets/logo-bmsk-dark.png' + ФОТО_В_ХРАНИЛИЩЕ } });
                  return о; }; return к; }; })();""".replace("ФОТО_В_ХРАНИЛИЩЕ", json.dumps(ФОТО)))
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)

            стр.evaluate("""async (картинка) => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              const и = PROJECTS.findIndex(x => x && x[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              // Снимки добавляются тем же путём, каким их кладёт менеджер, —
              // иначе проба проверяла бы выдуманное состояние, а не то, из
              // которого документ на самом деле собирает лист.
              if (typeof toggleImageCard === 'function' && imageCardCollapsed) toggleImageCard();
              canvasAddImage(картинка);
              canvasAddImage(картинка);
              await new Promise(r => setTimeout(r, 400));
            }""", КАРТИНКА)

            есть = стр.evaluate("() => !!document.getElementById('printParamsImagesItem')")
            if not есть:
                плохо("пункта «Изображения» в «Параметрах» нет вовсе — зеркалить нечего")

            открыть = """async () => {
              openPrintPreview();
              await new Promise(r => setTimeout(r, 800));
              const м = document.getElementById('printParamsDropMenu');
              if (м) м.style.display = 'block';
            }"""
            закрыть = """async () => {
              closePrintPreview();
              await new Promise(r => setTimeout(r, 300));
            }"""

            # ── 1. Окно печати, открытое сразу: всё включено ──
            стр.evaluate(открыть)
            в1 = стр.evaluate(ВИД, КАРТИНКА)
            if not в1["галочка"]:
                плохо("при включённых снимках галочка «Изображения» не стоит")
            if "вкл" not in (в1["подпись"] or ""):
                плохо(f"кнопка в карточке говорит «{в1['подпись']}» "
                      "при включённых снимках")
            if not в1["снимковВЛисте"]:
                плохо("снимки включены, а в листе для печати их нет — "
                      "мерить синхронность нечем")

            # ── 2. Нажали пункт в меню — кнопка в карточке переехала ──
            стр.evaluate("() => togglePrintImages(true)")
            стр.wait_for_timeout(600)
            в2 = стр.evaluate(ВИД, КАРТИНКА)
            if в2["галочка"]:
                плохо("сняли галочку в «Параметрах», а она осталась стоять")
            if "выкл" not in (в2["подпись"] or ""):
                плохо(f"сняли галочку в «Параметрах», а кнопка в карточке "
                      f"по-прежнему говорит «{в2['подпись']}» — виды разошлись")
            if not в2["тусклая"]:
                плохо("снимки выключены, а кнопка в карточке горит как включённая")
            if в2["снимковВЛисте"]:
                плохо(f"снимки выключены, а в листе их {в2['снимковВЛисте']} — "
                      "документ не перестроился")

            # ── 3. Вернули пунктом же — обратный ход ──
            стр.evaluate("() => togglePrintImages(true)")
            стр.wait_for_timeout(600)
            в3 = стр.evaluate(ВИД, КАРТИНКА)
            if not в3["галочка"] or "вкл" not in (в3["подпись"] or ""):
                плохо("обратное нажатие в «Параметрах» не вернуло ни галочку, "
                      "ни подпись на кнопке")
            if not в3["снимковВЛисте"]:
                плохо("снимки включили обратно, а в лист они не вернулись")

            # ── 4. Нажали кнопку в карточке при открытом окне ──
            стр.evaluate("() => { const к = document.getElementById('btnTogglePrintImages');"
                         " if (к) к.click(); }")
            стр.wait_for_timeout(600)
            в4 = стр.evaluate(ВИД, КАРТИНКА)
            if в4["галочка"]:
                плохо("нажали кнопку в карточке, а галочка в «Параметрах» "
                      "осталась стоять — зеркало работает в одну сторону")
            if в4["снимковВЛисте"]:
                плохо("нажали кнопку в карточке при открытом окне печати, "
                      "а снимки из листа не ушли")

            # ── 5. Закрыли и открыли заново: галочка по состоянию ──
            стр.evaluate(закрыть)
            стр.evaluate(открыть)
            в5 = стр.evaluate(ВИД, КАРТИНКА)
            if в5["галочка"]:
                плохо("окно печати открыли заново, и галочка «Изображения» "
                      "встала по разметке, а не по состоянию")
            if в5["снимковВЛисте"]:
                плохо("окно открыли заново, и снимки вернулись в лист сами")

            # Вернуть включённым, чтобы следующая проверка шла с чистого листа.
            стр.evaluate("() => { const к = document.getElementById('btnTogglePrintImages');"
                         " if (к) к.click(); }")
            стр.wait_for_timeout(400)

            # ── 6. Снимков нет — пункта нет ──
            стр.evaluate(закрыть)
            стр.evaluate("""async () => {
              if (typeof canvasClearAll === 'function') canvasClearAll();
              const х = document.getElementById('imageCanvas');
              if (х) х.querySelectorAll('.canvas-img-item').forEach(э => э.remove());
              await new Promise(r => setTimeout(r, 250));
            }""")
            стр.evaluate(открыть)
            в6 = стр.evaluate(ВИД, КАРТИНКА)
            if в6["пунктВиден"]:
                плохо("снимков нет, а пункт «Изображения» в меню остался — "
                      "выключатель, которому нечего выключать")
            стр.evaluate(закрыть)

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: кнопка в карточке и пункт «Изображения» в «Параметрах» — "
          "один выключатель: любое нажатие переставляет оба вида и сами "
          "снимки в листе, а пустая карточка пункта не показывает.")


if __name__ == "__main__":
    главная()
