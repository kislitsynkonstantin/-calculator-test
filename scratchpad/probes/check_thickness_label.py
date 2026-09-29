#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Смена толщины утепления в журналах подписана «Стены, пол и потолок».

Константин 30.09.2026, снимком журнала мини-окна со строкой «Толщина: 150 мм →
200 мм»: «в таких событиях скорее всего „пола и потолка“ — это надо
дописывать». Кнопки толщины меняют базу всего строения — и «Утепление
наружных стен», и «Утепление пола и потолка» разом, — поэтому подпись
называет все три.

Проба держит:
  • нажатие на кнопку толщины пишет в журнал ключ «Стены, пол и потолок»;
  • старая запись с ключом «Толщина» в журнале мини-окна показана с новой
    подписью, как и новая;
  • в полном журнале действий под стрелкой та же подпись, слова «Толщина»
    отдельной подписью нет.

    python3 check_thickness_label.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []


def прогон(бр, порт, шир, выс):
    н = f"[{шир}]"
    стр, ошибки = к.начать(бр, порт, шир, выс, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        НАХОДКИ.append(f"{н} пресету не выдан код"); стр.close(); return
    # Новая запись — нажатием на кнопку толщины.
    стр.evaluate("() => { window.__ТАБЛИЦЫ.events = []; }")
    стр.locator(".thick-btn").nth(2).click(); стр.wait_for_timeout(700)
    ключ = стр.evaluate("""() => { const е = (window.__ТАБЛИЦЫ.events || []).find(x => x.event_type === 'thickness_changed');
      return е ? ((е.details || {}).rows || [])[0].k : null; }""")
    if ключ != "Стены, пол и потолок":
        НАХОДКИ.append(f"{н} кнопка толщины пишет ключ «{ключ}»")
    # Старая запись — с ключом «Толщина», на день раньше.
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ, я = _sbUser.id;
      т.events.forEach(е => { if (!е.created_at) е.created_at = new Date().toISOString(); if (е.details && !е.details.presetCode) е.details.presetCode = код; });
      т.events.push({ id: 'стар', user_id: я, event_type: 'thickness_changed', created_at: new Date(Date.now() - 86400000).toISOString(), total_price: 3000000,
        project_name: 'Проба', details: { presetCode: код, preset: 'Проба', rows: [{ k: 'Толщина', a: '150 мм', b: '200 мм' }, { k: 'Итог', a: '3 000 000 ₽', b: '3 200 000 ₽' }] } });
      _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 }; }""", код)
    к.открыть(стр); к.вкладка(стр, "l"); стр.wait_for_timeout(700)
    т = стр.evaluate("() => (document.querySelector('#presetChipCard .pc-lg') || {}).innerText || ''")
    if т.count("Стены, пол и потолок: 150 мм → 200 мм") < 2 or "Толщина:" in т:
        НАХОДКИ.append(f"{н} журнал мини-окна: «{т[:200]}»")
    # Полный журнал действий, отбор по пресету, строки раскрыты.
    стр.evaluate("() => { закрытьКарточкуЗначка(); _alПодробно = true; _alПресет = String(" + repr(код) + "); _alПериод = 'всё'; _alПериодРазовый = true; openActionLog(); }")
    стр.wait_for_timeout(1500)
    # Подписи строк под стрелкой — в разметке и у свёрнутой строки.
    ж = стр.evaluate("() => [...document.querySelectorAll('#alFeed .al-row .al-dk')].map(э => э.textContent.trim())")
    if ж.count("Стены, пол и потолок") < 2 or "Толщина" in ж:
        НАХОДКИ.append(f"{н} полный журнал: подписи строк {ж}")
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
    print("Чисто: смена толщины пишется и показывается как «Стены, пол и потолок» — и новая, и старая запись, "
          "в журнале мини-окна и в полном журнале действий, на 1440 и 390.")


if __name__ == "__main__":
    главная()
