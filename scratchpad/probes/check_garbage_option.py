#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вывоз мусора: примечание, опция с количеством, глаз и проверка.

Константин 30.09.2026, снимком раздела «Доп. опции и логистика»:
  1. «Вывоз мусора убери фразу „в базовую комплектацию“» — примечание
     «Вывоз мусора не входит»;
  2. опция «Вывоз мусора (1 контейнер с грузчиками)» — 37 000 ₽, количество
     счётчиком, как у межкомнатных дверей;
  3. выбрали опцию — примечание гаснет глазом, сняли — возвращается;
  4. в проверке: опция выбрана — правка «убрать вывоз мусора» (базово его не
     предлагаем); выбрана, а примечание стоит — ещё и «убрать примечание»;
     не выбрана — ничего. У бруса та же опция — kb_e3.

Проба нажимает на строки, как менеджер, на 390 и 1440.

    python3 check_garbage_option.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СОСТ = """() => { const о = getOpt('e12'), место = SECTION_NOTES.extra.indexOf('Вывоз мусора не входит'), ключ = ключПримечания('extra', место);
  const пр = проверкаПоЧекЛисту(); const стр = document.getElementById('lbl_e12');
  return { есть: !!о, отмечена: !!checkedOptions.e12, имя: (стр && стр.querySelector('.opt-name') || {}).textContent || '',
    цена: о ? getOptPrice(о) : null, место, скрыто: hiddenNotes.has(ключ),
    старое: SECTION_NOTES.extra.some(т => /в базовую комплектацию/.test(т) && /мусор/i.test(т)),
    степпер: !!(стр && стр.querySelector('.opt-qty-stepper, .opt-qty-btn')),
    замечание: пр.замечания.some(з => /Вывоз мусора не входит/.test(з.т)),
    убрать: пр.замечания.some(з => /^Убрать вывоз мусора/.test(з.т)) }; }"""


def прогон(бр, порт, шир, выс):
    н = f"[{шир}]"
    стр = бр.new_page(viewport={"width": шир, "height": выс})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    с = стр.evaluate(СОСТ)
    if not с["есть"] or с["место"] == -1 or с["старое"]:
        НАХОДКИ.append(f"{н} опции нет или примечание не «Вывоз мусора не входит»: {с}"); стр.close(); return
    if с["отмечена"] or с["скрыто"] or с["замечание"]:
        НАХОДКИ.append(f"{н} по умолчанию: опция отмечена, примечание скрыто или есть замечание: {с}")
    # Отметить нажатием, как менеджер.
    стр.evaluate("() => document.getElementById('lbl_e12').scrollIntoView({ block: 'center' })"); стр.wait_for_timeout(200)
    стр.locator("#lbl_e12 .opt-check").click(); стр.wait_for_timeout(600)
    с = стр.evaluate(СОСТ)
    if not с["отмечена"] or not с["скрыто"] or с["цена"] != 37000 or not с["степпер"] or с["замечание"]:
        НАХОДКИ.append(f"{н} опция отмечена: {с}")
    # Базово вывоз не предлагаем: выбранный — правка «убрать» (30.09.2026).
    if not с["убрать"]:
        НАХОДКИ.append(f"{н} вывоз мусора выбран, а правки «Убрать вывоз мусора» нет: {с}")
    # Два контейнера — счётчиком.
    плюс = стр.locator("#lbl_e12 .opt-qty-btn").last
    if плюс.count():
        плюс.click(); стр.wait_for_timeout(500)
        с = стр.evaluate(СОСТ)
        if с["цена"] != 74000 or "2 контейнера с грузчиками" not in с["имя"]:
            НАХОДКИ.append(f"{н} два контейнера: {с}")
    # Менеджер вернул примечание глазом — проверка пишет замечание.
    стр.evaluate("() => { const к = ключПримечания('extra', SECTION_NOTES.extra.indexOf('Вывоз мусора не входит')); setNoteHidden(к, false); }")
    с = стр.evaluate(СОСТ)
    if not с["замечание"]:
        НАХОДКИ.append(f"{н} опция выбрана, примечание видно, а замечания нет: {с}")
    # Сняли опцию — примечание вернулось, замечания нет.
    стр.evaluate("() => { const к = ключПримечания('extra', SECTION_NOTES.extra.indexOf('Вывоз мусора не входит')); setNoteHidden(к, true); }")
    стр.locator("#lbl_e12 .opt-check").click(); стр.wait_for_timeout(600)
    с = стр.evaluate(СОСТ)
    if с["отмечена"] or с["скрыто"] or с["замечание"] or с["убрать"]:
        НАХОДКИ.append(f"{н} опцию сняли: {с}")
    # Клеёный брус: та же опция — kb_e3 (в базе прежняя строка без цены стала ею).
    б = стр.evaluate("""async () => {
      (window.__ТАБЛИЦЫ.pricing_options = window.__ТАБЛИЦЫ.pricing_options || []).push({ product: 'glulam', option_id: 'kb_e3', section: 'extra',
        name: 'Вывоз мусора (1 контейнер с грузчиками)', included: false, price: 37000, formula: null, status: null, sort: 1570 });
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 1500)); selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
      const о = getOpt('kb_e3'); if (!о) return null;
      toggleOpt('kb_e3'); await new Promise(r => setTimeout(r, 500));
      const место = SECTION_NOTES.extra.indexOf('Вывоз мусора не входит'), пр = проверкаПоЧекЛисту();
      return { счётчик: !!(о.formula && о.formula.qtyOption), отмечена: !!checkedOptions.kb_e3, место, скрыто: hiddenNotes.has(ключПримечания('extra', место)),
               убрать: пр.замечания.some(з => /^Убрать вывоз мусора/.test(з.т)) }; }""")
    if not б or not б["счётчик"] or not б["отмечена"] or б["место"] == -1 or not б["скрыто"] or not б["убрать"]:
        НАХОДКИ.append(f"{н} брус: вывоз мусора kb_e3 — {б}")
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
    print("Чисто: примечание «Вывоз мусора не входит»; опция «Вывоз мусора (1 контейнер с грузчиками)» — 37 000 ₽, "
          "счётчиком 2 контейнера — 74 000 ₽; отмеченная гасит примечание глазом, снятая возвращает; проверка пишет "
          "замечание, только когда опция выбрана, а примечание видно — на 1440 и 390.")


if __name__ == "__main__":
    главная()
