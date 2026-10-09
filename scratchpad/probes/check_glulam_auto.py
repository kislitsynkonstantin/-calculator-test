#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: базовая автоматика — правила каркаса на строках бруса.

Константин 09.10.2026: «Сделай базовую автоматику, то что можно взять из
каркаса — одинаковые по смыслу опции». Правила второй раз не пишутся:
каркасные переводятся на строки бруса (КАРКАС_В_БРУС и общие строки).
Проверяется поведением на экране, а не составом таблиц:

  • фундамент один: выбрали свайно-винтовой — остальные закрыты; двойная
    обвязка закрыта, пока свайно-винтового нет;
  • алюминиевые окна закрывают базовые окна, стеклопакет, подоконники и
    улучшения ПВХ; сняли — базовые возвращаются отмеченными;
  • покрытие кровли закрывает металлочерепицу базовой комплектации и другие
    покрытия; плоское снимает карнизную и ветровую планки;
  • дровяная печь ставит набор (установка, дымоход, портал, притопочный лист,
    камень), закрывает электрическую и другие дровяные; снятая — набор
    снимается, сообщение называет снятое; печь Изистим Ялта камня не ставит;
  • стеклянная дверь в режиме «Замена» закрывает металлическую, в «+ Доп» —
    нет;
  • виды покраски снаружи — по одному; ДПК снимает базовую террасную доску,
    фанера — базовый чистовой пол;
  • проект без террасы снимает базовую террасную доску, с террасой — ставит;
  • «Проверка»: «Фундамент не выбран» ведёт к свайно-винтовому бруса;
  • правила каркаса после бруса возвращаются целиком.

Данные выдуманные: тестовый репозиторий открыт.

    python3 check_glulam_auto.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
П_ТЕР, П_БЕЗ = "Брус с террасой 6×6", "Брус без террасы 5×4"


def таблицы():
    т = г.таблицы()
    база = next(p for p in т["pricing_projects"] if p["product"] == "glulam")
    for имя, откр in ((П_ТЕР, 12), (П_БЕЗ, 0)):
        п = dict(база); п.update({"slug": имя, "name": имя, "open_area": откр, "closed_area": 0})
        т["pricing_projects"].append(п)
    кар = lambda ид, сек, цена: {"product": "frame", "option_id": ид, "name": "x", "section": сек,
                                 "included": False, "price": цена, "formula": None, "status": None, "sort": 1}
    брус = lambda ид, сек, имя, цена, общая=None, вкл=False, sort=1000: {
        "product": "glulam", "option_id": ид, "name": имя, "section": сек, "included": вкл,
        "price": цена, "formula": None, "status": None, "sort": sort, "shared_option": общая}
    т["pricing_options"] += [кар(ид, сек, 10000 + н) for н, (ид, сек) in enumerate([
        ("st16", "stove"), ("st34", "stove"), ("st1", "stove"), ("st6", "stove"), ("st15", "stove"),
        ("st12", "stove"), ("st20", "stove"), ("st3", "stove"), ("ex11", "exterior"),
        ("p13", "paint"), ("p14", "paint")] + [("r" + str(н), "roof") for н in range(15, 23)])]
    т["pricing_options"] += [
        брус("kb_f1", "foundation", "Свайно-винтовой (проба)", 50000, sort=10),
        брус("kb_f2", "foundation", "Двойная обвязка (проба)", 20000, sort=11),
        брус("kb_f5", "foundation", "Забивные сваи (проба)", 60000, sort=12),
        брус("kb_f6", "foundation", "Ленточный (проба)", 70000, sort=13),
        брус("kb_f7", "foundation", "Плитный (проба)", 80000, sort=14),
        брус("kb_bp_wd_1", "windows", "Окна базовые (проба)", None, вкл=True, sort=400),
        брус("kb_bp_wd_2", "windows", "Стеклопакет белый (проба)", None, вкл=True, sort=401),
        брус("kb_bp_wd_4", "windows", "Подоконники (проба)", None, вкл=True, sort=402),
        брус("kb_bp_wd_6", "windows", "Дверь металлическая (проба)", None, вкл=True, sort=403),
        брус("kb_w1", "windows", "Окна 70 (проба)", 30000, sort=410),
        брус("kb_w2", "windows", "Окна 82 (проба)", 40000, sort=411),
        брус("kb_w3", "windows", "Ламинация снаружи (проба)", 5000, sort=412),
        брус("kb_w4", "windows", "Ламинация с двух сторон (проба)", 6000, sort=413),
        брус("kb_w6", "windows", "Окна алюминиевые (проба)", 90000, sort=414),
        брус("kb_w7", "windows", "Дверь стеклянная (проба)", 45000, sort=415),
        брус("kb_bp_rf_1", "roof", "Металлочерепица базовая (проба)", None, вкл=True, sort=500),
        брус("kb_r2", "roof", "Водосток пластик (проба)", 9000, sort=510),
        брус("kb_r3", "roof", "Водосток металл (проба)", 12000, sort=511),
    ] + [брус("kb_r" + str(н - 4), "roof", "Покрытие r" + str(н) + " (проба)", None, "r" + str(н), sort=520 + н)
         for н in range(15, 23)] + [
        брус("kb_bp_ex_1", "exterior", "Планки карнизная и ветровая (проба)", None, вкл=True, sort=600),
        брус("kb_bp_ex_3", "exterior", "Террасная доска базовая (проба)", None, вкл=True, sort=601),
        брус("kb_ex8", "exterior", "ДПК (проба)", None, "ex11", sort=602),
        брус("kb_bp_it_1", "interior", "Чистовой пол 27 мм (проба)", None, вкл=True, sort=700),
        брус("kb_i4", "interior", "Фанера (проба)", 15000, sort=701),
        брус("kb_p17", "paint", "Покраска бруса (проба)", 30000, sort=745),
        брус("kb_p18", "paint", "Покраска укрывная (проба)", None, "p13", sort=746),
        брус("kb_p19", "paint", "Покраска маслом (проба)", None, "p14", sort=747),
        брус("kb_st21", "stove", "Печь дровяная (проба)", None, "st16", sort=900),
        брус("kb_st43", "stove", "Печь Ялта (проба)", None, "st34", sort=901),
        брус("kb_st1", "stove", "Установка печи (проба)", None, "st1", sort=902),
        брус("kb_st10", "stove", "Дымоход (проба)", None, "st6", sort=903),
        брус("kb_st19", "stove", "Портал (проба)", None, "st15", sort=904),
        брус("kb_st16", "stove", "Притопочный лист (проба)", None, "st12", sort=905),
        брус("kb_st26", "stove", "Камень (проба)", None, "st20", sort=906),
        брус("kb_st38", "stove", "Печь электрическая (проба)", None, "st3", sort=907),
    ]
    return т


