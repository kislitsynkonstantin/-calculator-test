#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: общие с каркасом опции и раздел печи как у каркаса.

Константин 09.10.2026: «Общие опции — как в разделе В, норм. Сам реши, как это
устроить в базе и файлах выгрузки. Главное, чтобы в калькуляторе не
отличалось», и по печи: «как в каркасе». Строка бруса с пометкой
shared_option берёт название из списка каркаса в файле, а цену, формулу и
статус — из строки каркаса в базе. Своя строка бруса остаётся.

Цены здесь выдуманные и нарочно не совпадают со строками бруса: проба
различает, откуда взялось число. Проба смотрит на строку на экране и на итог:

  • общая строка печи показывает каркасное название и каркасную цену, а не
    свои; отмеченная, она прибавляет к итогу каркасную цену;
  • новая общая строка (электрическая печь) — тоже с каркасной ценой;
  • статус берётся у каркаса: строка, неактивная у каркаса, у бруса скрыта;
  • строка бруса без пометки остаётся своей — со своим названием и ценой;
  • «Классика до 23 м³» снята (неактивна) и не видна;
  • сохранённый расчёт с общей строкой открывается с каркасной ценой;
  • у каркаса всё по-прежнему: та же строка с той же ценой.

    python3 check_glulam_shared_stove.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ОПТИМА = "Печь Ферингер Оптима до 28 м³"           # имя st18 в списке каркаса
HARVIA = "Угловая печь для сауны Harvia Glow Corner TRC 90, 9 кВт"
ЦЕНА_ОПТИМА, ЦЕНА_HARVIA = 71000, 61000


def таблицы():
    т = г.таблицы()
    кар = lambda ид, цена, st=None: {"product": "frame", "option_id": ид, "name": "x", "section": "stove",
                                     "included": False, "price": цена, "formula": None, "status": st, "sort": 1}
    брус = lambda ид, имя, цена, общая=None, st=None, sort=1300: {
        "product": "glulam", "option_id": ид, "name": имя, "section": "stove", "included": False,
        "price": цена, "formula": None, "status": st, "sort": sort, "shared_option": общая}
    т["pricing_options"] += [
        кар("st18", ЦЕНА_ОПТИМА), кар("st3", ЦЕНА_HARVIA), кар("st22", 159900, "legacy"),
        брус("kb_st24", "Печь Ферингер Оптима до 28 м3", 64400, "st18", sort=1325),
        брус("kb_st38", "Угловая печь Harvia (своя строка)", 1, "st3", sort=1280),
        брус("kb_st28", "Печь Ферингер Оптима «Змеевик Наборный» до 23 м3", 159900, "st22", sort=1340),
        брус("kb_st23", "Печь Ферингер Классика до 23 м3", None, None, "legacy", sort=1490),
        брус("kb_st99", "Своя печь бруса проба", 12345, None, sort=1450),
    ]
    return т


ВИД = """() => { const в = ид => { const э = document.getElementById('lbl_' + ид);
    return !!(э && э.getClientRects().length && getComputedStyle(э).display !== 'none'); };
  const и = ид => { const э = document.querySelector('#lbl_' + ид + ' .opt-name'); return э ? э.textContent.trim() : null; };
  const ц = ид => { const o = OPTIONS.find(o => o.id === ид); return o ? getOptPrice(o) : undefined; };
  return { оптима: [в('kb_st24'), и('kb_st24'), ц('kb_st24')], harvia: [в('kb_st38'), и('kb_st38'), ц('kb_st38')],
           змеевик: в('kb_st28'), классика: в('kb_st23'), своя: [в('kb_st99'), и('kb_st99'), ц('kb_st99')],
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
    if в["оптима"] != [True, ОПТИМА, ЦЕНА_ОПТИМА]:
        НАХОДКИ.append(f"{н} общая Оптима: видна/имя/цена {в['оптима']}, ждали [True, «{ОПТИМА}», {ЦЕНА_ОПТИМА}]")
    if в["harvia"] != [True, HARVIA, ЦЕНА_HARVIA]:
        НАХОДКИ.append(f"{н} новая общая Harvia: {в['harvia']}, ждали [True, «{HARVIA}», {ЦЕНА_HARVIA}]")
    if в["змеевик"]:
        НАХОДКИ.append(f"{н} строка, неактивная у каркаса, у бруса видна")
    if в["классика"]:
        НАХОДКИ.append(f"{н} «Классика до 23 м³» видна, а она снята")
    if в["своя"] != [True, "Своя печь бруса проба", 12345]:
        НАХОДКИ.append(f"{н} строка без пометки: {в['своя']}, ждали свою")
    итог0 = в["итог"]
    стр.evaluate("() => { toggleOpt('kb_st24'); calc(); }")
    в = стр.evaluate(ВИД)
    if в["итог"] - итог0 != ЦЕНА_ОПТИМА:
        НАХОДКИ.append(f"{н} отмеченная общая Оптима прибавила {в['итог'] - итог0}, ждали {ЦЕНА_ОПТИМА}")
    # Сохранили и открыли
    стр.evaluate("""async () => { const с = JSON.parse(JSON.stringify(collectState())); restoreState(с);
      await new Promise(r => setTimeout(r, 500)); calc(); }""")
    в2 = стр.evaluate(ВИД)
    if в2["итог"] != в["итог"] or в2["оптима"][2] != ЦЕНА_ОПТИМА:
        НАХОДКИ.append(f"{н} открытый расчёт: итог {в['итог']} → {в2['итог']}, Оптима {в2['оптима']}")
    # Каркас: та же строка с той же ценой
    к_ = стр.evaluate("""async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 400));
      const o = OPTIONS.find(o => o.id === 'st18'); return o ? [o.name, o.price] : null; }""")
    if к_ != [ОПТИМА, ЦЕНА_ОПТИМА]:
        НАХОДКИ.append(f"{н} каркас: строка Оптимы {к_}")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    print(f"  {н} Оптима {в['оптима']}, Harvia {в['harvia'][2]}, прирост {в['итог'] - итог0}")
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
    print("Чисто: общие строки бруса берут название из списка каркаса, цену и статус — из строки каркаса; "
          "своя строка остаётся своей, «Классика» снята, сохранённый расчёт считает каркасной ценой — на 390 и 1440.")


if __name__ == "__main__":
    главная()
