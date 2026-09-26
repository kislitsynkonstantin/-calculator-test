#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий: скидка пишется одной строкой на правку, а не на шаг стрелки.

Константин 26.09.2026, снимком журнала на телефоне: «почему в журнале скидка по
0,5 % отображается?» Стрелка у поля процента шагает по 0,5 %, браузер шлёт
`change` на каждое её нажатие, и от 0 до 5 % выходило десять строк.

Проба держит:
  • десять шагов стрелкой и уход из поля — одно событие «0 % → 5 %»;
  • вверх и обратно вниз — ни одного события;
  • набор числа руками и уход — одно событие;
  • ввод суммой скидки и уход — одно событие;
  • шаги стрелкой без ухода из поля — одно событие по паузе (ждём 31 с).

    python3 check_discount_log.py
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
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(ДАННЫЕ, events=[], profiles=[{"id": "u-проба", "role": "admin",
                                                               "first_name": "Проба", "last_name": ""}]),
                           ensure_ascii=False) + ");")
НАХОДКИ = []


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


ШАГИ = """async () => {
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  window._sbProfile = { role: 'admin', full_name: 'Проба' };
  selectProjectOption(0);
  await new Promise(r => setTimeout(r, 800));
  const пауза = (мс) => new Promise(r => setTimeout(r, мс || 250));
  const скидки = () => (window.__ТАБЛИЦЫ.events || []).filter(с => с.event_type === 'discount_changed');
  const п = document.getElementById('discountPctInput');
  const шаг = (вверх) => { вверх ? п.stepUp() : п.stepDown();
    п.dispatchEvent(new Event('input', { bubbles: true }));
    п.dispatchEvent(new Event('change', { bubbles: true })); };
  const строка = (с) => { const р = ((с || {}).details || {}).rows || [];
    const к = р.find(х => х.k === 'Скидка'); return к ? к.a + ' → ' + к.b : null; };
  const вышло = {};
  let было = скидки().length;

  // 1. десять шагов стрелкой, уход из поля
  п.focus(); for (let и = 0; и < 10; и++) { шаг(true); await пауза(30); }
  п.blur(); await пауза();
  вышло.стрелка = { n: скидки().length - было, s: строка(скидки().slice(-1)[0]) };
  было = скидки().length;

  // 2. вверх и обратно
  п.focus(); шаг(true); шаг(true); шаг(false); шаг(false); п.blur(); await пауза();
  вышло.туда_обратно = скидки().length - было;
  было = скидки().length;

  // 3. набор руками
  п.focus(); п.value = '7'; п.dispatchEvent(new Event('input', { bubbles: true }));
  п.dispatchEvent(new Event('change', { bubbles: true })); п.blur(); await пауза();
  вышло.руками = { n: скидки().length - было, s: строка(скидки().slice(-1)[0]) };
  было = скидки().length;

  // 4. суммой
  const с = document.getElementById('discountSavedInput');
  с.focus(); с.value = String(Math.round((window._итогДоСкидки || 1000000) * 0.1));
  с.dispatchEvent(new Event('input', { bubbles: true })); с.blur(); await пауза();
  вышло.суммой = { n: скидки().length - было, s: строка(скидки().slice(-1)[0]) };
  было = скидки().length;

  // 5. шаги без ухода из поля — по паузе
  п.focus(); шаг(true); шаг(true); шаг(true); await пауза(500);
  вышло.безУходаСразу = скидки().length - было;
  await пауза(31000);
  вышло.безУхода = { n: скидки().length - было, s: строка(скидки().slice(-1)[0]) };
  return вышло;
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
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            try:
                в = стр.evaluate(ШАГИ)
            except Exception as e:
                плохо(f"проба оборвалась: {e!s:.300}")
                в = None
            if в:
                print(f"  {в}")
                if в["стрелка"]["n"] != 1 or в["стрелка"]["s"] != "0 % → 5 %":
                    плохо(f"десять шагов стрелкой дали {в['стрелка']['n']} событий "
                          f"({в['стрелка']['s']}) — ждали одно «0 % → 5 %»")
                if в["туда_обратно"] != 0:
                    плохо(f"вверх и обратно записали {в['туда_обратно']} событий — ждали ни одного")
                if в["руками"]["n"] != 1 or в["руками"]["s"] != "5 % → 7 %":
                    плохо(f"набор руками: {в['руками']} — ждали одно «5 % → 7 %»")
                if в["суммой"]["n"] != 1:
                    плохо(f"ввод суммой: {в['суммой']} — ждали одно событие")
                if в["безУходаСразу"] != 0:
                    плохо(f"шаги без ухода из поля записались сразу ({в['безУходаСразу']})")
                if в["безУхода"]["n"] != 1:
                    плохо(f"шаги без ухода из поля по паузе: {в['безУхода']} — ждали одно событие")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  •", н)
        sys.exit(1)
    print("Чисто.")


if __name__ == "__main__":
    главная()