СОСТ = """(ids) => { const р = {}; ids.forEach(ид => { const л = document.getElementById('lbl_' + ид);
    р[ид] = [!!checkedOptions[ид], !!(л && л.dataset.blocked === '1')]; }); return р; }"""


def сост(стр, ids):
    return стр.evaluate(СОСТ, ids)


def ждать(стр, ids, ожид, что):
    с = сост(стр, ids)
    плохо = {ид: с[ид] for ид in ids if с[ид] != ожид}
    if плохо:
        НАХОДКИ.append(f"{что}: [отмечена, закрыта] {плохо}, ждали {ожид}")


def прогон(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    каркас = стр.evaluate("""async () => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      // Правила каркаса проверяются по существу, а не сравнением со снимком:
      // снимок снимается уже после кода, который проверяется.
      const снимок = () => [MUTUAL_EXCLUSIONS.length, AUTO_INCLUDES.length, CONDITIONAL_EXCLUSIONS.length,
        ТРЕБУЕТ_ОПЦИЮ.map(п => п.опция).join(','),
        MUTUAL_EXCLUSIONS.some(п => п.triggers.join() === 'f5' && п.excludes.includes('f9')),
        AUTO_INCLUDES.some(п => п.triggers.includes('st16') && п.includes.includes('st1')),
        CONDITIONAL_EXCLUSIONS.some(п => п.trigger === 'w14'),
        [].concat(...MUTUAL_EXCLUSIONS.map(п => п.triggers.concat(п.excludes))).some(ид => /^kb_/.test(ид))];
      await loadPricing('frame', true); await new Promise(r => setTimeout(r, 300));
      const до = снимок();
      appSettings.showAutoToasts = true;
      window.__тосты = []; const _т = showToast; showToast = (m, ...а) => { __тосты.push(String(m)); return _т(m, ...а); };
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
      const чужие = [].concat(...MUTUAL_EXCLUSIONS.map(п => п.triggers.concat(п.excludes)),
        ...AUTO_INCLUDES.map(п => п.triggers.concat(п.includes)),
        ...CONDITIONAL_EXCLUSIONS.map(п => [п.trigger].concat(п.excludes)),
        ...ТРЕБУЕТ_ОПЦИЮ.map(п => [п.опция].concat(п.требует))).filter(ид => !getOpt(ид));
      const брус = снимок();
      return { до, брус, чужие: [...new Set(чужие)] }; }""")
    if каркас["до"][3] != "f6" or каркас["до"][4:] != [True, True, True, False]:
        НАХОДКИ.append(f"каркас: правила {каркас['до']}, ждали фундамент, набор печи, «Замену» двери, обвязку и ни одной строки бруса")
    if каркас["чужие"]:
        НАХОДКИ.append(f"в правилах бруса id, которых нет в его списке: {каркас['чужие'][:8]}")
    if not каркас["брус"][0] or not каркас["брус"][1]:
        НАХОДКИ.append(f"у бруса нет правил: взаимных/набора/условных/требований {каркас['брус']}")

    # Терраса по проекту
    стр.evaluate("(п) => { selectProjectOption(PROJECTS.findIndex(p => p[0] === п)); }", П_БЕЗ)
    ждать(стр, ["kb_bp_ex_3"], [False, False], "проект без террасы: базовая террасная доска")
    стр.evaluate("(п) => { selectProjectOption(PROJECTS.findIndex(p => p[0] === п)); }", П_ТЕР)
    ждать(стр, ["kb_bp_ex_3"], [True, False], "проект с террасой: базовая террасная доска")

    # «Проверка»: фундамент не выбран — переход к свайно-винтовому бруса
    пункт = стр.evaluate("() => проверкаПоЧекЛисту().замечания.filter(з => /^Фундамент не выбран/.test(з.т)).map(з => з.эл)")
    if пункт != ["lbl_kb_f1"]:
        НАХОДКИ.append(f"«Фундамент не выбран» ведёт к {пункт}, ждали ['lbl_kb_f1']")

    # Фундамент
    ждать(стр, ["kb_f2"], [False, True], "двойная обвязка без свайно-винтового")
    стр.evaluate("() => toggleOpt('kb_f1')")
    ждать(стр, ["kb_f5", "kb_f6", "kb_f7"], [False, True], "свайно-винтовой выбран: другие фундаменты")
    ждать(стр, ["kb_f2"], [False, False], "свайно-винтовой выбран: двойная обвязка")
    стр.evaluate("() => toggleOpt('kb_f1')")
    ждать(стр, ["kb_f5", "kb_f6", "kb_f7"], [False, False], "свайно-винтовой снят: другие фундаменты")

    # Алюминиевые окна
    стр.evaluate("() => toggleOpt('kb_w6')")
    ждать(стр, ["kb_bp_wd_1", "kb_bp_wd_2", "kb_bp_wd_4", "kb_w1", "kb_w2", "kb_w3", "kb_w4"], [False, True],
          "алюминиевые окна выбраны: окна ПВХ, стеклопакет, подоконники")
    ждать(стр, ["kb_bp_wd_6"], [True, False], "алюминиевые окна выбраны: входная дверь")
    стр.evaluate("() => toggleOpt('kb_w6')")
    ждать(стр, ["kb_bp_wd_1", "kb_bp_wd_2", "kb_bp_wd_4"], [True, False], "алюминиевые окна сняты: базовые позиции")
    стр.evaluate("() => toggleOpt('kb_w1')")
    ждать(стр, ["kb_bp_wd_1", "kb_w2"], [False, True], "окна 70 выбраны: базовые окна и окна 82")
    стр.evaluate("() => toggleOpt('kb_w1')")

    # Кровля
    стр.evaluate("() => toggleOpt('kb_r12')")
    ждать(стр, ["kb_bp_rf_1", "kb_r11", "kb_r13", "kb_r14"], [False, True], "Шинглас выбран: металлочерепица и другие покрытия")
    стр.evaluate("() => { toggleOpt('kb_r12'); toggleOpt('kb_r13'); }")
    ждать(стр, ["kb_bp_ex_1"], [False, True], "плоская кровля: карнизная и ветровая планки")
    стр.evaluate("() => toggleOpt('kb_r13')")
    ждать(стр, ["kb_bp_ex_1", "kb_bp_rf_1"], [True, False], "плоская кровля снята: планки и металлочерепица")
    стр.evaluate("() => toggleOpt('kb_r2')")
    ждать(стр, ["kb_r3"], [False, True], "водосток пластик выбран: водосток металл")
    стр.evaluate("() => toggleOpt('kb_r2')")

    # Печь
    стр.evaluate("() => { __тосты.length = 0; toggleOpt('kb_st21'); }")
    ждать(стр, ["kb_st1", "kb_st10", "kb_st19", "kb_st16", "kb_st26"], [True, False], "дровяная печь: набор")
    ждать(стр, ["kb_st38", "kb_st43"], [False, True], "дровяная печь: электрическая и другая дровяная")
    тосты = стр.evaluate("() => __тосты.slice()")
    if not any(т.startswith("Добавлено автоматически") and "Остальные дровяные" in т for т in тосты):
        НАХОДКИ.append(f"дровяная печь выбрана: сообщение {тосты}, ждали «Добавлено автоматически… Остальные дровяные…»")
    стр.evaluate("() => { __тосты.length = 0; toggleOpt('kb_st21'); }")
    ждать(стр, ["kb_st1", "kb_st10", "kb_st19", "kb_st16", "kb_st26"], [False, False], "дровяная печь снята: набор")
    тосты = стр.evaluate("() => __тосты.slice()")
    if not any(т.startswith("Сняты автоматически") and "Жадеит" in т for т in тосты):
        НАХОДКИ.append(f"дровяная печь снята: сообщение {тосты}, ждали «Сняты автоматически» со снятым набором")
    стр.evaluate("() => toggleOpt('kb_st43')")
    ждать(стр, ["kb_st1"], [True, False], "печь Ялта: установка")
    ждать(стр, ["kb_st26"], [False, False], "печь Ялта: камень")
    стр.evaluate("() => toggleOpt('kb_st43')")

    # Стеклянная дверь: «+ Доп» и «Замена»
    тумблер = стр.evaluate("() => !!document.getElementById('cmode_replace_kb_w7')")
    if not тумблер:
        НАХОДКИ.append("у стеклянной двери бруса нет переключателя «+ Доп / Замена»")
    стр.evaluate("() => toggleOpt('kb_w7')")
    ждать(стр, ["kb_bp_wd_6"], [True, False], "стеклянная дверь «+ Доп»: металлическая дверь")
    стр.evaluate("() => setConditionalMode('kb_w7', 'replace')")
    ждать(стр, ["kb_bp_wd_6"], [False, True], "стеклянная дверь «Замена»: металлическая дверь")
    стр.evaluate("() => { setConditionalMode('kb_w7', 'add'); toggleOpt('kb_w7'); }")

    # Покраска, ДПК, фанера
    стр.evaluate("() => toggleOpt('kb_p18')")
    ждать(стр, ["kb_p19", "kb_p17"], [False, True], "покраска укрывной: другие виды покраски")
    стр.evaluate("() => { toggleOpt('kb_p18'); toggleOpt('kb_ex8'); toggleOpt('kb_i4'); }")
    ждать(стр, ["kb_bp_ex_3", "kb_bp_it_1"], [False, True], "ДПК и фанера: базовая доска и чистовой пол")

    # Каркас после бруса
    после = стр.evaluate("""async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 400));
      return [MUTUAL_EXCLUSIONS.length, AUTO_INCLUDES.length, CONDITIONAL_EXCLUSIONS.length,
        ТРЕБУЕТ_ОПЦИЮ.map(п => п.опция).join(','),
        MUTUAL_EXCLUSIONS.some(п => п.triggers.join() === 'f5' && п.excludes.includes('f9')),
        AUTO_INCLUDES.some(п => п.triggers.includes('st16') && п.includes.includes('st1')),
        CONDITIONAL_EXCLUSIONS.some(п => п.trigger === 'w14'),
        [].concat(...MUTUAL_EXCLUSIONS.map(п => п.triggers.concat(п.excludes))).some(ид => /^kb_/.test(ид))]; }""")
    if после != каркас["до"]:
        НАХОДКИ.append(f"каркас после бруса: правила {после}, ждали как до {каркас['до']} и без строк бруса")
    if ош:
        НАХОДКИ.append(f"ошибки страницы: {ош[:3]}")
    стр.close()


def main():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        for н in НАХОДКИ:
            print("✗", н)
        sys.exit(1)
    print("✓ автоматика бруса: фундамент, окна, кровля, печь, дверь, покраска, терраса, «Проверка», каркас после бруса")


if __name__ == "__main__":
    main()
