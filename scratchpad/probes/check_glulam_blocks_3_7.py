#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус, блоки 3–7: двери, кровля, покраска, доп. опции, парная.

Константин 09.10.2026: «Делай все опции, кроме автоматики». Решения — из
разбора опций бруса и его ответов: межкомнатные двери по 24 000 ₽ с их
примечаниями, кровля и покраска — формулами каркаса, водостоки и
снегозадержатели — своя цена проекта, а без неё площадь кровли на ставку,
бытовка, биотуалет, вывоз мусора — как у каркаса, парная — ценами каркаса.

Цены здесь выдуманные и нарочно не совпадают со строками бруса: проба
различает, откуда взялось число. Проверяется на экране и в расчёте:

  • общая строка не читает таблицу проекта бруса: у бытовки 91 000 ₽ каркаса,
    а не 52 000 ₽ из таблицы проекта;
  • общая строка, у которой в базе каркаса строки нет (вывоз мусора), берёт
    цену из файла;
  • межкомнатные двери — общие, считаются дверями; отмеченные гасят
    примечание «Межкомнатные двери не входят в расчёт»;
  • водосток: у проекта со своей ценой — она; у проекта без цены и без
    площади — «укажите площадь» и пункт «Заполнить площадь кровли» в
    «Проверке»; вписали площадь — формула, пункт ушёл, примечание о
    водостоке погасло;
  • общая строка, снятая у каркаса, у бруса скрыта; снятая строка бруса
    скрыта, но в сохранённом расчёте отмеченной видна;
  • новая общая покраска видна с формулой каркаса, хотя своя строка в базе
    неактивна (так её не видит бой); отмеченная гасит «Покраска строения не
    входит в расчёт»;
  • правило чек-листа по каркасным строкам (премиальная парная) работает и
    по общим строкам бруса;
  • снегозадержатели бруса называются как у каркаса: «(трубчатые)», а с
    отмеченным Шингласом — «(крючки)»;
  • у каркаса всё по-прежнему.

    python3 check_glulam_blocks_3_7.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
П1, П2 = "Брус проба 6×6", "Брус без водостока 5×5"
ФОРМУЛА_P13 = {"coef": 1600, "mult": 1.1, "areaSrc": "paint", "areaMult": 1.25, "addonInside": 10000,
               "defaultMargin": 0.3, "translucentOption": True}
ФОРМУЛА_R10 = {"coef": 2200, "areaSrc": "roofSlope", "defaultMargin": 0.3}
ВОДОСТОК = {"coef": 270, "areaSrc": "roof", "defaultMargin": 0.3, "matrixFirst": True}


