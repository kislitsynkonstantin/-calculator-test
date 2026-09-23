#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Хвост длинного набора опций в журнале раскрывается нажатием.

Константин 23.09.2026, со снимком строки «Набор опций изменён»: «в журнале
когда опции не входят — „ещё“ по нажатию должно раскрывать список. Каким бы
он ни был».

Дефект был не в отрисовке, а в записи: `al2Списком` обрезала набор двенадцатью
именами и дописывала строку «и ещё N» прямо в значение. В базе оставались
двенадцать названий, остальные не сохранялись вовсе — раскрывать было неоткуда,
сколько ни нажимай. Поэтому первый берег пробы меряет запись, а не вид: проба,
которая смотрела бы только на кнопку, прошла бы на сборке, где кнопка есть, а
за ней пусто.

Берега:

  • запись: двадцать опций уходят в журнал двадцатью именами, без «и ещё»;
  • вид: показана дюжина, хвост скрыт, под списком кнопка «и ещё 8»;
  • нажатие: список раскрылся целиком, подпись стала «свернуть»,
    второе нажатие свернуло обратно;
  • палец: нажатие в 16 px над и под серединой подписи ловит её же —
    и при этом сама подпись осталась строчного веса (не выше 24 px);
  • зазор: кнопка не приклеена к последнему названию (не меньше 4 px);
  • старая запись (в значении уже лежит «и ещё 1»): кнопки нет — за ней
    ничего не лежит, и обещать список нельзя;
  • короткий набор в три имени: ни кнопки, ни скрытых пунктов.

    python3 check_log_more.py
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
ПОКАЗ = 12        # столько имён видно до нажатия
ПАЛЕЦ = 16        # px над и под серединой подписи
ВЕС = 24          # px: выше — подпись стала кнопкой-пятном
ЗАЗОР = 4         # px до последнего названия

ДЛИННЫЙ = "\n".join(f"Позиция набора № {i:02d}" for i in range(1, 21))
СТАРЫЙ = "\n".join([f"Старое название № {i:02d}" for i in range(1, 13)] + ["и ещё 1"])
КОРОТКИЙ = "\n".join(["Отливы на цоколь (металл)", "Подсветка полков стандарт",
                      "Портал для печи из камня"])

