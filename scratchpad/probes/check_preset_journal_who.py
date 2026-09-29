#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал мини-окна: кто сделал — и что открытие правкой не пишется.

Константин 29.09.2026, снимком журнала мини-окна у общего пресета менеджера:
«в пресете менеджера на его правки пишет мне „Вы“ — писать просто „Максим Г.“,
а у него „Вы“». Разбор показал две вещи. Подпись была верной по записи: эти
строки и правда записаны от администратора. Но записаны зря — открытие чужого
пресета раскладывало его толщину утепления и реквизиты, и журнал писал это
правками того, кто открыл: «Толщина утепления изменена 150 → 200»,
«Реквизиты заполнены».

Проба на 390 держит:
  • у администратора в журнале мини-окна свои строки — «Вы», чужие — «Имя Ф.»;
  • у менеджера, если в ленте есть чужие действия, так же; если только свои —
    подписи нет, как прежде;
  • открытие пресета с другой толщиной и заполненными реквизитами не пишет ни
    «Толщина утепления изменена», ни «Реквизиты заполнены»;
  • нажатие на кнопку толщины пишет её одной строкой — журнал не онемел.

    python3 check_preset_journal_who.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ЛЕНТА = """(роль) => { window._sbProfile = Object.assign({}, window._sbProfile || {}, { role: роль });
  const о = пресетКарточки(), я = _sbUser && _sbUser.id, д = Date.now();
  _alИмена['u-максим'] = 'Максим Григорьев';
  const с = (ид, кто, мин, тип) => ({ id: ид, created_at: new Date(д - мин * 60000).toISOString(), event_type: тип, user_id: кто,
    project_name: 'Проба', details: { rows: [{ k: 'Скидка', a: '0 %', b: '3 %' }], presetCode: о.код } });
  return { я, о: о.код }; }"""

ПОДПИСИ = """() => [...document.querySelectorAll('#presetChipCard .pc-lg-w')].map(э => { const b = э.querySelector('b'); return b ? b.textContent : ''; })"""


def лента(стр, роль, свои_и_чужие):
    стр.evaluate(ЛЕНТА, роль)
    стр.evaluate("""(оба) => { const о = пресетКарточки(), я = _sbUser && _sbUser.id, д = Date.now();
      const с = (ид, кто, мин) => ({ id: ид, created_at: new Date(д - мин * 60000).toISOString(), event_type: 'discount_changed', user_id: кто,
        project_name: 'Проба', details: { rows: [{ k: 'Скидка', a: '0 %', b: '3 %' }], presetCode: о.код } });
      const s = оба ? [с('a', 'u-максим', 5), с('b', я, 10)] : [с('b', я, 10), с('c', я, 20)];
      _журналПресета = { код: о.код, события: s, ошибка: '', грузится: false, когда: Date.now() };
      _пкВкладка = 'l'; заполнитьКарточкуЗначка(); }""", свои_и_чужие)
    стр.wait_for_timeout(200)
    return стр.evaluate(ПОДПИСИ)


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    if not стр.evaluate("() => activePresetId"):
        НАХОДКИ.append(f"{н} пресет не сохранился"); стр.close(); return
    к.открыть(стр); стр.wait_for_timeout(300)
    п = лента(стр, "admin", True)
    if п != ["Максим Г.", "Вы"]:
        НАХОДКИ.append(f"{н} администратор: подписи {п}, ждали ['Максим Г.', 'Вы']")
    п = лента(стр, "manager", True)
    if п != ["Максим Г.", "Вы"]:
        НАХОДКИ.append(f"{н} менеджер с чужими действиями в ленте: подписи {п}, ждали ['Максим Г.', 'Вы']")
    п = лента(стр, "manager", False)
    if any(п):
        НАХОДКИ.append(f"{н} менеджер, в ленте только свои: подписи {п}, ждали без подписи")
    стр.evaluate("() => закрытьКарточкуЗначка()")
    # ── открытие пресета с другой толщиной и заполненными реквизитами ──
    стр.evaluate("""() => { const все = loadAllPresets(), свой = все[activePresetId];
      const st = JSON.parse(JSON.stringify(свой.state || {}));
      st.thickness = (currentThickness === 2 ? 1 : 2); st.manager = 'Проба Менеджер'; st.client = 'Проба Заказчик'; st.contractNumber = '123'; st.contractDate = '2026-09-29';
      все['preset_чужой'] = { id: 'preset_чужой', name: 'Пресет с реквизитами', savedAt: new Date().toISOString(), state: st };
      saveAllPresets(все);
      ['managerName', 'clientName', 'contractNumber', 'contractDate'].forEach(ид => { const э = document.getElementById(ид); if (э) э.value = ''; });
      al2РеквизитыСброс(); window.__ТАБЛИЦЫ.events = []; loadPreset('preset_чужой'); }""")
    стр.wait_for_timeout(3500)
    виды = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).map(e => e.event_type)")
    if "thickness_changed" in виды:
        НАХОДКИ.append(f"{н} открытие пресета с другой толщиной записано как смена толщины: {виды}")
    if "requisites_filled" in виды:
        НАХОДКИ.append(f"{н} открытие пресета с реквизитами записано как «Реквизиты заполнены»: {виды}")
    if стр.evaluate("() => document.getElementById('managerName').value") != "Проба Менеджер":
        НАХОДКИ.append(f"{н} реквизиты пресета не разложились — проверка вслепую")
    # ── кнопка толщины ──
    стр.evaluate("() => { window.__ТАБЛИЦЫ.events = []; }")
    стр.locator(".thick-btn:not(.active)").first.click(); стр.wait_for_timeout(800)
    виды = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).map(e => e.event_type)")
    if виды.count("thickness_changed") != 1:
        НАХОДКИ.append(f"{н} нажатие на кнопку толщины записано {виды.count('thickness_changed')} раз вместо одного: {виды}")
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
    print("Чисто: в журнале мини-окна свои — «Вы», чужие — «Имя Ф.», у менеджера только со своими — без подписи; "
          "открытие пресета толщину и реквизиты правкой не пишет, кнопка толщины пишет одной строкой.")


if __name__ == "__main__":
    главная()
