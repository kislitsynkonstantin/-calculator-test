#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Аналитика считает сохранённые расчёты по текущему состоянию пресета.

Константин 25.09.2026: «Брать ли суммы и опции в аналитике из текущего
состояния пресета? — Конечно». Журнал пишет сумму и опции в минуту первого
сохранения, а правки после него до аналитики не доходили: расчёт, начатый на
4,6 млн и доведённый до 7 млн, в аналитике так и стоял на 4,6.

Проба держит:
  • строки «Расчёт сохранён» из журнала заменяются пресетами из базы
    (функция `preset_stats`) — по одной на пресет, с нынешними суммой,
    опциями и проектом; удалённые пресеты остаются;
  • прочие события (печать и др.) идут из журнала как есть;
  • менеджер видит только свои пресеты, даже если функция вернула больше;
  • функции нет или она не ответила — окно показывает журнал, как раньше.

    python3 check_stats_presets.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
НАХОДКИ = []

СОБЫТИЯ = [
    {"id": "e1", "user_id": "u-проба", "event_type": "preset_saved", "project_name": "Виго", "total_price": 4600000,
     "checked_options": {"a": True}, "discount": 0, "created_at": "2026-09-24T06:50:00Z"},
    {"id": "e2", "user_id": "u-другой", "event_type": "preset_saved", "project_name": "Милан", "total_price": 1000000,
     "checked_options": {}, "discount": 0, "created_at": "2026-09-24T07:00:00Z"},
    {"id": "e3", "user_id": "u-проба", "event_type": "print", "project_name": "Виго", "total_price": 7044020,
     "checked_options": {}, "discount": 2.8, "created_at": "2026-09-25T18:00:00Z"},
]
ПРЕСЕТЫ = [
    {"user_id": "u-проба", "preset_id": "preset_1", "created_at": "2026-09-24T06:50:59Z", "updated_at": "2026-09-25T18:03:00Z",
     "deleted_at": None, "project_name": "Виго", "total_price": "7044020", "options_count": 3,
     "checked_options": {"a": True, "b": True, "c": True}, "thickness": 150, "discount": "2.8", "cash_discount": True, "tech": "frame"},
    {"user_id": "u-проба", "preset_id": "preset_2", "created_at": "2026-09-20T10:00:00Z", "updated_at": "2026-09-21T10:00:00Z",
     "deleted_at": "2026-09-22T10:00:00Z", "project_name": "Техас", "total_price": "8532400", "options_count": 1,
     "checked_options": {"z": True}, "thickness": 150, "discount": "0", "cash_discount": False, "tech": "glulam"},
    {"user_id": "u-другой", "preset_id": "preset_3", "created_at": "2026-09-24T07:00:00Z", "updated_at": "2026-09-24T09:00:00Z",
     "deleted_at": None, "project_name": "Милан", "total_price": "9048682", "options_count": 0,
     "checked_options": {}, "thickness": 150, "discount": "0", "cash_discount": False, "tech": "frame"},
]


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


# Открывает окно аналитики и ловит последнее отправленное в него «events».
ОТКРЫТЬ = """async (роль) => {
  window._sbProfile = { role: роль, full_name: 'Проба' };
  window.__ТАБЛИЦЫ.profiles[0].role = роль;   // страница может перечитать профиль
  const рамка = document.getElementById('statsFrame');
  // Окно шлёт данные трижды (сразу, через 300 и 800 мс) — прошлый прогон
  // не должен попасть в этот.
  await new Promise(r => setTimeout(r, 1200));
  window.__послано = [];
  closeStats();
  openStats();
  const было = рамка.onload;
  рамка.onload = function () {
    const окно = рамка.contentWindow, отправить = окно.postMessage.bind(окно);
    окно.postMessage = function (м, ...о) { if (м && м.type === 'events') window.__послано.push(м); return отправить(м, ...о); };
    return было && было.apply(this, arguments);
  };
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 100));
    if (window.__послано.some(м => м.source === 'cloud')) break;
  }
  await new Promise(r => setTimeout(r, 200));
  const облако = window.__послано.filter(м => м.source === 'cloud').pop();
  closeStats();
  return облако ? облако.events.map(с => ({ кто: с.user_id, вид: с.event_type, проект: с.project_name,
    сумма: Number(с.total_price), опций: Object.keys(с.checked_options || {}).length })) : null;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");"
                "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];"
                "window.__ТАБЛИЦЫ.events = " + json.dumps(СОБЫТИЯ, ensure_ascii=False) + ";"
                "window.__RPC = Object.assign(window.__RPC || {}, { preset_stats: " + json.dumps(ПРЕСЕТЫ, ensure_ascii=False) + " });")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("""() => { ['pricingErrorScreen', 'loginScreen'].forEach(и => {
              const э = document.getElementById(и); if (э) э.style.display = 'none'; }); }""")

            # 1. Администратор: сохранения — из пресетов, печать — из журнала.
            с_ = стр.evaluate(ОТКРЫТЬ, "admin")
            if с_ is None:
                плохо("администратор: окно аналитики не получило данных из базы")
            else:
                сохр = sorted((x["кто"], x["сумма"], x["опций"]) for x in с_ if x["вид"] == "preset_saved")
                ждём = sorted([("u-проба", 7044020, 3), ("u-проба", 8532400, 1), ("u-другой", 9048682, 0)])
                if сохр != ждём:
                    плохо(f"администратор: сохранения не из текущих пресетов: {сохр}")
                if not any(x["вид"] == "print" and x["сумма"] == 7044020 for x in с_):
                    плохо("администратор: событие печати пропало")
                if any(x["вид"] == "preset_saved" and x["сумма"] in (4600000, 1000000) for x in с_):
                    плохо("администратор: старые снимки из журнала остались рядом с пресетами")
                print(f"  администратор: сохранений {len(сохр)}, суммы {[x[1] for x in сохр]}")

            # 2. Менеджер: только свои, даже если функция вернула чужое.
            с_ = стр.evaluate(ОТКРЫТЬ, "manager")
            if с_ is None:
                плохо("менеджер: окно аналитики не получило данных из базы")
            else:
                чужие = [x for x in с_ if x["кто"] != "u-проба"]
                if чужие:
                    плохо(f"менеджер видит чужое: {чужие}")
                сохр = sorted(x["сумма"] for x in с_ if x["вид"] == "preset_saved")
                if сохр != [7044020, 8532400]:
                    плохо(f"менеджер: свои сохранения не из пресетов: {сохр}")
                print(f"  менеджер: сохранений {len(сохр)}, чужих строк {len(чужие)}")

            # 3. Функции нет — окно показывает журнал, как раньше.
            стр.evaluate("() => { delete window.__RPC.preset_stats; }")
            с_ = стр.evaluate(ОТКРЫТЬ, "admin")
            сохр = sorted(x["сумма"] for x in (с_ or []) if x["вид"] == "preset_saved")
            if сохр != [1000000, 4600000]:
                плохо(f"без функции окно не вернулось к журналу: {сохр}")
            print(f"  без функции: сохранения из журнала {сохр}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: сохранённые расчёты в аналитике — по текущему состоянию пресетов, прочие события — из журнала; "
          "менеджер видит только своё; без функции в базе окно работает по журналу, как раньше.")


if __name__ == "__main__":
    главная()
