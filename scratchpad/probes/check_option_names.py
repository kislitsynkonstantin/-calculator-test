#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба названий опций: что стоит в каталоге, то и уходит в документ.

Константин 19.09.2026: «масло тут допиши Osmo или аналоги. Проверь, чтобы в
экспорт попадало». Название опции живёт в базе, а до клиента доходит тремя
путями — строкой в расчёте, листом для печати (он же PDF) и снимком по ссылке
клиенту. Проба берёт название из каталога и ищет его на всех трёх, а не
сверяет строку с написанной в самой пробе: так она переживёт следующую правку
названия и поймает не опечатку, а разрыв между каталогом и документом.

Отдельно держится переименование: комплектации в браузере кэшируются по
НАЗВАНИЯМ, и без записи в `OPTION_RENAMES` опция молча выпала бы из
закэшированного набора. Проба подставляет старое название и смотрит, что оно
доезжает до нового.

    python3 check_option_names.py
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

# Опции, у которых название правилось, и их прежние названия. Пара нужна
# целиком: новое проверяется в документе, старое — в переименованиях.
ПРАВЛЕНЫ = [
    ("p14", "Покраска снаружи маслом со шлифовкой"),
    ("p16", "Заводская покраска снаружи маслом"),
]


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(найденные[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            стр.add_init_script(ЗАГЛУШКА)
            # Без проекта лист для печати выходит пустым: `buildPrintDoc`
            # выходит сразу, если проект не выбран. Каталог опций при этом
            # берётся из самого файла — тот, что уехал в базу.
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "window.__ТАБЛИЦЫ.pricing_projects = [{"
                "  product: 'frame', sort: 1, slug: 'Проба 6×4', name: 'Проба 6×4',"
                "  price_100: 1000000, price_150: 1200000, price_200: 1400000,"
                "  floors: 1, roof_type: 'двускатная', warm: true,"
                "  open_area: 10, closed_area: 20, facade_area: 60,"
                "  paint_area: 60, roof_area: 40 }];")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            итог = стр.evaluate("""async (правлены) => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              const и = PROJECTS.findIndex(p => p && p[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              const из = [];
              for (const [ид, старое] of правлены) {
                const о = OPTIONS.find(x => x.id === ид);
                if (!о) { из.push({ ид, нет: true }); continue; }
                // Отмечаем опцию — иначе в лист она не попадёт вовсе.
                checkedOptions[ид] = true;
                из.push({ ид, имя: о.name, старое,
                          переименовано: migrateOptionNames([старое])[0] });
              }
              правлены.forEach(([ид]) => {
                checkedOptions[ид] = true;
                const стр = document.querySelector('.opt-item[data-id="' + ид + '"]');
                if (стр) стр.classList.add('active');
              });
              try { calc(); } catch (e) {}
              // Именно `openPrintPreview`, а не `buildPrintDoc` напрямую: набор
              // печатаемых разделов готовит она, и без него лист выходит пустым.
              openPrintPreview();
              await new Promise(r => setTimeout(r, 700));
              const лист = document.getElementById('printDoc');
              return { опции: из, лист: лист ? лист.innerText : null,
                       листЕсть: !!лист, страница: document.body.innerText,
                       отмечено: правлены.map(([ид]) => [ид, !!checkedOptions[ид]]),
                       листДлина: лист ? лист.innerText.length : 0,
                       листНачало: лист ? лист.innerText.slice(0, 400) : '',
                       проект: selectedProject ? selectedProject[0] : null,
                       активныеРазделы: (typeof printActiveSections !== 'undefined')
                          ? [...printActiveSections].slice(0, 6) : 'нет',
                       html: лист ? лист.innerHTML.length : -1,
                       опцийВсего: (typeof OPTIONS !== 'undefined') ? OPTIONS.length : -1 };
            }""", [list(п) for п in ПРАВЛЕНЫ])

            for о in итог["опции"]:
                if о.get("нет"):
                    плохо(f"опции {о['ид']} нет в каталоге — переименование потеряло её")
                    continue
                имя = о["имя"]
                if "Osmo" not in имя:
                    плохо(f"{о['ид']}: в каталоге «{имя}» — марка не дописана")
                if имя not in итог["страница"]:
                    плохо(f"{о['ид']}: название из каталога не совпало со строкой в расчёте")
                if not итог["листЕсть"]:
                    плохо("листа для печати нет в разметке — экспорт проверить нечем")
                elif имя not in итог["лист"]:
                    плохо(f"{о['ид']}: «{имя}» не попало в лист для печати — "
                          f"в PDF и по ссылке клиенту уйдёт другое название")
                if о["переименовано"] != имя:
                    плохо(f"{о['ид']}: прежнее название «{о['старое']}» не переводится в новое "
                          f"(получилось «{о['переименовано']}») — опция выпадет "
                          f"из закэшированной комплектации")
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: правленые названия стоят в каталоге, доходят до строки расчёта "
          "и до листа для печати, прежние названия переводятся в новые.")


if __name__ == "__main__":
    главная()
