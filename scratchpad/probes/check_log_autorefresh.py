#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий обновляется сам, пока открыт, и кнопки «Обновить» в нём нет.

Константин 24.09.2026: «кнопку обновления убери в журнале действий, поставь
автообновление 30 секунд». Прежде журнал читал базу только при открытии, и
чужое действие — как и сводка комплектаций, приходящая спустя до полуминуты, —
не появлялось, пока не нажмёшь кнопку.

Проба держит:

  • кнопки «Обновить» в шапке нет;
  • новое событие в базе появляется в ленте через 30 секунд — и не раньше;
  • обновление тихое: раскрытая строка остаётся раскрытой, а пролистанная
    лента не прыгает — строка перед глазами стоит на месте;
  • пока открыт выбор сотрудников, лента не перерисовывается — ждёт;
  • закрытый журнал базу не читает.

    python3 check_log_autorefresh.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []
СЕЙЧАС = datetime.now(timezone.utc)


def событие(н, минут_назад, вид="options_batch"):
    return {"id": н, "user_id": "u-проба", "event_type": вид,
            "project_name": f"Проба дом {н}", "total_price": 1000000 + н,
            "options_count": 3, "thickness": 150, "discount": 0, "cash_discount": False,
            "checked_options": {},
            "created_at": (СЕЙЧАС - timedelta(minutes=минут_назад)).isoformat(),
            "details": {"obj": f"Проба дом {н}",
                        "rows": [{"k": "Добавлены", "a": "", "b": "Отливы на цоколь (металл)"},
                                 {"k": "Итог", "a": "1 000 000 ₽", "b": "1 100 000 ₽"}]}}


ТАБЛИЦЫ = {
    "events": [событие(н, 10 + н * 7) for н in range(1, 26)],
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
    к.log_message = lambda *а, **кк: None
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


# Чтения журнала считаются по самому клиенту базы: так видно и то, чего на
# экране не видно, — закрытый журнал, читающий базу впустую.
СЧЁТЧИК = """() => {
  if (window.__чтений !== undefined) return;
  window.__чтений = 0;
  const из = _sb.from.bind(_sb);
  _sb.from = (т) => { if (т === 'events') window.__чтений++; return из(т); };
}"""

ДОБАВИТЬ = """(н) => {
  window.__ТАБЛИЦЫ.events.push({ id: н, user_id: 'u-проба', event_type: 'print',
    project_name: 'Новый дом ' + н, total_price: 2000000, options_count: 1, thickness: 150,
    discount: 0, cash_discount: false, checked_options: {},
    created_at: new Date(Date.now() - 1000).toISOString(),
    details: { obj: 'Новый дом ' + н, rows: [] } });
}"""

ЕСТЬ = "(н) => (document.getElementById('alFeed').innerText || '').includes('Новый дом ' + н)"


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 700})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                "window.addEventListener('DOMContentLoaded', function () {\n"
                "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n"
                "});")
            стр.clock.install()
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.clock.run_for(3000)
            стр.wait_for_timeout(1500)
            стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
            стр.evaluate(СЧЁТЧИК)
            проверить(стр)
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                плохо("ошибка страницы: " + о[:160])
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: кнопки «Обновить» нет, открытый журнал подтягивает новое через 30 секунд и не раньше, "
          "раскрытая строка и место в ленте переживают обновление, выбор сотрудников не сбивается, "
          "закрытый журнал базу не читает.")


def тик(стр, мс):
    # Часы стоят, поэтому время двигаем мелкими шагами с передышкой: ответ
    # заглушки базы приходит таймером, а следующий шаг чтения ставит свой
    # таймер уже после того, как предыдущий сработал.
    шаг = 250
    while мс > 0:
        стр.clock.run_for(min(шаг, мс))
        стр.wait_for_timeout(12)
        мс -= шаг
    стр.wait_for_timeout(150)


