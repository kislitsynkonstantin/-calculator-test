#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба клиентского листа: он ровно тот же, что уходит в PDF у менеджера.

Держит то, что задано 16.09.2026: ни срока цены отдельным блоком, ни строки
версии с именем менеджера — лист кончается оговоркой, как на бумаге.

И то, из-за чего этот блок вообще появлялся: дата, до которой держится цена,
не должна пропасть вместе с ним. Она стоит в блоке общей стоимости и в полоске
итога — проба меряет её там, а не верит на слово.
"""
import json
import pathlib
import sys
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent.parent
ХРОМ = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
СТРАНИЦА = (КОРЕНЬ / "404.html").read_text(encoding="utf-8")
КОД = "adkv8q5j"
СРОК = "15.09.2026"

СНИМОК = {
    "status": "ok",
    "snapshot_at": "2026-09-16T10:00:00+00:00",
    "price_until": "2026-09-15",
    "snapshot": {
        "проект": "Фахверковая баня «Берлин» 9×5",
        "менеджер": "Ефремов Артём",
        "подрядчик": "ООО «ПСК Вега»",
        "подпись": "Баранов Г.Н.",
        "заказчикФИО": "Иванов И. С.",
        "договор": "5997878", "дата": "05.09.2026",
        "итог": 4021637, "доСкидки": 4103711, "скидка": 2, "наличные": True, "выгода": 82074,
        "база": 2943019, "опции": 1160692, "позиций": 56,
        "разделы": [
            {"имя": "Внешняя отделка", "сумма": 486300,
             "позиции": [{"т": "Планкен из сосны 20×140, сорт АВ", "ц": 486300},
                         {"т": "Пропитка планкена в два слоя"}],
             "примечания": ["Цвет пропитки согласуется до начала работ"]},
            {"имя": "Инженерные коммуникации",
             "позиции": [{"т": "Консультация по инженерным коммуникациям"}]}],
    },
}

НАХОДКИ = []
ОКНА = [("телефон", 390, 844), ("стол", 1280, 900)]


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def главная():
    с, порт = сервер()
    адрес = f"http://127.0.0.1:{порт}/{КОД}"
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
        к = бр.new_context()
        к.route(f"http://127.0.0.1:{порт}/{КОД}*",
                lambda м: м.fulfill(status=200, content_type="text/html; charset=utf-8",
                                    body=СТРАНИЦА))
        к.route("**/rest/v1/rpc/**",
                lambda м: м.fulfill(status=200, content_type="application/json",
                                    body=json.dumps(СНИМОК if м.request.url.endswith("client_link_get")
                                                    else {"status": "ok"})))
        стр = к.new_page()
        for окно, ш, в in ОКНА:
            стр.set_viewport_size({"width": ш, "height": в})
            стр.goto(адрес, wait_until="load")
            стр.wait_for_timeout(800)
            д = стр.evaluate("""() => {
              const лист = document.querySelector('.bl-doc');
              const хвост = лист ? лист.lastElementChild : null;
              return {
                естьЛист: !!лист,
                срокБлоком: !!document.querySelector('.bl-till'),
                строкаВерсии: !!document.querySelector('.bl-ver'),
                хвост: хвост ? хвост.className : null,
                текст: лист ? лист.textContent : '',
              };
            }""")
            if not д["естьЛист"]:
                НАХОДКИ.append(f"[{окно}] лист не отрисовался вовсе")
                continue
            if д["срокБлоком"]:
                НАХОДКИ.append(f"[{окно}] на листе остался блок «Цена действует до…»")
            if д["строкаВерсии"]:
                НАХОДКИ.append(f"[{окно}] на листе осталась строка версии с именем менеджера")
            if д["хвост"] != "bl-foot":
                НАХОДКИ.append(f"[{окно}] лист кончается не оговоркой, а «{д['хвост']}»")
            for слово in ("подготовил", "Вопросы по спецификации", "Цена действует до"):
                if слово in д["текст"]:
                    НАХОДКИ.append(f"[{окно}] на листе осталось «{слово}»")
            # Дата цены обязана остаться там, где она стоит и у менеджера, —
            # в строке спец. цены под итогом и в полоске. Это и есть причина,
            # по которой убранный блок не был потерей.
            if д["текст"].count(СРОК) < 2:
                НАХОДКИ.append(f"[{окно}] дата, до которой держится цена ({СРОК}), "
                               f"встречается на листе {д['текст'].count(СРОК)} раз — "
                               "ожидались итог и полоска")
            стр.screenshot(path=str(pathlib.Path(__file__).parent / f"лист-{окно}.png"),
                           full_page=False)
        бр.close()
    с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: лист кончается оговоркой, срок цены на месте в итоге.")


if __name__ == "__main__":
    главная()
