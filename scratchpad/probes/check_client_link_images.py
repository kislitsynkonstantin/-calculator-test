#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снятая галочка «Изображения» убирает снимки и из ссылки клиенту.

Константин 22.09.2026, снимком клиентской страницы с четырьмя фотографиями:
«если снята галочка „Изображение“ в разделе параметры в режиме печати и
сохранена ссылка, то фото не должны отображаться по ссылке. Сейчас
отображается». Галочка правила только лист печати, а в снимок для ссылки фото
уходили всё равно — менеджер выключал их перед отправкой и обнаруживал у
клиента.

Проба проходит весь путь, а не проверяет переменную: собирает снимок в
калькуляторе — с включёнными и с выключенными изображениями, — а потом отдаёт
каждый клиентской странице тем же ответом базы, каким она его получает в
работе, и считает картинки в листе.

  • изображения включены — клиент видит обе фотографии;
  • выключены — на клиентской странице их нет вовсе;
  • выключены и включены обратно — снимки возвращаются: выключатель не
    односторонний.

Первая проверка здесь не формальность: без неё вторая проходила бы и на
сломанной сборке, где снимок пуст всегда.

    python3 check_client_link_images.py
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
СТРАНИЦА = (КОРЕНЬ / "404.html").read_text(encoding="utf-8")
КОД = "prbimg01"
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


def снимок_из_калькулятора(бр, порт):
    """Три снимка ссылки подряд: изображения включены, выключены, включены."""
    стр = бр.new_page(viewport={"width": 1440, "height": 950})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)

    # Снимки берутся по http-адресу, а не как data: — в снимок ссылки идут
    # только те, что уже лежат в облаке, и data: отсеялся бы ещё на подходе,
    # а проба мерила бы пустоту в обоих случаях.
    фото = f"http://127.0.0.1:{порт}/assets/logo-bmsk-dark.png"
    итог = стр.evaluate("""async ([фото]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      window._sbProfile = { role: 'admin', full_name: 'Проба' };
      const и = PROJECTS.findIndex(x => x && x[0]);
      selectProjectOption(и >= 0 ? и : 0);
      await new Promise(r => setTimeout(r, 900));
      if (typeof toggleImageCard === 'function' && imageCardCollapsed) toggleImageCard();
      canvasAddImage(фото); canvasAddImage(фото);
      await new Promise(r => setTimeout(r, 500));

      const собрать = () => { buildPrintDoc(); return JSON.parse(JSON.stringify(
        window._снимокКлиента || {})); };
      const включено = собрать();
      // Выключатель трогаем тем же путём, что менеджер, — пунктом
      // «Изображения» в «Параметрах» окна печати.
      togglePrintImages(true);
      const выключено = собрать();
      togglePrintImages(true);
      const обратно = собрать();
      return { включено, выключено, обратно, состояние: printImagesEnabled };
    }""", [фото])
    стр.close()
    return итог, ошибки


def картинок_у_клиента(бр, порт, снимок):
    """Сколько фотографий видно на клиентской странице по этому снимку."""
    ответ = {
        "status": "ok",
        "snapshot_at": "2026-09-22T09:00:00+00:00",
        "price_until": None,
        "snapshot": снимок,
    }
    к = бр.new_context(viewport={"width": 1280, "height": 1000})
    к.route(f"http://127.0.0.1:{порт}/{КОД}*",
            lambda м: м.fulfill(status=200, content_type="text/html; charset=utf-8",
                                body=СТРАНИЦА))
    к.route("**/rest/v1/rpc/**",
            lambda м: м.fulfill(status=200, content_type="application/json",
                                body=json.dumps(ответ if м.request.url.endswith("client_link_get")
                                                else {"status": "ok"})))
    стр = к.new_page()
    стр.goto(f"http://127.0.0.1:{порт}/{КОД}", wait_until="load")
    стр.wait_for_timeout(1500)
    сколько = стр.evaluate("() => document.querySelectorAll('.bl-imgs img').length")
    к.close()
    return сколько


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            снимки, ошибки = снимок_из_калькулятора(бр, порт)
            if ошибки:
                плохо("ошибки страницы калькулятора: " + "; ".join(ошибки)[:200])

            for имя, ожидание in (("включено", "есть"), ("выключено", "нет"),
                                  ("обратно", "есть")):
                с_ = снимки.get(имя) or {}
                в_снимке = len(с_.get("снимки") or [])
                в_раскладке = len(с_.get("раскладка") or [])
                у_клиента = картинок_у_клиента(бр, порт, с_)
                print(f"  {имя}: в снимке {в_снимке}, в раскладке {в_раскладке}, "
                      f"у клиента на странице {у_клиента}")
                if ожидание == "есть" and у_клиента < 2:
                    плохо(f"[{имя}] изображения включены, а клиент видит "
                          f"{у_клиента} фотографии — проверка «выключено» прошла бы "
                          "и на сборке, где снимок пуст всегда")
                if ожидание == "нет" and (у_клиента or в_снимке or в_раскладке):
                    плохо(f"[{имя}] галочка «Изображения» снята, а по ссылке "
                          f"клиент видит {у_клиента} фотографии "
                          f"(в снимке {в_снимке}, в раскладке {в_раскладке})")
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: снятая галочка «Изображения» убирает фотографии и из снимка "
          "ссылки, и с клиентской страницы, а возвращённая — возвращает.")


if __name__ == "__main__":
    главная()