def проверить(стр):
    # Часы страницы останавливаем: иначе к подкрученному времени добавляется
    # настоящее, потраченное на саму пробу, и «раньше 30 секунд» не измерить.
    стр.clock.pause_at(datetime.fromtimestamp(стр.evaluate("() => Date.now()") / 1000 + 1, tz=timezone.utc))
    стр.evaluate("() => openActionLog()")
    тик(стр, 500)

    # ── кнопки нет ──
    кнопки = стр.evaluate("""() => [...document.querySelectorAll('#actionLogPanel .al-hbtn')]
      .map(к => (к.getAttribute('title') || '') + ' ' + к.innerText).join(' | ')""")
    if "Обновить" in кнопки:
        плохо("в шапке журнала осталась кнопка «Обновить»")

    # ── раскрыть строку и пролистать ──
    # Раскрываем строку ниже той, что перед глазами: свёрнутая выше неё строка
    # сдвинула бы ленту в обратную сторону и прикрыла бы прыжок от новой строки.
    стр.evaluate("() => { document.getElementById('actionLogOverlay').scrollTop = 900; }")
    тик(стр, 100)
    стр.evaluate("""() => {
      const р = [...document.querySelectorAll('#alFeed .al-row')].find(р => р.getBoundingClientRect().top > 250);
      const кн = р && р.querySelector('.al-chev-btn'); if (кн) кн.click();
    }""")
    тик(стр, 100)
    до = стр.evaluate("""() => {
      const окно = document.getElementById('actionLogOverlay');
      const верх = окно.getBoundingClientRect().top;
      const р = [...document.querySelectorAll('#alFeed .al-row')].find(р => р.getBoundingClientRect().bottom > верх);
      const откр = document.querySelector('#alFeed .al-row.open');
      return { ид: р && р.dataset.ev, верх: р && Math.round(р.getBoundingClientRect().top),
               открыта: откр && откр.dataset.ev, прокрутка: окно.scrollTop };
    }""")
    if not до.get("прокрутка"):
        плохо("ленту не удалось пролистать — проверять место в ленте не на чем")

    # ── новое событие: через 30 секунд, не раньше ──
    стр.evaluate(ДОБАВИТЬ, 101)
    тик(стр, 28000)
    if стр.evaluate(ЕСТЬ, 101):
        плохо("новое событие появилось раньше 30 секунд")
    тик(стр, 3000)
    if not стр.evaluate(ЕСТЬ, 101):
        плохо("новое событие не появилось в открытом журнале за 31 секунду")
    после = стр.evaluate("""(ид) => {
      const р = document.querySelector('#alFeed .al-row[data-ev="' + ид + '"]');
      const откр = document.querySelector('#alFeed .al-row.open');
      return { верх: р ? Math.round(р.getBoundingClientRect().top) : null, открыта: откр && откр.dataset.ev };
    }""", до.get("ид") or "")
    if до.get("открыта") and после.get("открыта") != до.get("открыта"):
        плохо(f"раскрытая строка свернулась при обновлении ({до.get('открыта')} → {после.get('открыта')})")
    if после.get("верх") is None or abs(после["верх"] - (до.get("верх") or 0)) > 2:
        плохо(f"лента прыгнула при обновлении: строка перед глазами была на {до.get('верх')} px, стала на {после.get('верх')} px")

    # ── пока открыт выбор сотрудников — ждёт ──
    стр.evaluate("() => { const м = document.getElementById('alSelMenu'); if (м) м.style.display = 'block'; }")
    стр.evaluate(ДОБАВИТЬ, 102)
    тик(стр, 31000)
    if стр.evaluate(ЕСТЬ, 102):
        плохо("лента перерисовалась под открытым выбором сотрудников")
    стр.evaluate("() => alSelЗакрыть()")
    тик(стр, 31000)
    if not стр.evaluate(ЕСТЬ, 102):
        плохо("после закрытия выбора сотрудников лента так и не обновилась")

    # ── закрытый журнал базу не читает ──
    стр.evaluate("() => closeActionLog()")
    было = стр.evaluate("() => window.__чтений")
    тик(стр, 95000)
    стало = стр.evaluate("() => window.__чтений")
    if стало != было:
        плохо(f"закрытый журнал читал базу: {стало - было} раз(а) за полторы минуты")


if __name__ == "__main__":
    главная()