def таблицы():
    т = г.таблицы()
    п2 = dict(next(p for p in т["pricing_projects"] if p["product"] == "glulam"))
    п2.update({"slug": П2, "name": П2})
    т["pricing_projects"].append(п2)
    кар = lambda ид, сек, цена, st=None, f=None: {"product": "frame", "option_id": ид, "name": "x", "section": сек,
                                                  "included": False, "price": цена, "formula": f, "status": st, "sort": 1}
    брус = lambda ид, сек, имя, цена, общая=None, st=None, f=None, sort=1000: {
        "product": "glulam", "option_id": ид, "name": имя, "section": сек, "included": False,
        "price": цена, "formula": f, "status": st, "sort": sort, "shared_option": общая}
    т["pricing_options"] += [
        кар("e6", "extra", 91000), кар("w15", "windows", 24000), кар("r10", "roof", None, "legacy", ФОРМУЛА_R10),
        кар("p13", "paint", None, "formula", ФОРМУЛА_P13),
        кар("r16", "roof", None, "formula", {"coef": 770, "mult": 1.1, "areaSrc": "roof", "defaultMargin": 0.35}),
        брус("kb_r12", "roof", "Шинглас (своя строка)", None, "r16", sort=660),
        брус("kb_r4", "roof", "Снегозадержатели", None, None, None,
             {"coef": 191, "areaSrc": "roof", "defaultMargin": 0.3, "matrixFirst": True}, sort=580),
        кар("s19", "steam", 37500), кар("s23", "steam", 66250), кар("s27", "steam", 56250), кар("s34", "steam", 127500),
        брус("kb_e2", "extra", "Аренда бытовки (своя строка)", None, "e6", sort=1560),
        брус("kb_e3", "extra", "Вывоз мусора (своя строка)", 11111, "e12", sort=1570),
        брус("kb_w8", "windows", "Межкомнатные двери (своя строка)", 13200, "w15", sort=480),
        брус("kb_r2", "roof", "Водосточная система (пластик)", None, None, None, ВОДОСТОК, sort=560),
        брус("kb_r6", "roof", "Снегозадержатели трубчатые (своя)", None, "r10", sort=600),
        брус("kb_p4", "paint", "Масло снаружи по проекту", 50000, sort=760),
        брус("kb_p18", "paint", "Покраска снаружи (своя строка)", None, "p13", "legacy", ФОРМУЛА_P13, sort=746),
        брус("kb_s15", "steam", "Подсветка пологов (своя)", 25000, "s19", sort=1090),
        брус("kb_s19", "steam", "Соль (своя)", 55000, "s23", sort=1110),
        брус("kb_s22", "steam", "Подсветка потолка (своя)", 90000, "s27", sort=1140),
        брус("kb_s27", "steam", "Премиальная сборка 102 000 (своя)", 102000, "s34", sort=1190),
        брус("kb_s28", "steam", "Премиальная сборка 128 000 (своя)", 128000, sort=1200),
    ]
    т["pricing_matrix"] += [
        {"product": "glulam", "project_slug": "Брус проба 6×6", "option_id": "kb_e2", "price": 52000},
        {"product": "glulam", "project_slug": "Брус проба 6×6", "option_id": "kb_r2", "price": 38200},
    ]
    return т


ВИД = """() => { const в = ид => { const э = document.getElementById('lbl_' + ид);
    return !!(э && э.getClientRects().length && getComputedStyle(э).display !== 'none'); };
  const и = ид => { const э = document.querySelector('#lbl_' + ид + ' .opt-name'); return э ? э.textContent.trim() : null; };
  const ц = ид => { const o = OPTIONS.find(o => o.id === ид); return o ? getOptPrice(o) : undefined; };
  const прим = (сек, т) => hiddenNotes.has(ключПримечания(сек, (SECTION_NOTES[сек] || []).indexOf(т)));
  const пр = проверкаПоЧекЛисту();
  return { бытовка: ц('kb_e2'), мусор: ц('kb_e3'), двери: [в('kb_w8'), ц('kb_w8'), !!(OPTIONS.find(o => o.id === 'kb_w8') || {}).formula],
           водосток: [в('kb_r2'), ц('kb_r2'), !!document.querySelector('#optprice_kb_r2 .kb-need-area'),
                      !!document.querySelector('#lbl_kb_r2 .opt-formula-badge')],
           трубчатые: в('kb_r6'), масло: в('kb_p4'), сборка128: в('kb_s28'),
           покраска: [в('kb_p18'), и('kb_p18'), ц('kb_p18')],
           парная: [ц('kb_s15'), ц('kb_s27'), и('kb_s27')],
           примДвери: прим('windows', 'Межкомнатные двери не входят в расчёт'),
           примСтроения: прим('paint', 'Покраска строения не входит в расчёт'),
           примВодосток: hiddenNotes.has('roof_drain'),
           замечания: пр.замечания.map(з => [з.т, з.эл]), итог: Math.round(_currentTotal || 0) }; }"""

