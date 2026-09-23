#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Строку журнала действий раскрывает птичка, и мимо неё трудно попасть.

Константин 23.09.2026: «раскрытие позиции сделать по птичке (и чуть область
расширить вокруг неё, на ширину пальца, чтобы не промазать)». Раньше нажатие
ловила вся строка: её задевали, выделяя сумму или копируя код, и подробности
открывались сами.

Проба меряет то, что происходит от нажатия, и то, куда на самом деле попадает
палец, — не разметку:

  • нажали по тексту строки — подробности не раскрылись;
  • нажали по птичке — раскрылись, нажали ещё раз — закрылись;
  • площадь нажатия вокруг птички не меньше 40 px: проба тычет в четыре
    точки в 18 px от её середины и смотрит, кто ловит нажатие;
  • сама птичка осталась мелкой: нарисованная коробка не больше 20 px —
    требование к пальцу оплачивается невидимым полем, а не весом значка;
  • у события без подробностей кнопки нет вовсе.

Последняя проверка и проверка веса держат друг друга: без первой проба
прошла бы на сборке, где кнопка стоит везде, без второй — на сборке, где
птичку раздули до пальца.

    python3 check_log_chevron.py
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
ПАЛЕЦ = 18        # px от середины птички, куда проба тычет: половина пальца
ВЕС = 20          # px: больше — значок стал пятном в строке

СОБЫТИЯ = [
    # С подробностями — эту строку можно раскрыть.
    {"id": 1, "user_id": "u-проба", "event_type": "options_batch",
     "project_name": "Фахверковая баня «Берлин» 9×5", "total_price": 6747501,
     "options_count": 12, "thickness": 150, "discount": 3, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T08:35:00Z",
     "details": {"obj": "Фахверковая баня «Берлин» 9×5",
                 "preset": "Фахверковая баня «Берлин» 9×5 · 03.09.26",
                 "presetCode": "901974",
                 "rows": [{"k": "Добавлены", "a": "", "b": "Отливы на цоколь (металл)"},
                          {"k": "Итог", "a": "3 086 292 ₽", "b": "6 813 238 ₽"}]}},
    # Без подробностей — раскрывать нечего, птички быть не должно.
    {"id": 2, "user_id": "u-проба", "event_type": "print",
     "project_name": "Фахверковая баня «Магдебург» 6×6", "total_price": 4241082,
     "options_count": 8, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T08:37:00Z",
     "details": {"obj": "Фахверковая баня «Магдебург» 6×6", "rows": []}},
]

ТАБЛИЦЫ = {
    "events": СОБЫТИЯ,
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
    "preset_links": [], "presets": [],
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "Проба 6×4", "name": "Проба 6×4",
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
}


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


