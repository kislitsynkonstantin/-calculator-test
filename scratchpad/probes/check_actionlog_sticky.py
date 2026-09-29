#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шапка журнала действий прицеплена, Esc закрывает окно.

Константин 29.09.2026, снимком шапки журнала: «журнал действий закрепляй вот
так при промотке (как в Аналитике). Когда много действий, потом до крестика
долго мотать. И проверь, чтобы Esc срабатывал на закрытие окна журнала
действий». Шапка уезжала вверх вместе с лентой, а Esc журнал не закрывал
вовсе — в общей цепочке Esc его не было.

Проба на 390 и 1440, днём и ночью, с лентой в 80 событий держит:
  • пролистали ленту — шапка стоит у верха экрана, крестик на месте и
    нажимается: в его середине под пальцем он сам, а не строка ленты;
  • прицепленная шапка без скругления — из-под углов не видно строк;
    вернулись наверх — скругление обратно;
  • Esc при открытом списке периода закрывает только список, второй Esc —
    окно; Esc без списков закрывает окно сразу.

    python3 check_actionlog_sticky.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

СЕВ = """() => { const т = window.__ТАБЛИЦЫ, д = Date.now(), я = (_sbUser && _sbUser.id) || 'u-проба';
  т.events = [];
  for (let i = 0; i < 80; i++) т.events.push({ id: 's' + i, user_id: я, event_type: i % 2 ? 'discount_changed' : 'print',
    created_at: new Date(д - i * 1800e3).toISOString(), project_name: 'Проба дом 8×8',
    details: { rows: i % 2 ? [{ k: 'Скидка', a: '0 %', b: (i % 7) + ' %' }] : [{ k: 'Шаблон', b: 'blank' }] } }); }"""

ШАПКА = """() => { const о = document.getElementById('actionLogOverlay'), ш = document.querySelector('#actionLogPanel > .ovl-head');
  const х = ш.querySelector('.ovl-x'), r = ш.getBoundingClientRect(), xr = х.getBoundingClientRect();
  const под = document.elementFromPoint(xr.left + xr.width / 2, xr.top + xr.height / 2);
  return { верх: Math.round(r.top), низ: Math.round(r.bottom), прокрутка: Math.round(о.scrollTop), всего: о.scrollHeight - о.clientHeight,
    крестик: !!(под && (под === х || х.contains(под))), угол: getComputedStyle(ш).borderTopLeftRadius, класс: ш.className }; }"""


def открыт(стр):
    return стр.evaluate("() => getComputedStyle(document.getElementById('actionLogOverlay')).display !== 'none'")


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(бр, порт, ш, в, ночь)
    стр.evaluate(СЕВ)
    стр.evaluate("() => { _alПериод = 'всё'; openActionLog(); }"); стр.wait_for_timeout(1500)
    с = стр.evaluate(ШАПКА)
    if с["всего"] < 600:
        НАХОДКИ.append(f"{н} лента короткая — пролистать нечего ({с['всего']} px), проверка вслепую")
    if "al-stuck" in с["класс"] or с["угол"] == "0px":
        НАХОДКИ.append(f"{н} шапка прицеплена ещё до прокрутки: {с}")
    стр.evaluate("() => { document.getElementById('actionLogOverlay').scrollTop = 1500; }"); стр.wait_for_timeout(300)
    с = стр.evaluate(ШАПКА)
    if abs(с["верх"]) > 1:
        НАХОДКИ.append(f"{н} пролистали на {с['прокрутка']} px — шапка уехала: верх {с['верх']} px")
    if not с["крестик"]:
        НАХОДКИ.append(f"{н} крестик после прокрутки не нажимается — под ним другой элемент")
    if с["угол"] != "0px":
        НАХОДКИ.append(f"{н} прицепленная шапка со скруглением {с['угол']} — из-под углов видны строки")
    стр.screenshot(path=str(м.СНИМКИ / f"actionlog-sticky-{ш}{'-n' if ночь else ''}.png"))
    стр.evaluate("() => { document.getElementById('actionLogOverlay').scrollTop = 0; }"); стр.wait_for_timeout(300)
    с = стр.evaluate(ШАПКА)
    if с["угол"] == "0px" or "al-stuck" in с["класс"]:
        НАХОДКИ.append(f"{н} вернулись наверх — шапка осталась прицепленной: {с}")
    # ── Esc ──
    стр.evaluate("() => alPerToggle({ stopPropagation(){} })"); стр.wait_for_timeout(250)
    if стр.evaluate("() => document.getElementById('alPerMenu').style.display") == "none":
        НАХОДКИ.append(f"{н} список периода не открылся — Esc со списком не проверен")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(250)
    if not открыт(стр):
        НАХОДКИ.append(f"{н} Esc при открытом списке периода закрыл всё окно, а не список")
    elif стр.evaluate("() => document.getElementById('alPerMenu').style.display") != "none":
        НАХОДКИ.append(f"{н} Esc не закрыл список периода")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(300)
    if открыт(стр):
        НАХОДКИ.append(f"{н} Esc не закрывает журнал действий")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в, ночь in ((390, 844, False), (390, 844, True), (1440, 900, False), (1440, 900, True)):
                прогон(бр, порт, ш, в, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: шапка журнала действий прицеплена при прокрутке, крестик нажимается, углы прицепленной шапки "
          "прямые и возвращаются наверху; Esc закрывает сначала список периода, потом окно — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
