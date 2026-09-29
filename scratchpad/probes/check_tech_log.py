#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Технология переключена» — только когда её переключили.

Константин 29.09.2026, снимком журнала мини-окна брусового пресета: три строки
«Технология переключена: Каркас → Клеёный брус, итог 3 086 292 ₽ → 0 ₽» —
«что значит переключение технологии? Пресет же может быть только в одной
технологии сделан». Это было открытие брусового пресета из каркаса: пресет
сам переключает технологию, а `switchTech` писал каждое переключение в журнал
и цеплял к нему код открываемого пресета.

Проба на 390 держит:
  • открытие пресета другой технологии не пишет «Технология переключена»;
  • выбор в поле «Технология» пишет её одной строкой — журнал не онемел;
  • журнал пресета и отбор по пресету не берут прежние такие записи:
    записанная в базу смена технологии с кодом пресета во вкладке «Журнал»
    мини-окна не видна, а соседняя правка того же пресета видна.

    python3 check_tech_log.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СМЕНЫ = "() => (window.__ТАБЛИЦЫ.events || []).filter(e => e.event_type === 'tech_changed').map(e => ({ код: (e.details || {}).presetCode || '', ряды: (e.details || {}).rows || [] }))"


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        НАХОДКИ.append(f"{н} пресету не выдан код — дальше проверять нечего"); стр.close(); return
    # ── прежние записи в журнале пресета ──
    if "tech_changed" in стр.evaluate("() => видыЖурналаПресета()"):
        НАХОДКИ.append(f"{н} журнал пресета и отбор по пресету берут смену технологии")
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ, д = Date.now();
      т.events = [
        { id: 't1', user_id: 'u-проба', event_type: 'tech_changed', created_at: new Date(д - 3600e3).toISOString(), project_name: 'Проба',
          details: { presetCode: код, rows: [{ k: 'Технология', a: 'Каркас', b: 'Клеёный брус' }, { k: 'Итог', a: '3 086 292 ₽', b: '0 ₽' }] } },
        { id: 't2', user_id: 'u-проба', event_type: 'discount_changed', created_at: new Date(д - 7200e3).toISOString(), project_name: 'Проба',
          details: { presetCode: код, rows: [{ k: 'Скидка', a: '0 %', b: '3 %' }] } }];
      _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 }; }""", код)
    к.открыть(стр); стр.wait_for_timeout(300)
    стр.evaluate("() => { _пкВкладка = 'l'; заполнитьКарточкуЗначка(); загрузитьЖурналПресета(true); }")
    стр.wait_for_timeout(1500)
    текст = стр.evaluate("() => (document.querySelector('#presetChipCard .pc-pane.on') || {}).innerText || ''")
    if "Скидка" not in текст:
        НАХОДКИ.append(f"{н} соседняя правка пресета не видна в журнале — проверка вслепую: «{текст[:120]}»")
    if "Технология" in текст:
        НАХОДКИ.append(f"{н} прежняя запись «Технология переключена» видна в журнале пресета")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    # Цены бруса в заглушке не нужны: проба смотрит на журнал, а не на расчёт.
    стр.evaluate("""() => { window.glulamAllowed = () => true; window.loadPricing = async () => true; window.__ТАБЛИЦЫ.events = []; }""")
    # ── открытие брусового пресета из каркаса ──
    стр.evaluate("""() => { const все = loadAllPresets(), свой = все[activePresetId];
      const st = JSON.parse(JSON.stringify(свой.state || {})); st.tech = 'glulam';
      все['preset_брус'] = { id: 'preset_брус', name: 'Брусовый пресет', savedAt: new Date().toISOString(), state: st };
      saveAllPresets(все); loadPreset('preset_брус'); }""")
    стр.wait_for_timeout(3500)
    if стр.evaluate("() => currentTech") != "glulam":
        НАХОДКИ.append(f"{н} брусовый пресет не переключил технологию — открытие не проверено")
    смены = стр.evaluate(СМЕНЫ)
    if смены:
        НАХОДКИ.append(f"{н} открытие пресета другой технологии записано как смена технологии: {смены}")
    # ── выбор в поле «Технология» ──
    стр.evaluate("() => { window.__ТАБЛИЦЫ.events = []; selectTech('frame'); }")
    стр.wait_for_timeout(2500)
    смены = стр.evaluate(СМЕНЫ)
    if len(смены) != 1:
        НАХОДКИ.append(f"{н} выбор в поле «Технология» записан {len(смены)} раз вместо одного: {смены}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 390, 844)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: открытие пресета другой технологии смену технологии не пишет, выбор в поле «Технология» пишет одной "
          "строкой, прежние такие записи в журнал пресета не попадают.")


if __name__ == "__main__":
    главная()