ВИД = """([палец]) => {
  const строки = [...document.querySelectorAll('#alFeed .al-row')];
  const сПодробностями = строки.filter(с => с.querySelector('.al-more'));
  const первая = сПодробностями[0] || null;
  if (!первая) return { строк: строки.length, есть: false };
  const кн = первая.querySelector('.al-chev-btn');
  const текст = первая.querySelector('.al-text');
  const к = кн ? кн.getBoundingClientRect() : null;
  // Куда попадает палец в 18 px от середины значка — по четырём сторонам.
  const ловит = [];
  if (к) {
    const x = к.left + к.width / 2, y = к.top + к.height / 2;
    [[x - палец, y], [x + палец, y], [x, y - палец], [x, y + палец]]
      .forEach(([тx, тy]) => {
        const э = document.elementFromPoint(тx, тy);
        ловит.push(!!(э && э.closest && э.closest('.al-chev-btn')));
      });
  }
  return {
    строк: строки.length, есть: true,
    кнопок: document.querySelectorAll('#alFeed .al-chev-btn').length,
    строкСПодробностями: сПодробностями.length,
    открыта: первая.classList.contains('open'),
    ширина: к ? Math.round(к.width) : null,
    высота: к ? Math.round(к.height) : null,
    ловит,
    текстСередина: текст ? [Math.round(текст.getBoundingClientRect().left + 20),
                           Math.round(текст.getBoundingClientRect().top
                                      + текст.getBoundingClientRect().height / 2)] : null,
    птичкаСередина: к ? [Math.round(к.left + к.width / 2), Math.round(к.top + к.height / 2)] : null,
  };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for тема in ("Модерн", "Бланк"):
                for имя, ш, в in (("телефон", 390, 900), ("монитор", 1440, 950)):
                    где = f"{тема} · {имя} {ш}px"
                    стр = бр.new_page(viewport={"width": ш, "height": в})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(
                        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                        "Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate("""async ([бланк]) => {
                      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                      _sbProfile = { role: 'admin', full_name: 'Проба' };
                      document.body.classList.toggle('ui-blank', бланк);
                      openActionLog();
                      await loadActionLog(true);
                      await new Promise(r => setTimeout(r, 600));
                    }""", [тема == "Бланк"])

                    в0 = стр.evaluate(ВИД, [ПАЛЕЦ])
                    if not в0.get("есть"):
                        плохо(f"[{где}] в журнале нет строки с подробностями — "
                              "раскрывать нечего, проверка прошла бы вхолостую")
                        стр.close()
                        continue
                    if в0["кнопок"] != в0["строкСПодробностями"]:
                        плохо(f"[{где}] птичек {в0['кнопок']} на "
                              f"{в0['строкСПодробностями']} раскрываемых строк — "
                              "у события без подробностей кнопки быть не должно")

                    # ── нажатие по тексту строки ничего не раскрывает ──
                    x, y = в0["текстСередина"]
                    стр.mouse.click(x, y)
                    стр.wait_for_timeout(250)
                    после_текста = стр.evaluate(ВИД, [ПАЛЕЦ])
                    if после_текста["открыта"]:
                        плохо(f"[{где}] нажатие по тексту строки раскрыло "
                              "подробности — раскрывать должна только птичка")

                    # ── нажатие по птичке раскрывает и закрывает ──
                    x, y = в0["птичкаСередина"]
                    стр.mouse.click(x, y)
                    стр.wait_for_timeout(250)
                    после_птички = стр.evaluate(ВИД, [ПАЛЕЦ])
                    if not после_птички["открыта"]:
                        плохо(f"[{где}] нажатие по птичке не раскрыло подробности")
                    стр.mouse.click(x, y)
                    стр.wait_for_timeout(250)
                    если_закрыли = стр.evaluate(ВИД, [ПАЛЕЦ])
                    if если_закрыли["открыта"]:
                        плохо(f"[{где}] второе нажатие по птичке не закрыло строку")

                    промахи = [с_ for с_, попал in
                               zip(("слева", "справа", "сверху", "снизу"), в0["ловит"])
                               if not попал]
                    print(f"  {где}: птичка {в0['ширина']}×{в0['высота']} px, "
                          f"палец в {ПАЛЕЦ} px попадает "
                          + ("со всех сторон" if not промахи
                             else "мимо " + ", ".join(промахи)))
                    if промахи:
                        плохо(f"[{где}] в {ПАЛЕЦ} px от птички нажатие уже мимо "
                              f"({', '.join(промахи)}) — площадь не расширена")
                    if (в0["ширина"] or 0) > ВЕС or (в0["высота"] or 0) > ВЕС:
                        плохо(f"[{где}] сама птичка выросла до "
                              f"{в0['ширина']}×{в0['высота']} px — требование к "
                              "пальцу оплачено весом значка, а не невидимым полем")

                    if ошибки:
                        плохо(f"[{где}] ошибки страницы: " + "; ".join(ошибки)[:200])
                    стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: раскрывает только птичка, палец ловится в 18 px от неё со всех "
          "сторон, сам значок остался мелким, а у события без подробностей "
          "кнопки нет.")


if __name__ == "__main__":
    главная()
