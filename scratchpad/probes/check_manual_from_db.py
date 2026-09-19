#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба справки, приходящей из базы.

19.09.2026 справка уехала из `index.html` в таблицу `app_docs`: 475 КБ текста
лежали строкой base64 в открытом репозитории и отдавались всякому, кто знал
адрес страницы. Переключение это проверить нечем: домен базы закрыт шлюзом
наружу, а глазами открыть окно справки на тесте — значит поверить, что оно
соберётся и у менеджера, и у администратора, и во второй раз.

Проба подставляет строки `app_docs` в заглушку базы и смотрит на кадр:

  • справка запрашивается сама, ещё до нажатия — окно открывается собранным,
    а не с подписью «загружается»;
  • у менеджера главы «Лог развития» нет вовсе, и пункта меню на неё тоже:
    правило держит база, но пункт остаётся в оболочке и обязан быть убран;
  • у администратора глава и пункт на месте;
  • второе открытие обходится без запроса — документ лежит в памяти;
  • когда база молчит, в окне стоит внятная строка, а не пустая белизна:
    молчаливо пустое окно — худший исход, ради которого проба и написана.

    python3 check_manual_from_db.py
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent.parent
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


ХРОМ = хром()


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def строки(роль):
    """То, что вернёт база этой роли. Строки со `staff_only` приходят только
    администратору — это правило RLS, и заглушка его повторяет: не прячет
    главу в браузере, а не отдаёт её вовсе."""
    все = справка.части("manual")
    видно = [ч for ч in все if роль == "admin" or not ч["staff_only"]]
    return [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"],
             "staff_only": ч["staff_only"], "html": ч["html"]} for ч in видно]


# Вход доходит до конца только с каталогом цен: без него `loadPricing` бросает
# «база вернула пустой ответ», ветка входа обрывается досрочно, и до строки с
# предзагрузкой справки дело не доходит вовсе. Проба проверяет именно эту
# строку, поэтому каталог ей нужен — хватает одного проекта.
ЦЕНЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "проба", "name": "Проба 6×4",
        "price_100": 100000, "price_150": 150000, "price_200": 200000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [],
    "pricing_options": [],
    "pricing_sections": [],
}

# Шум среды: наружу закрыт шлюз, каталога цен в пробе почти нет. К справке это
# отношения не имеет, и мешать находкам не должно.
ШУМ = ("favicon", "jsdelivr", "supabase.co", "ERR_TUNNEL_CONNECTION_FAILED",
       "ERR_CERT_AUTHORITY_INVALID", "ERR_NAME_NOT_RESOLVED", "[цены]")


def плохо(где, текст):
    НАХОДКИ.append(f"[{где}] {текст}")


