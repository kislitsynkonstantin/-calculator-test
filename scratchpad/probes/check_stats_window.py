#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба окна аналитики: история берётся за срок, а не последней тысячей.

Константин 19.09.2026: «карта активности не хранит данные больше 2 недель. Тут
выбрано по всем аккаунтам». Данные хранились: в таблице событий лежало пять
месяцев и 2179 записей. Обрезал запрос — `.limit(1000)` при сортировке от
новых к старым. Тысяча свежих событий на пятерых — это пятнадцать дней, а
карта рисует тридцать четыре недели; из 147 сохранённых расчётов в окно
попадало 17.

Проба ставит в заглушку полторы тысячи событий и растягивает их на тринадцать
месяцев — дальше года намеренно, потому что в окне есть вкладка «Всё время»,
и год под ней был бы той же тихой обрезкой. Мерка не в числе строк, а в
глубине: видно ли событие годовой давности. Так она переживёт и смену шага
страницы, и рост числа событий.

Второй прицел — свод по месяцам. 19.09.2026, следом: «и месяц показывает
только последний, хотя период стоит „Все время"». Таблица брала шесть месяцев
`slice(0,6)` и молча отрезала остальное. Проба считает строки свода и сверяет
их с числом месяцев, которые она сама разложила.

Отдельно держится постраничный обход: заглушка режет `range` по-настоящему,
поэтому забытая страница или повтор первой сразу видны по числу.

    python3 check_stats_window.py
"""
import datetime
import re
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
ПОДПИСЬ_КАРТЫ = re.compile(r'Всего за (?:(год)|(\d+) нед\.):\s*(\d+)')

СОБЫТИЙ = 1500          # больше одной страницы
АККАУНТОВ = 5           # события размазаны по пятерым, как в бою
ДНЕЙ = 400              # больше года: годовой порог под «Всё время» — обрезка
СВОИХ = СОБЫТИЙ // АККАУНТОВ   # окно менеджера показывает только его расчёты


def события():
    """Полторы тысячи расчётов, ровно размазанных по сроку.

    Возвращает список и число календарных месяцев, которые он задевает, —
    считать его в уме нельзя: граница месяца ездит вместе с сегодняшним днём.
    """
    из = []
    месяцы = set()
    сейчас = datetime.datetime.now(datetime.timezone.utc)
    for н in range(СОБЫТИЙ):
        дн = (н * ДНЕЙ) / СОБЫТИЙ
        когда = сейчас - datetime.timedelta(days=дн, minutes=н % 60)
        из.append({
            "id": н + 1, "user_id": "u-%d" % (н % АККАУНТОВ), "event_type": "preset_saved",
            "project_name": "Проба", "total_price": 1000000 + н,
            "options_count": 3, "thickness": 150, "discount": 0,
            "cash_discount": False, "checked_options": {},
            "created_at": когда.isoformat().replace("+00:00", "Z"),
            "details": {"obj": "Проба"},
        })
        месяцы.add(когда.strftime("%Y-%m"))
    return из, len(месяцы)


def своих_за_недель(соб, недель):
    """Сколько своих расчётов обязано попасть в окно карты активности.

    Карта кончается текущей неделей и уходит назад на `недель` понедельников,
    поэтому граница считается от понедельника этой недели, а не «сегодня минус
    N дней». День запаса снимается с края: событие, стоящее ровно на границе,
    легко перескакивает её из-за часового пояса, и ожидание должно быть нижней
    границей, а не точным числом.
    """
    сегодня = datetime.datetime.now(datetime.timezone.utc).date()
    понедельник = сегодня - datetime.timedelta(days=сегодня.weekday())
    от = понедельник - datetime.timedelta(days=(недель - 1) * 7 - 1)
    return sum(1 for е in соб
               if е["user_id"] == "u-0"
               and datetime.date.fromisoformat(е["created_at"][:10]) >= от)


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
    СОБ, МЕСЯЦЕВ = события()
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
              try { await openStats(); } catch (e) { return { сбой: String(e) }; }
              // Кадру нужно время: он грузится из srcdoc и рисует по сообщению.
              await new Promise(r => setTimeout(r, 2500));
              const кадр = document.getElementById('statsFrame');
              const д = кадр && кадр.contentDocument;
              if (!д) return { нетКадра: true };
              const строки = [...д.querySelectorAll('#monthlyBody tr')]
                .filter(т => т.children.length > 1);
              const подпись = (д.getElementById('hmStats') || {}).innerText || '';
              return {
                строк: строки.length,
                месяцы: строки.map(т => ((т.children[0] || {}).textContent || '').trim()),
                подписьКарты: подпись.replace(/\\s+/g, ' ').trim(),
              };
            }""")
            if not м:
                НАХОДКИ.append("страница не ответила")
            elif м.get("сбой"):
                НАХОДКИ.append("аналитика не открылась: " + м["сбой"][:120])
            elif м.get("нетКадра"):
                НАХОДКИ.append("кадр аналитики не отдал свой документ — читать нечего")
            elif not м["строк"]:
                НАХОДКИ.append("таблица по месяцам пуста — в окно не доехало ни одного расчёта")
            else:
                # Свод по месяцам ничего не обещает урезать: его подпись —
                # «Расчёты и суммы», а не «топ». Значит строк в нём столько,
                # сколько месяцев в истории.
                if м["строк"] < МЕСЯЦЕВ:
                    НАХОДКИ.append(
                        f"в таблице по месяцам {м['строк']} строк вместо {МЕСЯЦЕВ} — "
                        f"история обрезана: {', '.join(м['месяцы'])}")
                # Карта активности рисует столько недель, сколько влезло в
                # ширину, и сама объявляет своё окно в подписи. Поэтому ожидание
                # считается по объявленному окну, а не по общей стопке: иначе
                # проба ругалась бы на здоровое окно, где старые расчёты честно
                # остались за краем карты. Считаются только свои расчёты —
                # окно менеджера чужих не показывает.
                подпись = м["подписьКарты"]
                разбор = ПОДПИСЬ_КАРТЫ.search(подпись or "")
                if not подпись:
                    НАХОДКИ.append("подпись карты активности пуста — считать нечего")
                elif not разбор:
                    НАХОДКИ.append(
                        f"в подписи карты активности нет счёта: «{подпись[:70]}»")
                else:
                    недель = 54 if разбор.group(1) == "год" else int(разбор.group(2))
                    насчитано = int(разбор.group(3))
                    ожидание = своих_за_недель(СОБ, недель)
                    if насчитано < ожидание:
                        НАХОДКИ.append(
                            f"карта активности за {недель} нед. насчитала {насчитано} "
                            f"расчётов вместо {ожидание} — часть истории до неё не доехала")

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
