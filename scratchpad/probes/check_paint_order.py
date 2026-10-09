#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Покраска: заводская — после подбора цвета, покраска клеёного бруса — только в брусе.

Константин 30.09.2026, двумя снимками раздела «Покраска»:
  1. «Опцию по покраске клеёного бруса убери из каркаса. Перенеси в клеёный
     брус — это относится к той технологии. Проверь, чтобы было отражено в
     таблице экспорта»;
  2. «Заводскую покраску поставь после подбора цвета, а потом ручную (там где
     не прописано заводская — это ручная)».

Проба на 390 и 1440 держит:
  • каркас: строки раздела идут «Подбор цвета» → заводская укрывная →
    заводская маслом → покраска снаружи укрывная → маслом со шлифовкой →
    террасная доска; покраски клеёного бруса в списке нет;
  • каркас: сохранённый расчёт с отмеченной покраской клеёного бруса её
    показывает (снятая опция не пропадает из чужих расчётов);
  • выгрузка: в «Матрице опций» у неё статус «снята», в «Калькуляторе опций»
    её нет — проверяется по тем же условиям, что стоят в выгрузке;
  • брус: «Покраска клеёного бруса со шлифовкой» в разделе (место — сортировкой
    в базе, сразу после подбора цвета), у неё переключатель «Укрывная / Лессирующая» и цена по площади
    фасада, отмеченная — гасит предупреждение о лессирующем составе, пока
    палитра не нажата, как у каркаса.

    python3 check_paint_order.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
КБ = """{ product: 'glulam', option_id: 'kb_p17', section: 'paint', name: 'Покраска клеёного бруса со шлифовкой (укрывная краска Sikkens, Zobel или аналоги)',
  included: false, price: null, status: 'formula', sort: 745,
  formula: { coef: 2300, mult: 1.1, areaSrc: 'paint', comment: '', areaMult: 1.25, addonInside: 10000, defaultMargin: 0.3, translucentOption: true } }"""
ПОРЯДОК = """() => [...document.querySelectorAll('#sec_opts_paint .opt-item')].filter(э => э.getClientRects().length)
  .map(э => (э.id || '').replace(/^lbl_/, ''))"""


def прогон(бр, порт, шир, выс):
    н = f"[{шир}]"
    стр = бр.new_page(viewport={"width": шир, "height": выс})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    порядок = стр.evaluate(ПОРЯДОК)
    ждём = ["p1", "p15", "p16", "p13", "p14", "p18"]
    живые = [х for х in порядок if х in ждём + ["p17"]]
    if живые != ждём:
        НАХОДКИ.append(f"{н} каркас: порядок покраски {живые}, ждали {ждём}")
    # Выгрузка — те же условия, что в _doExcelExport.
    в = стр.evaluate("""() => ({ снята: ОПЦИИ_СНЯТЫ.has('p17'),
      калькулятор: OPTIONS.filter(o => o.status === 'formula' && o.formula && !опцияСнята(o)).map(o => o.id),
      // С (10) снятость спрашивается у опцияСнята(): она знает и строки бруса,
      // общие со снятой строкой каркаса.
      код: String(_doExcelExport).includes("опцияСнята(opt) ? 'снята'") && String(_doExcelExport).includes("!опцияСнята(o)")
        && опцияСнята(getOpt('p17')) })""")
    if not в["снята"] or "p17" in в["калькулятор"] or not в["код"]:
        НАХОДКИ.append(f"{н} выгрузка: {в}")
    # Сохранённый расчёт с покраской клеёного бруса — строка видна.
    стр.evaluate("() => { checkedOptions.p17 = true; renderOptionSections(); calc(); }"); стр.wait_for_timeout(400)
    if "p17" not in стр.evaluate(ПОРЯДОК):
        НАХОДКИ.append(f"{н} каркас: отмеченная в сохранённом расчёте покраска клеёного бруса не видна")
    стр.evaluate("() => { checkedOptions.p17 = false; renderOptionSections(); calc(); }")
    # Брус.
    стр.evaluate("async () => { window.__ТАБЛИЦЫ.pricing_options = window.__ТАБЛИЦЫ.pricing_options || []; window.__ТАБЛИЦЫ.pricing_options.push(" + КБ + ");"
                 " await switchTech('glulam'); await new Promise(r => setTimeout(r, 1500)); selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }")
    б = стр.evaluate("""() => { const о = getOpt('kb_p17'); if (!о) return null;
      const ряд = [...document.querySelectorAll('#sec_opts_paint .opt-item')].filter(э => э.getClientRects().length).map(э => (э.id || '').replace(/^lbl_/, ''));
      kbAreas.fasad = 120; renderOptionSections(); calc();
      const стр = document.getElementById('lbl_kb_p17');
      return { ряд, цена: getOptPrice(о), переключатель: !!(стр && стр.querySelector('.translucent-toggle, .opt-transl, [data-transl], .paint-type-toggle, .seg')) || /Лессирующ/.test(стр ? стр.textContent : '') }; }""")
    if not б:
        НАХОДКИ.append(f"{н} брус: опции покраски клеёного бруса нет")
    else:
        # Место в списке у бруса задаёт сортировка в базе (745 — между подбором
        # цвета 740 и укрывной Tikkurila 750); в заглушке других строк покраски нет.
        if "kb_p17" not in б["ряд"]:
            НАХОДКИ.append(f"{н} брус: покраски клеёного бруса нет в разделе: {б['ряд']}")
        if not б["цена"] or not б["переключатель"]:
            НАХОДКИ.append(f"{н} брус: нет цены по площади фасада или переключателя состава: {б}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 1440, 900)
            прогон(бр, порт, 390, 844)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: каркас — подбор цвета, заводская покраска, потом ручная; покраски клеёного бруса в каркасе нет "
          "(в сохранённом расчёте видна), в выгрузке она «снята» и вне калькулятора опций; брус — покраска клеёного "
          "бруса в разделе, с ценой по фасаду и выбором состава — на 1440 и 390.")


if __name__ == "__main__":
    главная()
