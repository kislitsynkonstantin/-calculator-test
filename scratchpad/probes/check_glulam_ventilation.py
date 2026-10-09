#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: вентиляция снята и из базы, и из опций.

Константин 09.10.2026, снимком поиска по опциям: «Сделай опции по вентиляции
в брусе неактивной в базе и как опцию. Вентиляцию считают отдельно инженеры».
Строка базовой комплектации «Базовая система вентиляции…» стояла в базе, а
опция с тем же названием за 141 300 ₽ — в «Утеплении, плёнках»: клиент мог
заплатить за то, что база уже обещала.

В базе обе строки — «неактивна» (status legacy), строка базы — не входит в
базу. Проба держит поведение калькулятора:
  • в новом расчёте бруса ни строки базы, ни опции нет — и в режиме «Старые»
    тоже;
  • сохранённый расчёт, где строка базы была отмечена, открывается без неё;
  • сохранённый расчёт с отмеченной опцией показывает её с ценой, и итог
    её учитывает — сумма старого расчёта не меняется сама;
  • в печати нового расчёта вентиляции нет.

    python3 check_glulam_ventilation.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЦЕНА = 141300


def таблицы():
    т = г.таблицы()
    т["pricing_options"] += [
        {"product": "glulam", "option_id": "kb_bp_fr_12", "section": "frame", "included": False, "status": "legacy",
         "price": None, "formula": None, "sort": 210,
         "name": "Базовая система вентиляции (рекуператор в комнате отдыха, активная вытяжная в моечном и парном отделении)"},
        {"product": "glulam", "option_id": "kb_in3", "section": "insulation", "included": False, "status": "legacy",
         "price": ЦЕНА, "formula": None, "sort": 280,
         "name": "Базовая система вентиляции (рекуператор в комнате отдыха, активная вятяжная система в мечном и парном отделении)"},
    ]
    return т


ВИД = """() => { const в = id => { const э = document.getElementById('lbl_' + id); return !!(э && э.getClientRects().length && getComputedStyle(э).display !== 'none'); };
  return { база: в('kb_bp_fr_12'), опция: в('kb_in3'), отмБаза: !!checkedOptions.kb_bp_fr_12, отмОпция: !!checkedOptions.kb_in3,
           итог: Math.round(_currentTotal || 0) }; }"""


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к = бр.new_context(viewport={"width": ш, "height": 900})
    стр = к.new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async () => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0] === 'Брус проба 6×6'));
      setThickness(1); calc(); await new Promise(r => setTimeout(r, 300)); }""")
    в = стр.evaluate(ВИД)
    if в["база"] or в["опция"] or в["отмБаза"] or в["отмОпция"]:
        НАХОДКИ.append(f"{н} новый расчёт: строка базы {в['база']}/{в['отмБаза']}, опция {в['опция']}/{в['отмОпция']}")
    итог0 = в["итог"]
    # Режим «Старые» показывает неактивные опции — снятые он показывать не должен.
    стр.evaluate("async () => { setOptionPricingMode('legacy'); await new Promise(r => setTimeout(r, 300)); }")
    в = стр.evaluate(ВИД)
    if в["база"] or в["опция"]:
        НАХОДКИ.append(f"{н} режим «Старые»: строка базы {в['база']}, опция {в['опция']}")
    стр.evaluate("async () => { setOptionPricingMode('new'); await new Promise(r => setTimeout(r, 300)); }")
    # Печать нового расчёта.
    печать = стр.evaluate("async () => { openPrintPreview(); await new Promise(r => setTimeout(r, 500)); const т = document.getElementById('printDoc').textContent; closePrintPreview(); return т; }")
    if "вентиляци" in печать.lower():
        НАХОДКИ.append(f"{н} в печати нового расчёта есть вентиляция")
    # Сохранённый расчёт: строка базы и опция отмечены.
    стр.evaluate("""async () => { const с = collectState(); с.checkedOptions = Object.assign({}, с.checkedOptions, { kb_bp_fr_12: true, kb_in3: true });
      restoreState(с); await new Promise(r => setTimeout(r, 500)); calc(); await new Promise(r => setTimeout(r, 200)); }""")
    в = стр.evaluate(ВИД)
    if в["база"] or в["отмБаза"]:
        НАХОДКИ.append(f"{н} старый расчёт: строка базы осталась (видна {в['база']}, отмечена {в['отмБаза']})")
    if not (в["опция"] and в["отмОпция"]):
        НАХОДКИ.append(f"{н} старый расчёт с отмеченной опцией: опция видна {в['опция']}, отмечена {в['отмОпция']}")
    elif в["итог"] - итог0 != ЦЕНА:
        НАХОДКИ.append(f"{н} старый расчёт: опция добавила к итогу {в['итог'] - итог0}, ждали {ЦЕНА}")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    print(f"  {н} новый расчёт без вентиляции, «Старые» без неё, старый расчёт: опция {в['опция']}, прирост {в['итог'] - итог0}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: у бруса вентиляции нет ни в базе, ни в опциях — и в режиме «Старые», и в печати; старый расчёт "
          "теряет строку базы, а отмеченная опция в нём остаётся со своей ценой — на 390 и 1440.")


if __name__ == "__main__":
    главная()