def открыть(стр, порт, роль, ряды):
    """Страница с подставленной базой и ролью, доведённая до входа."""
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(ряды, ensure_ascii=False) + ";\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ЦЕНЫ, ensure_ascii=False) + ");\n"
        # Роль читается из профиля: по ней калькулятор говорит справке, оставлять
        # ли пункт «Лог развития» в меню.
        "window.addEventListener('DOMContentLoaded', function () {\n"
        "  window._sbProfile = { role: " + json.dumps(роль) + " };\n"
        "});")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""() => {
      const беда = document.getElementById('pricingErrorScreen');
      if (беда) беда.style.display = 'none';
    }""")


def кадр(стр):
    return стр.frame_locator("#manualFrame")


def дождаться_глав(стр, сколько_ждать=6000):
    шаг, ждём = 200, 0
    while ждём < сколько_ждать:
        if кадр(стр).locator(".ch").count():
            return True
        стр.wait_for_timeout(шаг)
        ждём += шаг
    return False


def проверить_роль(бр, порт, роль, имя):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.on("console", lambda с: ошибки.append(с.text) if с.type == "error" else None)
    ряды = строки(роль)
    открыть(стр, порт, роль, ряды)

    # ── справка спрошена заранее, до всякого нажатия ─────────────────────────
    заранее = стр.evaluate("() => !!_справка")
    if not заранее:
        плохо(имя, "справка не запрошена после входа — окно откроется пустым "
                   "и будет собираться на глазах")

    стр.evaluate("() => openManual()")
    if not дождаться_глав(стр):
        плохо(имя, "окно справки открылось, но глав в нём нет")
        стр.close()
        return

    # Сверяем не числа, а имена: в окне обязаны стоять ровно те главы, что
    # отдала база. Лишняя строка в ответе так не теряется — оболочка убирает
    # «Лог развития» и в браузере, и по одному счёту это выглядело бы нормой.
    в_окне = set(кадр(стр).locator(".ch").evaluate_all(
        "узлы => узлы.map(у => у.id.replace(/^ch-/, ''))"))
    глав = len(в_окне)
    отдано = {р["part"].replace("ch-", "") for р in ряды if р["part"] != "shell"}
    пропало = отдано - в_окне
    лишнее = в_окне - отдано
    if пропало == {"tasks"} and роль != "admin":
        плохо(имя, "база отдала менеджеру внутреннюю главу «Лог развития» — "
                   "в браузере её убрала оболочка, но приходить она не должна вовсе")
    elif пропало:
        плохо(имя, f"база отдала главы, которых в окне нет: {', '.join(sorted(пропало))}")
    if лишнее:
        плохо(имя, f"в окне есть главы, которых база не отдавала: {', '.join(sorted(лишнее))}")

    есть_лог = кадр(стр).locator("#ch-tasks").count()
    есть_пункт = кадр(стр).locator("#sbTasks").count()
    if роль == "admin":
        if not есть_лог:
            плохо(имя, "у администратора нет главы «Лог развития»")
        if not есть_пункт:
            плохо(имя, "у администратора нет пункта меню «Лог развития»")
    else:
        if есть_лог:
            плохо(имя, "менеджеру пришла внутренняя глава «Лог развития»")
        if есть_пункт:
            плохо(имя, "у менеджера в меню остался пункт «Лог развития» — "
                       "пункт ведёт в никуда и обещает то, чего нет")

    # ── второе открытие: документ лежит в памяти ─────────────────────────────
    # База «пустеет» между открытиями: если запрос уйдёт снова, справка придёт
    # без глав, и это будет видно.
    стр.evaluate("() => { closeManual(); window.__ТАБЛИЦЫ.app_docs = []; }")
    стр.wait_for_timeout(200)
    стр.evaluate("() => openManual()")
    стр.wait_for_timeout(600)
    если_снова = кадр(стр).locator(".ch").count()
    if если_снова != глав:
        плохо(имя, f"второе открытие собрало {если_снова} глав вместо {глав} — "
                   "документ спрашивается у базы каждый раз")

    куда = pathlib.Path(__file__).parent
    for ширина in (390, 1440):
        стр.set_viewport_size({"width": ширина, "height": 900})
        стр.wait_for_timeout(300)
        стр.screenshot(path=str(куда / f"справка-из-базы-{имя}-{ширина}.png"))

    важные = [о for о in ошибки if not any(ш in о for ш in ШУМ)]
    for о in важные[:3]:
        плохо(имя, f"ошибка страницы: {о[:160]}")
    стр.close()


def проверить_молчание(бр, порт):
    """База молчит — в окне обязана стоять строка, а не пустая белизна."""
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    открыть(стр, порт, "manager", [])
    стр.evaluate("() => openManual()")
    стр.wait_for_timeout(1200)
    текст = (кадр(стр).locator("body").inner_text() or "").strip()
    if not текст:
        плохо("молчание базы", "окно справки пустое — человек не знает, "
                               "сломалось у него или у нас")
    elif "не удалось" not in текст.lower():
        плохо("молчание базы", f"в окне стоит не то: «{текст[:80]}»")
    стр.screenshot(path=str(pathlib.Path(__file__).parent / "справка-из-базы-молчание.png"))
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
            проверить_роль(бр, порт, "manager", "менеджер")
            проверить_роль(бр, порт, "admin", "администратор")
            проверить_молчание(бр, порт)
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: справка приходит из базы, у менеджера без внутренней главы, "
          "второе открытие без запроса, молчание базы объяснено словами.")


if __name__ == "__main__":
    главная()
