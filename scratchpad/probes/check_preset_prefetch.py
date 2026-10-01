#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Сводка» и «Журнал» мини-окна грузятся сразу при открытии пресета.

Константин 30.09.2026, снимком вкладки «Сводка» с «Сводка загружается…»:
«когда открываю пресет, сразу прогружай в мини-окне вкладки Сводка и Журнал.
Долго грузятся всегда».

Проба на 390 и 1440 (ответ базы задержан на 1,5 с) держит:
  • свой пресет открыт, мини-окно не раскрывали — через несколько секунд
    журнал и сводка уже в памяти;
  • вкладки «Журнал» и «Сводка», открытые после этого, сразу со списком и
    итогом — без полоски «загружается»;
  • обе вкладки берут события пресета одним запросом к базе, а не двумя;
  • правка, сделанная после подгрузки, появляется в «Журнале» при первом
    открытии вкладки — подгруженное обновляется тихо, без полоски;
  • то же у общего пресета коллеги, открытого из «Общих».

    python3 check_preset_prefetch.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ПОДМЕНА = """(код) => {
  const я = _sbUser.id, т = Date.now();
  window.__событияПробы = [];
  for (let и = 0; и < 8; и++) window.__событияПробы.push({ id: 'п' + и, user_id: я, event_type: и % 2 ? 'print' : 'option_added',
    created_at: new Date(т - (и + 1) * 3600000).toISOString(), total_price: 3200000 + и * 1000,
    details: { presetCode: код, preset: 'Проба', rows: [{ k: 'Опция', b: 'Полок из липы' }] } });
  window.__вызововСобытий = 0;
  if (!window.__былRpc) window.__былRpc = _sb.rpc.bind(_sb);
  _sb.rpc = (имя, а) => {
    if (имя !== 'preset_events') return window.__былRpc(имя, а);
    window.__вызововСобытий++;
    const нужные = window.__событияПробы.map(с => Object.assign({}, с, { details: Object.assign({}, с.details, { presetCode: String(а.p_code) }) }));
    return new Promise(r => setTimeout(() => r({ data: нужные, error: null }), 1500));
  };
  _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 };
  _сводкаПресета = { код: '', данные: null, ошибка: '', грузится: false, когда: 0 };
  if (typeof _событияПресета !== 'undefined') _событияПресета.clear();
  if (typeof _пкПодгрузкаКод !== 'undefined') _пкПодгрузкаКод = '';
}"""

СОСТ = """(код) => ({ журнал: _журналПресета.код === код && !!_журналПресета.события,
  сводка: _сводкаПресета.код === код && !!_сводкаПресета.данные, вызовов: window.__вызововСобытий,
  открыто: document.getElementById('presetChipCard').classList.contains('show'), режим: _значокРежим })"""

ВКЛАДКА = """(в) => { const п = document.querySelector('#presetChipCard #pcPane-' + в);
  return { ждёт: !!(п && п.querySelector('.pc-wait')), текст: п ? п.innerText.replace(/\\s+/g, ' ').trim().slice(0, 120) : '' }; }"""


def закрыть(стр):
    if стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.evaluate("() => закрытьКарточкуЗначка()")
    стр.wait_for_timeout(200)


def проверить(стр, н, код, что):
    стр.wait_for_timeout(4200)
    с = стр.evaluate(СОСТ, код)
    if с["открыто"]:
        НАХОДКИ.append(f"{н} {что}: мини-окно открылось само — проба ждёт закрытое")
    if not с["журнал"] or not с["сводка"]:
        НАХОДКИ.append(f"{н} {что}: мини-окно не раскрывали, а журнал {'в памяти' if с['журнал'] else 'не загружен'}, "
                       f"сводка {'в памяти' if с['сводка'] else 'не загружена'} (режим «{с['режим']}»)")
    if с["вызовов"] != 1:
        НАХОДКИ.append(f"{н} {что}: событий пресета запрошено {с['вызовов']} раз, ждали один запрос на обе вкладки")
    # Правка после подгрузки — вкладка должна её показать.
    стр.evaluate("""() => window.__событияПробы.unshift({ id: 'п-новая', user_id: _sbUser.id, event_type: 'print',
      created_at: new Date().toISOString(), total_price: 3300000, details: { presetCode: '', preset: 'Проба', rows: [{ k: 'Лист', b: 'Метка-новой-правки' }] } })""")
    к.открыть(стр)
    for в, имя in (("l", "Журнал"), ("s", "Сводка")):
        стр.locator(f"#pcTab-{в}").click(); стр.wait_for_timeout(120)
        т = стр.evaluate(ВКЛАДКА, в)
        if т["ждёт"] or "загружается" in т["текст"]:
            НАХОДКИ.append(f"{н} {что}: вкладка «{имя}» открылась с загрузкой: «{т['текст'][:70]}»")
    стр.locator("#pcTab-l").click(); стр.wait_for_timeout(2200)
    т = стр.evaluate(ВКЛАДКА, "l")
    if "Метка-новой-правки" not in стр.evaluate("() => document.querySelector('#presetChipCard #pcPane-l').innerText"):
        НАХОДКИ.append(f"{н} {что}: правка после подгрузки не появилась в «Журнале»: «{т['текст'][:90]}»")
    return с


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(СоШрифтами(бр), порт, ш, в, False)
    ид = стр.evaluate("() => activePresetId")
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && String(p.shortCode || p.sharedId || ''); }")
    if not ид or not код:
        НАХОДКИ.append(f"{н} пресету не выдан код"); стр.close(); return
    # 1. Свой пресет.
    закрыть(стр)
    стр.evaluate(ПОДМЕНА, код)
    стр.evaluate("(ид) => loadPreset(ид)", ид)
    закрыть(стр)
    проверить(стр, н, код, "свой пресет")
    стр.screenshot(path=str(м.СНИМКИ / f"prefetch-{ш}.png"))
    # 2. Общий пресет коллеги.
    закрыть(стр)
    стр.evaluate(ПОДМЕНА, "555666")
    стр.evaluate("""() => { _sharedPresets.push({ short_code: '555666', id: '555666', name: 'Баня «Бремен» 6×6', author_name: 'Павел Волков',
      author_id: 'u-другой', is_public: true, visibility: 'public', locked: true, created_at: '2026-09-22T13:05:00Z', updated_at: '2026-09-22T13:05:00Z',
      state: { version: 1, manager: '', client: '' } }); openSharedPreset('555666'); }""")
    стр.wait_for_timeout(300)
    закрыть(стр)
    проверить(стр, н, "555666", "общий пресет коллеги")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                прогон(бр, порт, ш, в)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: при открытии пресета журнал и сводка мини-окна грузятся сами, одним запросом событий; "
          "вкладки открываются сразу с содержимым и тихо подтягивают правку, сделанную после подгрузки, — у своего пресета и у общего коллеги, на 390 и 1440.")


if __name__ == "__main__":
    главная()
