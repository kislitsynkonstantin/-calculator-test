#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба счёта открытий клиентской страницы.

Считается приход по ссылке, а не загрузка страницы. Проба держит ровно это:
  • первое открытие вкладки — свежий приход (p_fresh = true);
  • обновление той же вкладки — не приход (p_fresh = false);
  • возврат во вкладку (visibilitychange) — не приход;
  • новая вкладка — снова свежий приход;
  • предпросмотр менеджера (?preview=1) не отмечается вовсе;
  • вызов уходит на client_link_open и без единого параметра в адресе
    (у PostgREST параметры на /rpc/ — фильтры по столбцам, и «?t=…» давал 400).

Живая база из контейнера закрыта шлюзом, поэтому ответ подменяется: проверяется
то, что отправляет страница, а поведение самой функции — запросом к базе.
"""
import json
import os
import pathlib
import sys
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent.parent
def хром():
    """Путь к браузеру. Номер сборки в нём меняется при обновлении образа,
    поэтому вписанный в пробу он однажды перестал бы совпадать. Значение
    кладёт хук запуска сессии; нет его — находим сами."""
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


ХРОМ = хром()
СТРАНИЦА = (КОРЕНЬ / "404.html").read_text(encoding="utf-8")
КОД = "adkv8q5j"

СНИМОК = {
    "status": "ok",
    "snapshot_at": "2026-09-16T10:00:00+00:00",
    "price_until": "2026-09-30",
    "snapshot": {
        "проект": "Баня 6×4", "разделы": [], "итого": 1200000,
        "шапка": {}, "параметры": [], "снимки": [],
    },
}

НАХОДКИ = []


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def подключить(контекст, порт, журнал):
    def страница(маршрут):
        маршрут.fulfill(status=200, content_type="text/html; charset=utf-8", body=СТРАНИЦА)

    def база(маршрут):
        зпр = маршрут.request
        имя = зпр.url.rsplit("/", 1)[-1]
        адрес, _, хвост = имя.partition("?")
        журнал.append({"имя": адрес, "хвост": хвост,
                       "тело": json.loads(зпр.post_data or "{}")})
        ответ = СНИМОК if адрес == "client_link_get" else {"status": "ok", "new_visit": True}
        маршрут.fulfill(status=200, content_type="application/json", body=json.dumps(ответ))

    контекст.route("**/rest/v1/rpc/**", база)
    контекст.route(f"http://127.0.0.1:{порт}/{КОД}*", страница)


def открытия(журнал):
    return [з for з in журнал if з["имя"] == "client_link_open"]


def главная():
    с, порт = сервер()
    адрес = f"http://127.0.0.1:{порт}/{КОД}"
    журнал = []
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])

        # ── вкладка первая: приход, обновление, возврат ──────────────────────
        к1 = бр.new_context()
        подключить(к1, порт, журнал)
        с1 = к1.new_page()
        с1.goto(адрес, wait_until="load")
        с1.wait_for_timeout(700)
        о = открытия(журнал)
        if len(о) != 1:
            НАХОДКИ.append(f"первое открытие дало {len(о)} отметок вместо одной")
        elif о[0]["тело"].get("p_fresh") is not True:
            НАХОДКИ.append(f"первое открытие отмечено не как приход: {о[0]['тело']}")
        if о and о[0]["хвост"]:
            НАХОДКИ.append(f"в адрес вызова попали параметры «?{о[0]['хвост']}» — PostgREST ответит 400")

        с1.reload(wait_until="load")
        с1.wait_for_timeout(700)
        о = открытия(журнал)
        if len(о) != 2:
            НАХОДКИ.append(f"после обновления отметок {len(о)}, ожидалось 2")
        elif о[1]["тело"].get("p_fresh") is not False:
            НАХОДКИ.append(f"обновление страницы посчитано новым приходом: {о[1]['тело']}")

        # Возврат во вкладку: страница переспрашивает версию и отмечается,
        # но приходом это не считается.
        с1.evaluate("""() => {
          Object.defineProperty(document, 'visibilityState', { get: () => 'visible', configurable: true });
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        с1.wait_for_timeout(700)
        о = открытия(журнал)
        if len(о) < 3:
            НАХОДКИ.append("возврат во вкладку не отметился вовсе — время последнего захода не сдвинется")
        elif о[-1]["тело"].get("p_fresh") is not False:
            НАХОДКИ.append(f"возврат во вкладку посчитан новым приходом: {о[-1]['тело']}")
        к1.close()

        # ── вкладка вторая: снова приход ─────────────────────────────────────
        было = len(открытия(журнал))
        к2 = бр.new_context()
        подключить(к2, порт, журнал)
        с2 = к2.new_page()
        с2.goto(адрес, wait_until="load")
        с2.wait_for_timeout(700)
        о = открытия(журнал)
        if len(о) != было + 1:
            НАХОДКИ.append(f"новая вкладка дала {len(о) - было} отметок вместо одной")
        elif о[-1]["тело"].get("p_fresh") is not True:
            НАХОДКИ.append(f"новая вкладка не посчитана приходом: {о[-1]['тело']}")
        к2.close()

        # ── предпросмотр менеджера не отмечается ─────────────────────────────
        было = len(открытия(журнал))
        к3 = бр.new_context()
        подключить(к3, порт, журнал)
        с3 = к3.new_page()
        с3.goto(адрес + "?preview=1", wait_until="load")
        с3.wait_for_timeout(700)
        if len(открытия(журнал)) != было:
            НАХОДКИ.append("предпросмотр менеджера отметился как открытие клиента")
        к3.close()

        # Прежняя функция больше не зовётся: в базе она осталась только ради
        # боевого домена, и новая страница ходить в неё не должна.
        if any(з["имя"] == "client_link_seen" for з in журнал):
            НАХОДКИ.append("страница всё ещё зовёт client_link_seen вместо client_link_open")

        бр.close()
    с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: приход, обновление, возврат, новая вкладка и предпросмотр —"
          " отмечаются так, как задумано.")
    print("Отметок всего:", len(открытия(журнал)))


if __name__ == "__main__":
    главная()
