#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Свой опубликованный пресет: «Мои» и «Общие» — одни данные.

Константин 27.09.2026: «пресеты опубликованные в Моих и Общих в одном
аккаунте должны быть синхронны полностью. Если я нажимаю опубликованный
пресет из вкладки «Мои» … все изменения в нём должны отразиться и в
публичном. И наоборот, когда редактирую публичный с открытым замком (я или
кто-то), меняется основной. … если открыт замок в публичном, то в «Моих»
загрузить и редактировать нельзя. … Когда загружаю публичный мой пресет из
моих — плашки как при редактировании общего быть не должно».

Проба на 390 и 1440 держит:
  1. замок закрыт: пресет грузится из «Моих» без полоски общего пресета,
     правка на экране уходит в общую копию через save_own_preset_link;
  2. замок открыт: «Загрузить» в «Моих» приглушена, загрузка отказывает
     словами, пресет не становится активным;
  3. пресет открыт из «Моих» и замок открыли — правка на экране не проходит,
     автосохранение молчит;
  4. правку другого человека в общей копии «Мои» забирают себе — в память
     страницы и в строку presets;
  5. закрыли замок — на экран ложится то, что направили в «Общих»;
  6. загрузка из «Моих» забирает ушедшую вперёд общую копию;
  7. при медленной базе загрузка не ждёт сверки: пресет на экране сразу, а
     ушедшая вперёд копия ложится следом (27.09.2026: «загрузка стала
     подтормаживать»).

    python3 check_own_shared_sync.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ПОДГОТОВКА = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle('blank', false);
  selectProjectOption(0); await ждать(700);
  const снимок = collectState();
  window.__тосты = []; window.showToast = т => window.__тосты.push(String(т));
  window.__rpcСвоё = [];
  window.__RPC.save_own_preset_link = а => {
    window.__rpcСвоё.push(а);
    const с = (window.__ТАБЛИЦЫ.preset_links || []).find(r => r.short_code === а.p_code && r.author_id === _sbUser.id);
    if (!с) return false;
    Object.assign(с, { state: а.p_state, spec_state: а.p_spec, requisites: а.p_req, discount: а.p_disc, payment_plan: а.p_plan,
      updated_at: new Date().toISOString(), last_edited_by: _sbUser.id });
    return true;
  };
  window.__RPC.set_preset_lock = а => { const с = window.__ТАБЛИЦЫ.preset_links.find(r => r.short_code === а.p_code); if (с) с.locked = а.p_locked; return true; };
  const давно = '2026-09-20T10:00:00.000Z';
  const строка = { short_code: '111111', id: '111111', preset_id: 'p1', author_id: _sbUser.id, author_name: 'Проба', name: 'Свой опубликованный',
    state: снимок, ...splitStateToGranular(снимок), is_public: true, visibility: 'public', locked: true,
    created_at: давно, updated_at: давно, last_edited_by: _sbUser.id };
  window.__ТАБЛИЦЫ.preset_links = [JSON.parse(JSON.stringify(строка))];
  window.__ТАБЛИЦЫ.presets = [{ id: 'p1', user_id: _sbUser.id, name: 'Свой опубликованный', state: снимок, updated_at: давно }];
  saveAllPresets({ p1: { id: 'p1', name: 'Свой опубликованный', state: JSON.parse(JSON.stringify(снимок)), savedAt: давно,
                         shortCode: '111111', sharedId: '111111', publishedAs: 'public' } });
  _sharedPresets.length = 0; _sharedPresets.push(JSON.parse(JSON.stringify(строка)));
  try { _общиеЗагружены = true; } catch (e) {}
  setActivePreset(null);
  return true;
}"""

# Из разных разделов и без взаимных запретов: соседние опции одного раздела
# (кровля, например) исключают друг друга, и вторая снималась бы первой.
ОПЦИИ = """() => {
  const св = [...document.querySelectorAll('.opt-item[id^="lbl_"]')].filter(e => e.offsetWidth && !e.dataset.blocked)
    .map(e => ({ id: e.id.slice(4), разд: (e.closest('[id^="list_"]') || {}).id })).filter(x => !checkedOptions[x.id]);
  const запрет = (а, б) => MUTUAL_EXCLUSIONS.some(r => (r.triggers.includes(а) && r.excludes.includes(б)) || (r.triggers.includes(б) && r.excludes.includes(а)));
  for (const а of св) for (const б of св) if (а.разд !== б.разд && !запрет(а.id, б.id)) return [а.id, б.id];
  return св.slice(0, 2).map(x => x.id);
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                стр.evaluate(ПОДГОТОВКА)
                # 1. замок закрыт — загрузка из «Моих», без полоски, правка уходит в общую копию
                стр.evaluate("async () => { await loadPreset('p1'); await new Promise(r => setTimeout(r, 2300)); }")
                р = стр.evaluate("""() => { const п = document.getElementById('sharedModeIndicator');
                  return { активный: activePresetId, общий: _activeSharedCode, полоска: !!(п && п.offsetWidth && getComputedStyle(п).display !== 'none'),
                           закрыт: замокПресетаЗакрыт() }; }""")
                if р["активный"] != "p1" or р["общий"] or р["полоска"] or р["закрыт"]:
                    плохо(f"{н} 1: загрузка из «Моих» под замком: {р} — ждали активный p1 без полоски и без запрета правки")
                оп = стр.evaluate(ОПЦИИ)
                if not оп:
                    плохо(f"{н} нечего переключать"); стр.close(); continue
                стр.locator(f'#lbl_{оп[0]}').click(); стр.wait_for_timeout(2600)
                р = стр.evaluate(f"""() => {{ const с = window.__ТАБЛИЦЫ.preset_links[0];
                  return {{ вызовов: window.__rpcСвоё.length, код: (window.__rpcСвоё.slice(-1)[0] || {{}}).p_code,
                           вКопии: !!(с.spec_state && с.spec_state.checkedOptions && с.spec_state.checkedOptions['{оп[0]}']),
                           вСтейте: !!(с.state && с.state.checkedOptions && с.state.checkedOptions['{оп[0]}']) }}; }}""")
                if not р["вызовов"] or р["код"] != "111111" or not (р["вКопии"] and р["вСтейте"]):
                    плохо(f"{н} 1: правка из «Моих» не ушла в общую копию под замком: {р}")
                # 3. открыли замок, пока пресет на экране из «Моих» — правка не проходит
                стр.evaluate("() => { window.__rpcСвоё.length = 0; window.__тосты.length = 0; _sharedPresets[0].locked = false; window.__ТАБЛИЦЫ.preset_links[0].locked = false; }")
                до = стр.evaluate(f"() => !!checkedOptions['{оп[1]}']")
                стр.locator(f'#lbl_{оп[1]}').click(); стр.wait_for_timeout(2600)
                р = стр.evaluate(f"() => ({{ стало: !!checkedOptions['{оп[1]}'], вызовов: window.__rpcСвоё.length, тосты: window.__тосты.slice() }})")
                if р["стало"] != до or р["вызовов"]:
                    плохо(f"{н} 3: при открытом замке правка из «Моих» прошла: опция {до}→{р['стало']}, записей {р['вызовов']}")
                if not any("Общих" in т for т in р["тосты"]):
                    плохо(f"{н} 3: отказ в правке не объяснён словами: {р['тосты']}")
                # 2. замок открыт — «Загрузить» приглушена, загрузка отказывает
                стр.evaluate("async () => { setActivePreset(null); window.__тосты.length = 0; openPresetPanel(); await new Promise(r => setTimeout(r, 300)); switchPresetTab('my'); renderPresetList(); }")
                р = стр.evaluate("""async () => { const к = document.querySelector('#presetList .pcard[data-pid="p1"] .pcard-use');
                  const выкл = к && к.getAttribute('aria-disabled') === 'true', вид = к ? getComputedStyle(к).opacity : null;
                  await loadPreset('p1'); await new Promise(r => setTimeout(r, 200));
                  return { выкл, вид, активный: activePresetId, тосты: window.__тосты.slice() }; }""")
                if not р["выкл"] or float(р["вид"] or 1) > 0.6:
                    плохо(f"{н} 2: «Загрузить» при открытом замке не приглушена: {р}")
                if р["активный"] == "p1" or not any("Замок открыт" in т for т in р["тосты"]):
                    плохо(f"{н} 2: при открытом замке пресет загрузился из «Моих» или отказ без слов: {р}")
                стр.screenshot(path=str(СНИМКИ / f"own-sync-open-{ш}.png"))
                # 4. чужая правка в общей копии — «Мои» забирают себе
                р = стр.evaluate(f"""async () => {{
                  const с = window.__ТАБЛИЦЫ.preset_links[0];
                  const ст = JSON.parse(JSON.stringify(с.state)); ст.checkedOptions = Object.assign({{}}, ст.checkedOptions, {{ '{оп[1]}': true }});
                  Object.assign(с, {{ state: ст, ...splitStateToGranular(ст), updated_at: new Date(Date.now() + 60000).toISOString(), last_edited_by: 'u-другой' }});
                  приходОбщего({{ eventType: 'UPDATE', new: JSON.parse(JSON.stringify(с)), old: {{ short_code: '111111' }} }});
                  await new Promise(r => setTimeout(r, 600));
                  const п = loadAllPresets().p1, б = window.__ТАБЛИЦЫ.presets.find(x => x.id === 'p1');
                  return {{ вПамяти: !!п.state.checkedOptions['{оп[1]}'], вБазе: !!(б && б.state && б.state.checkedOptions && б.state.checkedOptions['{оп[1]}']) }};
                }}""")
                if not (р["вПамяти"] and р["вБазе"]):
                    плохо(f"{н} 4: чужая правка общей копии не дошла до «Моих»: {р}")
                # 5. пресет на экране из «Моих», замок закрывают — на экран ложится общая копия
                р = стр.evaluate(f"""async () => {{
                  const с = window.__ТАБЛИЦЫ.preset_links[0];
                  // экран и «Мои» — старые, копия ушла вперёд
                  const п = loadAllPresets(); const старое = JSON.parse(JSON.stringify(п.p1.state)); delete старое.checkedOptions['{оп[1]}'];
                  п.p1.state = старое; п.p1.savedAt = '2026-09-20T10:00:00.000Z'; saveAllPresets(п);
                  setActivePreset('p1'); _идётВосстановление++; restoreState(старое); await new Promise(r => setTimeout(r, 2200)); _идётВосстановление--;
                  const ст = JSON.parse(JSON.stringify(с.state)); ст.checkedOptions['{оп[1]}'] = true;
                  Object.assign(с, {{ state: ст, ...splitStateToGranular(ст), updated_at: new Date(Date.now() + 120000).toISOString(), last_edited_by: 'u-другой' }});
                  _sharedPresets[0].locked = false; с.locked = false;
                  const было = !!checkedOptions['{оп[1]}'];
                  await togglePresetLock('111111'); await new Promise(r => setTimeout(r, 2600));
                  return {{ было, стало: !!checkedOptions['{оп[1]}'], закрыт: _sharedPresets[0].locked, правкаЗдесь: !замокПресетаЗакрыт() }};
                }}""")
                if р["было"] or not р["стало"] or not р["закрыт"] or not р["правкаЗдесь"]:
                    плохо(f"{н} 5: закрытый замок не положил на экран общую копию или не вернул правку: {р}")
                # 6. загрузка из «Моих» забирает ушедшую вперёд копию
                р = стр.evaluate(f"""async () => {{
                  setActivePreset(null);
                  const с = window.__ТАБЛИЦЫ.preset_links[0];
                  const ст = JSON.parse(JSON.stringify(с.state)); ст.checkedOptions['{оп[0]}'] = false;
                  Object.assign(с, {{ state: ст, ...splitStateToGranular(ст), updated_at: new Date(Date.now() + 300000).toISOString(), last_edited_by: 'u-другой', locked: true }});
                  _sharedPresets[0].locked = true;
                  await loadPreset('p1'); await new Promise(r => setTimeout(r, 2300));
                  return {{ активный: activePresetId, опция: !!checkedOptions['{оп[0]}'] }};
                }}""")
                if р["активный"] != "p1" or р["опция"]:
                    плохо(f"{н} 6: загрузка из «Моих» не забрала общую копию: {р}")
                # 7. медленная база — загрузка не ждёт сверки (27.09.2026: «загрузка стала подтормаживать»)
                р = стр.evaluate(f"""async () => {{
                  setActivePreset(null);
                  const с = window.__ТАБЛИЦЫ.preset_links[0];
                  const ст = JSON.parse(JSON.stringify(с.state)); ст.checkedOptions['{оп[0]}'] = true;
                  Object.assign(с, {{ state: ст, ...splitStateToGranular(ст), updated_at: new Date(Date.now() + 600000).toISOString(), last_edited_by: 'u-другой', locked: true }});
                  delete _sharedPresets[0].updated_at;
                  const был = _sb.from.bind(_sb);
                  _sb.from = т => {{ const з = был(т); if (т !== 'preset_links') return з;
                    const t = з.then.bind(з); з.then = (ok, err) => new Promise(r => setTimeout(r, 3000)).then(() => t(ok, err)); return з; }};
                  const t0 = performance.now();
                  loadPreset('p1');
                  await new Promise(r => setTimeout(r, 50));
                  const сразу = {{ активный: activePresetId, мс: Math.round(performance.now() - t0) }};
                  await new Promise(r => setTimeout(r, 5800));
                  _sb.from = был;
                  return {{ сразу, потом: !!checkedOptions['{оп[0]}'] }};
                }}""")
                if р["сразу"]["активный"] != "p1":
                    плохо(f"{н} 7: при медленной базе загрузка ждёт сверки: через 50 мс активный {р['сразу']}")
                if not р["потом"]:
                    плохо(f"{н} 7: сверка в фоне не положила ушедшую вперёд копию на экран")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: свой опубликованный — под замком правится в «Моих» и уходит в общую копию, без полоски; при открытом "
          "замке в «Моих» не грузится и не правится; правки общей копии доходят до «Моих», закрытый замок кладёт их "
          "на экран, загрузка забирает ушедшую вперёд копию — на 390 и 1440.")


if __name__ == "__main__":
    главная()
