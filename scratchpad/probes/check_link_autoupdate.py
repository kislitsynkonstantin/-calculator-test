#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Автообновление ссылки срабатывает на любую правку расчёта.

Константин 22.09.2026, снимком меню «Параметры»: «автообновление ссылки не
работает. Либо большой интервал обновления. Надо, чтобы после каждого действия
обновлялась ссылка сама, если стоит эта галочка».

Оно и правда не работало почти нигде: вызов стоял только в `пометитьПравку`,
через которую проходят звёздочка, подарок и подсветка, — а галочка опции,
проект, толщина и скидка идут через `calc()`, и там его не было. Вторая
причина тише: `снимокРазошёлся` сравнивает с `window._снимокКлиента`, который
пересобирает сборка документа печати, — при закрытом окне печати сравнение
отвечало «ничего не изменилось» на любую правку.

Проба меряет запись в базу, а не намерение: заглушка `client_links`
по-настоящему принимает `update`, и проба смотрит, поменялась ли строка.

  • галочка стоит, отметили опцию — строка ссылки обновилась, и снимок в ней
    тот же, что на листе;
  • галочка стоит, окно печати закрыто — обновление всё равно приходит;
  • галочка снята — та же правка строку не трогает.

Последняя проверка здесь не формальность: без неё проба прошла бы и на сборке,
где ссылка переписывается на каждое движение мыши.

    python3 check_link_autoupdate.py
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
ЖДЁМ = 2500        # мс: столько проба даёт автообновлению на срабатывание

# Цены берём из общей выдумки проб: без них опции идут «по запросу» и не
# отмечаются вовсе — правку, на которую должна отозваться ссылка, сделать
# было бы нечем.
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");")


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


СОСТОЯНИЕ = """() => {
  const с = (window.__ТАБЛИЦЫ.client_links || []).find(с => с.code === 'adkv8q5j') || {};
  // Снимок листа пересобираем перед сравнением: при закрытом окне печати он
  // иначе остался бы тем, что был до правки, и «разошлось» отвечало бы нет
  // в обоих случаях — проверка прошла бы вхолостую.
  try { снимокДляСсылки(); } catch (e) {}
  return {
    когда: с.snapshot_at || '',
    полейВСнимке: Object.keys(с.snapshot || {}).length,
    // Сравнение — то же самое, которым страница решает, звать ли «Обновить».
    разошлось: (typeof снимокРазошёлся === 'function')
      ? снимокРазошёлся(_ссылкаКлиента) : null,
  };
}"""

# Правка, идущая через calc(): отмечаем первую доступную опцию расчёта — тот
# самый путь, которым менеджер меняет смету.
ПРАВКА = """() => {
  const о = OPTIONS.find(o => o && o.id && document.getElementById('chk_' + o.id)
                              && document.getElementById('lbl_' + o.id)
                              && !checkedOptions[o.id]);
  if (!о) return null;
  toggleOpt(о.id);
  return о.id;
}"""


def подготовить(стр, порт, авто):
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async ([авто]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      window._sbProfile = { role: 'admin', full_name: 'Проба' };
      const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
      selectProjectOption(и >= 0 ? и : 0);
      await new Promise(r => setTimeout(r, 900));
      // Ссылка в заглушке выдана на пресет «7» — открываем его же, иначе
      // страница ищет ссылку чужого расчёта и не находит ничего.
      activePresetId = '7';
      appSettings.autoUpdateClientLink = авто;
      await загрузитьСсылкуКлиента();
      await new Promise(r => setTimeout(r, 300));
    }""", [авто])


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

            for имя, авто in (("галочка стоит", True), ("галочка снята", False)):
                стр = бр.new_page(viewport={"width": 1440, "height": 950})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                подготовить(стр, порт, авто)

                нашлась = стр.evaluate("() => !!_ссылкаКлиента")
                if not нашлась:
                    плохо(f"[{имя}] ссылка расчёта не нашлась — обновлять нечего, "
                          "проверка прошла бы вхолостую")
                    стр.close()
                    continue

                было = стр.evaluate(СОСТОЯНИЕ)
                опция = стр.evaluate(ПРАВКА)
                if not опция:
                    плохо(f"[{имя}] в расчёте не нашлось опции, которую можно "
                          "отметить, — правку делать нечем")
                    стр.close()
                    continue
                стр.wait_for_timeout(ЖДЁМ)
                стало = стр.evaluate(СОСТОЯНИЕ)

                обновилось = стало["когда"] != было["когда"]
                print(f"  {имя}: правка «{опция}» · строка ссылки "
                      + ("обновилась" if обновилось else "не менялась")
                      + f" · полей в снимке {стало['полейВСнимке']}"
                      + f" · расчёт разошёлся со ссылкой: "
                      + ("да" if стало["разошлось"] else "нет"))

                if авто and not обновилось:
                    плохо(f"[{имя}] после правки расчёта ссылка не обновилась за "
                          f"{ЖДЁМ} мс — менеджер отправит клиенту прежнюю смету")
                if авто and обновилось and стало["разошлось"]:
                    плохо(f"[{имя}] ссылка обновилась, но несёт не то, что на "
                          "листе: сравнение снимков говорит «разошлось»")
                if авто and стало["полейВСнимке"] < 10:
                    плохо(f"[{имя}] в ссылку ушёл пустой снимок "
                          f"({стало['полейВСнимке']} полей) — клиент увидит "
                          "голый лист")
                if not авто and обновилось:
                    плохо(f"[{имя}] галочка снята, а ссылка обновилась сама — "
                          "клиент увидит правку, которую ему не отправляли")
                if not авто and not стало["разошлось"]:
                    плохо(f"[{имя}] правка не изменила снимок расчёта — обновлять "
                          "было нечего, и проверка «галочка стоит» прошла бы "
                          "вхолостую")

                if ошибки:
                    плохо(f"[{имя}] ошибки страницы: " + "; ".join(ошибки)[:200])
                стр.close()

            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: при стоящей галочке ссылка догоняет расчёт сама и несёт ровно "
          "то, что на листе; при снятой — не трогается, и расчёт честно "
          "расходится с отправленным.")


if __name__ == "__main__":
    главная()