СОБЫТИЯ = [
    # 1. Новая запись с длинным набором — её и раскрываем.
    {"id": 1, "user_id": "u-проба", "event_type": "options_batch",
     "project_name": "Каркасная баня с террасой 15.5 × 4.8", "total_price": 6694122,
     "options_count": 20, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T09:51:00Z",
     "details": {"obj": "Каркасная баня с террасой 15.5 × 4.8",
                 "rows": [{"k": "Добавлены", "a": "", "b": ДЛИННЫЙ},
                          {"k": "Итог", "a": "5 587 994 ₽", "b": "6 694 122 ₽"}]}},
    # 2. Запись до правки: «и ещё 1» лежит в самом значении.
    {"id": 2, "user_id": "u-проба", "event_type": "options_batch",
     "project_name": "Фахверковая баня «Берлин» 9×5", "total_price": 5100000,
     "options_count": 13, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T09:40:00Z",
     "details": {"obj": "Фахверковая баня «Берлин» 9×5",
                 "rows": [{"k": "Добавлены", "a": "", "b": СТАРЫЙ}]}},
    # 3. Короткий набор — кнопке взяться неоткуда.
    {"id": 3, "user_id": "u-проба", "event_type": "options_batch",
     "project_name": "Баня из бруса «Тула» 6×4", "total_price": 2100000,
     "options_count": 3, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T09:30:00Z",
     "details": {"obj": "Баня из бруса «Тула» 6×4",
                 "rows": [{"k": "Добавлены", "a": "", "b": КОРОТКИЙ}]}},
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


# Все строки журнала раскрываем сразу: подробности нужны целиком.
РАСКРЫТЬ = """() => {
  document.querySelectorAll('#alFeed .al-row').forEach(с => с.classList.add('open'));
}"""

ВИД = """([палец]) => {
  const ряды = [...document.querySelectorAll('#alFeed .al-row')];
  const списки = ряды.map(р => {
    const с = р.querySelector('.al-dlist');
    if (!с) return null;
    const пункты = [...с.querySelectorAll('li')].filter(л => !л.classList.contains('al-dmore'));
    const видно = пункты.filter(л => л.getBoundingClientRect().height > 0);
    const кн = с.querySelector('.al-dmore-btn');
    const к = кн ? кн.getBoundingClientRect() : null;
    let ловит = null, зазор = null;
    if (к) {
      const x = к.left + к.width / 2, y = к.top + к.height / 2;
      ловит = [[x, y - палец], [x, y + палец]].map(([тx, тy]) => {
        const э = document.elementFromPoint(тx, тy);
        return !!(э && э.closest && э.closest('.al-dmore-btn'));
      });
      const последний = видно[видно.length - 1];
      if (последний) зазор = Math.round(к.top - последний.getBoundingClientRect().bottom);
    }
    return {
      проект: (р.querySelector('.al-obj') || {}).textContent || '',
      всего: пункты.length, видно: видно.length,
      кнопка: !!кн, подпись: кн ? кн.textContent.trim() : null,
      ширина: к ? Math.round(к.width) : null,
      высота: к ? Math.round(к.height) : null,
      середина: к ? [Math.round(к.left + к.width / 2), Math.round(к.top + к.height / 2)] : null,
      ловит, зазор,
    };
  }).filter(Boolean);
  return списки;
}"""

ЗАПИСЬ = """() => {
  // Берег записи: двадцать опций должны уйти в журнал двадцатью именами.
  const н = new Set(); for (let i = 1; i <= 20; i++) н.add('проба-' + i);
  const т = al2Списком(н);
  const части = t => String(t).split('\\n').filter(Boolean);
  return { строк: части(т).length,
           хвост: /и ещё \\d+/.test(т),
           предел: typeof AL_ПОКАЗ_СПИСКА === 'number' ? AL_ПОКАЗ_СПИСКА : null };
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

                    # ── берег записи ──
                    з = стр.evaluate(ЗАПИСЬ)
                    if з["строк"] != 20 or з["хвост"]:
                        плохо(f"[{где}] в журнал ушло {з['строк']} имён из двадцати"
                              + (" и строка «и ещё N» в самом значении" if з["хвост"] else "")
                              + " — отрезанные названия не сохраняются, "
                                "раскрывать будет нечего")
                    if з["предел"] != ПОКАЗ:
                        плохо(f"[{где}] предел показа в коде {з['предел']}, "
                              f"проба ждёт {ПОКАЗ}")

                    стр.evaluate(РАСКРЫТЬ)
                    стр.wait_for_timeout(200)
                    списки = стр.evaluate(ВИД, [ПАЛЕЦ])
                    if len(списки) != 3:
                        плохо(f"[{где}] списков в журнале {len(списки)} вместо трёх — "
                              "проба идёт вхолостую")
                        стр.close()
                        continue
                    длинный, старый, короткий = списки

                    # ── вид длинного набора ──
                    if длинный["всего"] != 20 or длинный["видно"] != ПОКАЗ:
                        плохо(f"[{где}] длинный набор: пунктов {длинный['всего']}, "
                              f"видно {длинный['видно']} — ждали 20 и {ПОКАЗ}")
                    if not длинный["кнопка"]:
                        плохо(f"[{где}] у набора из двадцати имён нет кнопки хвоста")
                    elif длинный["подпись"] != f"и ещё {20 - ПОКАЗ}":
                        плохо(f"[{где}] подпись кнопки «{длинный['подпись']}» "
                              f"вместо «и ещё {20 - ПОКАЗ}»")

                    if длинный["кнопка"]:
                        промахи = [с_ for с_, п in zip(("сверху", "снизу"),
                                                       длинный["ловит"]) if not п]
                        if промахи:
                            плохо(f"[{где}] в {ПАЛЕЦ} px от подписи нажатие мимо "
                                  f"({', '.join(промахи)}) — поля вокруг неё нет")
                        if (длинный["высота"] or 0) > ВЕС:
                            плохо(f"[{где}] подпись выросла до {длинный['высота']} px — "
                                  "палец оплачен весом, а не невидимым полем")
                        if длинный["зазор"] is not None and длинный["зазор"] < ЗАЗОР:
                            плохо(f"[{где}] между кнопкой и последним названием "
                                  f"{длинный['зазор']} px — приклеена")

                        # ── нажатие раскрывает и сворачивает ──
                        x, y = длинный["середина"]
                        стр.mouse.click(x, y)
                        стр.wait_for_timeout(250)
                        после = стр.evaluate(ВИД, [ПАЛЕЦ])[0]
                        if после["видно"] != 20:
                            плохо(f"[{где}] после нажатия видно {после['видно']} "
                                  "имён из двадцати — хвост не раскрылся")
                        if после["подпись"] == длинный["подпись"]:
                            плохо(f"[{где}] подпись после раскрытия осталась "
                                  f"«{после['подпись']}» — свернуть обратно нечем")
                        x2, y2 = после["середина"]
                        стр.mouse.click(x2, y2)
                        стр.wait_for_timeout(250)
                        свернули = стр.evaluate(ВИД, [ПАЛЕЦ])[0]
                        if свернули["видно"] != ПОКАЗ:
                            плохо(f"[{где}] второе нажатие не свернуло список: "
                                  f"видно {свернули['видно']}")
                        print(f"  {где}: {длинный['всего']} имён, "
                              f"видно {длинный['видно']}, подпись "
                              f"«{длинный['подпись']}» → «{после['подпись']}», "
                              f"зазор {длинный['зазор']} px")

                    # ── старая запись и короткий набор ──
                    if старый["кнопка"]:
                        плохо(f"[{где}] у старой записи («и ещё 1» лежит в значении) "
                              "нарисована кнопка — за ней ничего нет")
                    if старый["видно"] != старый["всего"]:
                        плохо(f"[{где}] старая запись показана не целиком: "
                              f"{старый['видно']} из {старый['всего']}")
                    if короткий["кнопка"] or короткий["видно"] != короткий["всего"]:
                        плохо(f"[{где}] короткий набор из {короткий['всего']} имён "
                              "показан не целиком или получил кнопку хвоста")

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
    print("Чисто: имена уходят в журнал все, показана дюжина, хвост раскрывается "
          "и сворачивается нажатием, палец его ловит, а у старых записей и "
          "коротких наборов кнопки нет.")


if __name__ == "__main__":
    главная()