ИМЯ_P13 = "Покраска снаружи (укрывная краска Sikkens, Zobel или аналоги)"
ИМЯ_S34 = "Сборка премиальной парной (специальная бригада, LED-монтаж)"


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
    стр.evaluate("""async (п) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0] === п));
      setThickness(1); calc(); await new Promise(r => setTimeout(r, 300)); }""", П1)
    в = стр.evaluate(ВИД)
    if в["бытовка"] != 91000:
        НАХОДКИ.append(f"{н} бытовка {в['бытовка']}, ждали 91 000 каркаса, а не 52 000 из таблицы проекта бруса")
    if в["мусор"] != 37000:
        НАХОДКИ.append(f"{н} вывоз мусора {в['мусор']}, ждали 37 000 из файла каркаса")
    if в["двери"] != [True, 24000, True]:
        НАХОДКИ.append(f"{н} межкомнатные двери: видна/цена/поштучно {в['двери']}, ждали [True, 24000, True]")
    if в["водосток"][:2] != [True, 38200] or в["водосток"][3]:
        НАХОДКИ.append(f"{н} водосток у проекта со своей ценой: {в['водосток']}, ждали 38 200 без пометки «формула»")
    if в["трубчатые"]:
        НАХОДКИ.append(f"{н} общая строка, снятая у каркаса, у бруса видна")
    if в["масло"] or в["сборка128"]:
        НАХОДКИ.append(f"{н} снятые строки бруса видны: масло {в['масло']}, сборка 128 000 {в['сборка128']}")
    if в["покраска"][:2] != [True, ИМЯ_P13] or в["покраска"][2] is not None:
        НАХОДКИ.append(f"{н} общая покраска до площади: {в['покраска']}, ждали видна, «{ИМЯ_P13}», без цены")
    if в["парная"] != [37500, 127500, ИМЯ_S34]:
        НАХОДКИ.append(f"{н} парная: {в['парная']}, ждали цены каркаса 37 500 и 127 500")
    # Двери: две двери и примечание
    стр.evaluate("() => { toggleOpt('kb_w8'); formulaOverrides.kb_w8 = { area: 2 }; calc(); }")
    в = стр.evaluate(ВИД)
    if в["двери"][1] != 48000:
        НАХОДКИ.append(f"{н} две межкомнатные двери стоят {в['двери'][1]}, ждали 48 000")
    if not в["примДвери"]:
        НАХОДКИ.append(f"{н} межкомнатные двери отмечены, а примечание «не входят в расчёт» не погасло")
    # Покраска по площади, примечание
    стр.evaluate("() => { kbSetArea('fasad', '100'); toggleOpt('kb_p18'); calc(); }")
    в = стр.evaluate(ВИД)
    if в["покраска"][2] != 328571:
        НАХОДКИ.append(f"{н} общая покраска при 100 м²: {в['покраска'][2]}, ждали 328 571 по формуле каркаса")
    if not в["примСтроения"]:
        НАХОДКИ.append(f"{н} покраска снаружи отмечена, а «Покраска строения не входит в расчёт» не погасло")
    # Премиальная парная — правило чек-листа по общим строкам
    стр.evaluate("() => { ['kb_s15', 'kb_s19', 'kb_s22'].forEach(toggleOpt); calc(); }")
    в = стр.evaluate(ВИД)
    прем = [з for з in в["замечания"] if з[0] == "Добавить сборку премиальной парной"]
    if прем != [["Добавить сборку премиальной парной", "lbl_kb_s27"]]:
        НАХОДКИ.append(f"{н} премиальная парная в «Проверке»: {прем}, ждали пункт с переходом к строке бруса")
    # Сохранённый расчёт со снятой строкой
    вид = стр.evaluate("() => { checkedOptions.kb_p4 = true; const а = isOptionVisible(getOpt('kb_p4')); delete checkedOptions.kb_p4; return [а, isOptionVisible(getOpt('kb_p4'))]; }")
    if вид != [True, False]:
        НАХОДКИ.append(f"{н} снятая строка бруса: видна отмеченной / неотмеченной {вид}, ждали [True, False]")
    # Проект без своей цены водостока
    стр.evaluate("""async (п) => { selectProjectOption(PROJECTS.findIndex(p => p[0] === п)); kbSetArea('roof', '');
      kbSetArea('fasad', ''); calc(); await new Promise(r => setTimeout(r, 300));
      if (!checkedOptions.kb_r2) toggleOpt('kb_r2'); if (!checkedOptions.kb_p18) toggleOpt('kb_p18'); calc(); }""", П2)
    в = стр.evaluate(ВИД)
    оба = [з for з in в["замечания"] if з[0].startswith("Заполнить площадь")]
    if оба != [["Заполнить площадь фасада и кровли", "kbAreaFasad kbAreaRoof"]]:
        НАХОДКИ.append(f"{н} обе площади пусты, отмечены водосток и покраска: {оба}, ждали один пункт «Заполнить площадь фасада и кровли» к обоим полям")
    стр.evaluate("() => { kbSetArea('fasad', '100'); calc(); }")
    в = стр.evaluate(ВИД)
    пункт = [з for з in в["замечания"] if з[0].startswith("Заполнить площадь")]
    if в["водосток"][1] is not None or not в["водосток"][2]:
        НАХОДКИ.append(f"{н} водосток у проекта без цены и без площади: {в['водосток']}, ждали «укажите площадь»")
    if пункт != [["Заполнить площадь кровли", "kbAreaRoof"]]:
        НАХОДКИ.append(f"{н} пункт о площади в «Проверке»: {пункт}, ждали «Заполнить площадь кровли» с переходом к полю")
    if not в["примВодосток"]:
        НАХОДКИ.append(f"{н} водосток отмечен, а примечание «Водосточная система не входит в стоимость» не погасло")
    # Строка, построенная сразу у проекта без своей цены, — та же «укажите площадь», а не «введите сумму»
    свежая = стр.evaluate("() => { const э = buildOptItem(getOpt('kb_r2')); return [!!э.querySelector('.kb-need-area'), !!э.querySelector('#por_kb_r2')]; }")
    if свежая != [True, False]:
        НАХОДКИ.append(f"{н} строка водостока, построенная у проекта без цены: «укажите площадь»/«введите сумму» {свежая}, ждали [True, False]")
    стр.evaluate("() => { kbSetArea('roof', '100'); calc(); }")
    в = стр.evaluate(ВИД)
    if в["водосток"][1] != 38571 or в["водосток"][3]:
        НАХОДКИ.append(f"{н} водосток при 100 м² кровли: {в['водосток']}, ждали 38 571 без пометки «формула»")
    if any(з[0].startswith("Заполнить площадь") for з in в["замечания"]):
        НАХОДКИ.append(f"{н} площадь вписана, а пункт «Заполнить площадь» остался")
    # Снегозадержатели бруса: «(трубчатые)», с Шингласом — «(крючки)», как у каркаса
    имена = стр.evaluate("""async () => { const и = () => [getOpt('kb_r4').name,
        (document.querySelector('#lbl_kb_r4 .opt-name') || {}).textContent || ''];
      const а = и(); toggleOpt('kb_r12'); calc(); const б = и(); toggleOpt('kb_r12'); calc(); const в = и();
      return [а, б, в]; }""")
    ждём = ["Снегозадержатели (трубчатые)", "Снегозадержатели (крючки)", "Снегозадержатели (трубчатые)"]
    for (имя, строка), ж, когда in zip(имена, ждём, ("без Шингласа", "с Шингласом", "Шинглас снят")):
        if имя != ж or ж not in строка:
            НАХОДКИ.append(f"{н} снегозадержатели {когда}: «{имя}», на экране «{строка.strip()[:60]}», ждали «{ж}»")
    # Каркас: та же строка, та же цена
    к_ = стр.evaluate("""async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 400));
      const ц = ид => { const o = OPTIONS.find(o => o.id === ид); return o ? [o.name, o.price] : null; };
      return [ц('e6'), ц('w15'), ц('s34')]; }""")
    if [x[1] if x else None for x in к_] != [91000, 24000, 127500]:
        НАХОДКИ.append(f"{н} каркас: {к_}")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    print(f"  {н} бытовка {91000 if not НАХОДКИ else '?'}, водосток {в['водосток'][1]}, покраска 100 м²")
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
    print("Чисто: общие строки бруса считают ценой каркаса мимо таблицы проекта, двери — дверями с примечанием, "
          "водосток — своей ценой или от площади кровли с пунктом в «Проверке», снятые строки скрыты, "
          "правила чек-листа и примечаний находят общие строки — на 390 и 1440.")


if __name__ == "__main__":
    главная()
