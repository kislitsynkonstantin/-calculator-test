#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресеты живут в базе; без связи — очередь в браузере, которая уходит сама.

Константин 25.09.2026: сначала «запрети сохранение пресетов локально в
браузере. Только в базу», следом — «если связи нет — пресет сохраняется в
браузер. А когда связь появляется, загружается в базу и в браузере
удаляется».

Проба держит:
  • со связью сохранение не пишет в браузер ни байта под ключом пресетов,
    строка появляется в базе, код выдаётся, «Пресет сохранён» — после ответа;
  • правка открытого пресета доходит до базы (до этой правки автосохранение
    писало только в браузер, и база держала первую версию);
  • без связи новый пресет и правка ложатся в очередь в браузере, сказано
    об этом словами; после «перезагрузки» без связи пресет в списке;
  • связь вернулась — очередь уходит в базу сама, ключ удаляется, сказано;
  • очередь не затирает в базе то, что там новее, и не воскрешает удалённое;
  • старая копия пресетов переезжает так же: чего в базе нет или что свежее —
    уходит, остальное снимается; не легло — ключ остаётся;
  • память браузера полна — со связью пресет сохраняется как обычно (до
    правки сохранение обрывалось на записи открытого пресета), без связи
    сказано, что он не сохранился;
  • пока коды не прочитаны из базы, новые номера не раздаются.

    python3 check_presets_outbox.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
КЛЮЧ = "banya_msk_presets_v1"
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


def старые(*иды):
    return {и: {"id": и, "name": "Старый " + и, "savedAt": "2026-09-01T10:00:00Z",
                "state": {"savedAt": "2026-09-01T10:00:00Z", "project": {"name": "Проба"}, "checkedOptions": {}}}
            for и in иды}


def страница(бр, порт, в_браузере, отказ=None, база=None):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    if база is not None:
        стр.add_init_script("window.__ТАБЛИЦЫ.presets = " + json.dumps(база, ensure_ascii=False) + ";")
    # Старая копия кладётся до первого сценария страницы — как у менеджера.
    стр.add_init_script(f"try {{ if (!sessionStorage.getItem('засеяно')) {{ localStorage.setItem('{КЛЮЧ}', "
                        f"{json.dumps(json.dumps(в_браузере, ensure_ascii=False), ensure_ascii=False)}); "
                        "sessionStorage.setItem('засеяно', '1'); } } catch (e) {}")
    # Нет связи — база не принимает записей пресетов, пока стоит флаг.
    стр.add_init_script("(function () { const с = window.supabase.createClient;"
        " window.supabase.createClient = function () { const к = с.apply(this, arguments); const f = к.from.bind(к);"
        " к.from = function (т) { const о = f(т); if (т === 'presets') { const u = о.upsert;"
        " о.upsert = function (в, н) { if (window.__нетСвязи) return { then: r => r({ error: { message: 'Failed to fetch' } }) };"
        " return u.call(о, в, н); }; } return о; }; return к; }; })();")
    if отказ:
        # Отказ базы для одного пресета — до первой синхронизации при входе.
        # База отказывает в записи одного пресета — на уровне заглушки, потому
        # что первая синхронизация идёт ещё до конца загрузки страницы.
        стр.add_init_script("(function () { const с = window.supabase.createClient;"
            " window.supabase.createClient = function () { const к = с.apply(this, arguments); const f = к.from.bind(к);"
            " к.from = function (т) { const о = f(т); if (т === 'presets') { const u = о.upsert;"
            " о.upsert = function (в, н) { const м = Array.isArray(в) ? в : [в];"
            f" if (м.some(x => x && x.id === '{отказ}')) return {{ then: r => r({{ error: {{ message: 'отказ' }} }}) }};"
            " return u.call(о, в, н); }; } return о; }; return к; }; })();")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none'; }""")
    return стр, ошибки


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

            # 1. Перенос и новое сохранение.
            стр, ошибки = страница(бр, порт, старые("preset_old1"))
            р = стр.evaluate(f"""async () => {{
              await sbSyncPresets(true);
              await new Promise(r => setTimeout(r, 300));
              return {{ вБазе: (window.__ТАБЛИЦЫ.presets || []).map(x => x.id),
                       ключ: localStorage.getItem('{КЛЮЧ}'), вПамяти: Object.keys(loadAllPresets()) }}; }}""")
            if "preset_old1" not in р["вБазе"]:
                плохо(f"пресет, живший только в браузере, не долит в базу: {р['вБазе']}")
            if р["ключ"] is not None:
                плохо("после переноса старая копия в браузере осталась")
            if "preset_old1" not in р["вПамяти"]:
                плохо("перенесённый пресет пропал из списка")
            print(f"  перенос: в базе {len(р['вБазе'])}, ключ {'удалён' if р['ключ'] is None else 'остался'}")
            р = стр.evaluate(f"""async () => {{
              const записи = []; const был = Storage.prototype.setItem;
              Storage.prototype.setItem = function (к, в) {{ записи.push(к); return был.call(this, к, в); }};
              selectProjectOption(0); calc();
              const код = await сохранитьНовыйПресет('Проба в базу', 'Проба в базу', collectState());
              await new Promise(r => setTimeout(r, 300));
              Storage.prototype.setItem = был;
              const ид = activePresetId;
              const тост = (document.getElementById('toastMsg') || {{}}).textContent || '';
              window._пресеты = {{}};   // «перезагрузка»: память страницы пуста
              const пусто = Object.keys(loadAllPresets()).length;
              await sbSyncPresets(true);
              return {{ записи, код, ид, тост, пусто, вБазе: (window.__ТАБЛИЦЫ.presets || []).some(x => x.id === ид),
                       вернулся: !!loadAllPresets()[ид] }}; }}""")
            if КЛЮЧ in р["записи"]:
                плохо("сохранение записало пресеты в браузер")
            if not р["вБазе"]:
                плохо("новый пресет не лёг в базу")
            if not р["код"]:
                плохо("новый пресет без кода")
            if "Пресет сохранён" not in р["тост"]:
                плохо(f"после ответа базы нет «Пресет сохранён»: {р['тост']!r}")
            if р["пусто"] != 0 or not р["вернулся"]:
                плохо(f"после «перезагрузки» пресет не вернулся из базы (пусто было {р['пусто']})")
            print(f"  сохранение: код {р['код']}, в базе — {р['вБазе']}, записей в браузер под ключом — {р['записи'].count(КЛЮЧ)}")
            # Коды не раздаются, пока не прочитаны из базы.
            н = стр.evaluate("""() => { _кодыПресетовИзБазы = false;
              const все = loadAllPresets(); все['preset_nocode'] = { id: 'preset_nocode', name: 'Без кода', state: {} }; saveAllPresets(все);
              const сколько = назначитьКодыПресетам(); _кодыПресетовИзБазы = true; return сколько; }""")
            if н:
                плохо(f"коды раздаются до чтения из базы: {н}")
            # Правка открытого пресета доходит до базы.
            р = стр.evaluate("""async () => {
              const ид = activePresetId;
              const до = JSON.stringify(window.__ТАБЛИЦЫ.presets.find(x => x.id === ид).state.discount || null);
              const п = document.getElementById('discountPctInput'); if (п) { п.value = '7'; п.dispatchEvent(new Event('input', {bubbles:true})); }
              saveToPreset(ид, true);
              await new Promise(r => setTimeout(r, 300));
              const р = window.__ТАБЛИЦЫ.presets.find(x => x.id === ид);
              return { ид, сохранено: р.state.savedAt, в_памяти: loadAllPresets()[ид].state.savedAt,
                       ключ: localStorage.getItem('%s') }; }""" % КЛЮЧ)
            if р["сохранено"] != р["в_памяти"]:
                плохо("правка открытого пресета не дошла до базы — там осталась прежняя версия")
            if р["ключ"] is not None:
                плохо("со связью правка легла в браузер")
            print(f"  правка открытого пресета: в базе {'новая' if р['сохранено'] == р['в_памяти'] else 'старая'} версия")

            # Без связи: новый пресет и правка — в очередь.
            р = стр.evaluate("""async () => {
              window.__нетСвязи = true;
              await сохранитьНовыйПресет('Без связи', 'Без связи', collectState());
              await new Promise(r => setTimeout(r, 300));
              const ид = activePresetId;
              const тост = (document.getElementById('toastMsg') || {}).textContent || '';
              await new Promise(r => setTimeout(r, 20));
              saveToPreset(ид, true);
              await new Promise(r => setTimeout(r, 300));
              const очередь = JSON.parse(localStorage.getItem('%s') || '{}');
              const последняя = loadAllPresets()[ид].state.savedAt;
              window._пресеты = undefined;   // «перезагрузка» без связи
              const после = !!loadAllPresets()[ид];
              return { ид, тост, вОчереди: !!очередь[ид], версия: очередь[ид] && очередь[ид].state.savedAt,
                       последняя, код: очередь[ид] && очередь[ид].shortCode,
                       вБазе: window.__ТАБЛИЦЫ.presets.some(x => x.id === ид), после }; }""" % КЛЮЧ)
            if not р["вОчереди"]:
                плохо("без связи пресет не лёг в браузер")
            elif р["версия"] != р["последняя"]:
                плохо("без связи правка не легла в очередь — там первая версия")
            if not р["код"]:
                плохо("в очереди пресет без кода")
            if "сохранён в браузере" not in р["тост"]:
                плохо(f"без связи не сказано, что пресет в браузере: {р['тост']!r}")
            if р["вБазе"]:
                плохо("заглушка «нет связи» пропустила запись в базу")
            if not р["после"]:
                плохо("после перезагрузки без связи пресета нет в списке")
            print(f"  без связи: в очереди — {р['вОчереди']}, код {р['код']}, после перезагрузки в списке — {р['после']}")
            офлайн = р["ид"]

            # Связь вернулась.
            р = стр.evaluate("""async () => {
              window.__нетСвязи = false;
              window.dispatchEvent(new Event('online'));
              for (let i = 0; i < 30 && localStorage.getItem('%s'); i++) await new Promise(r => setTimeout(r, 100));
              await new Promise(r => setTimeout(r, 200));
              const р = window.__ТАБЛИЦЫ.presets.find(x => x.id === '%s');
              return { ключ: localStorage.getItem('%s'), вБазе: !!р, версия: р && р.state.savedAt,
                       тост: (document.getElementById('toastMsg') || {}).textContent || '' }; }""" % (КЛЮЧ, офлайн, КЛЮЧ))
            if not р["вБазе"]:
                плохо("связь вернулась, а пресет из очереди в базу не ушёл")
            if р["ключ"] is not None:
                плохо("пресет ушёл в базу, а в браузере остался")
            if "ушёл в базу" not in р["тост"]:
                плохо(f"не сказано, что пресет ушёл в базу: {р['тост']!r}")
            print(f"  связь вернулась: в базе — {р['вБазе']}, ключ {'удалён' if р['ключ'] is None else 'остался'}")

            # Очередь не затирает новое и не воскрешает удалённое.
            р = стр.evaluate("""async () => {
              const Б = window.__ТАБЛИЦЫ.presets;
              Б.push({ id: 'p_new', user_id: 'u-проба', name: 'Новее в базе', state: { savedAt: '2026-09-20T10:00:00Z', mark: 'база' },
                       updated_at: '2026-09-20T10:00:00Z', deleted_at: null });
              Б.push({ id: 'p_del', user_id: 'u-проба', name: 'Удалён', state: {}, updated_at: '2026-09-20T10:00:00Z',
                       deleted_at: '2026-09-20T10:00:00Z' });
              localStorage.setItem('%s', JSON.stringify({
                p_new: { id: 'p_new', name: 'Старое', savedAt: '2026-09-10T10:00:00Z', state: { savedAt: '2026-09-10T10:00:00Z', mark: 'браузер' } },
                p_del: { id: 'p_del', name: 'Удалён', savedAt: '2026-09-21T10:00:00Z', state: { savedAt: '2026-09-21T10:00:00Z' } } }));
              await выгрузитьОчередь();
              return { метка: Б.find(x => x.id === 'p_new').state.mark, удалён: Б.find(x => x.id === 'p_del').deleted_at,
                       ключ: localStorage.getItem('%s') }; }""" % (КЛЮЧ, КЛЮЧ))
            if р["метка"] != "база":
                плохо("старая версия из очереди затёрла в базе более новую")
            if not р["удалён"]:
                плохо("очередь воскресила удалённый пресет")
            if р["ключ"] is not None:
                плохо("снятые с очереди записи остались в браузере")

            # Связь есть, память полна — сохранение идёт как обычно.
            р = стр.evaluate("""async () => {
              const был = Storage.prototype.setItem;
              Storage.prototype.setItem = function () { throw new DOMException('full', 'QuotaExceededError'); };
              await сохранитьНовыйПресет('Полно со связью', 'Полно со связью', collectState());
              await new Promise(r => setTimeout(r, 300));
              Storage.prototype.setItem = был;
              const ид = activePresetId;
              return { тост: (document.getElementById('toastMsg') || {}).textContent || '',
                       вБазе: window.__ТАБЛИЦЫ.presets.some(x => x.id === ид && x.name === 'Полно со связью') }; }""")
            if not р["вБазе"] or "Пресет сохранён" not in р["тост"]:
                плохо(f"при полной памяти браузера сохранение со связью не дошло до базы: {р['тост']!r}")

            # Нет связи и память полна — сказано, что не сохранился.
            т = стр.evaluate("""async () => {
              window.__нетСвязи = true; const был = Storage.prototype.setItem;
              Storage.prototype.setItem = function () { throw new DOMException('full', 'QuotaExceededError'); };
              await сохранитьНовыйПресет('Полно', 'Полно', collectState());
              await new Promise(r => setTimeout(r, 300));
              Storage.prototype.setItem = был; window.__нетСвязи = false;
              return (document.getElementById('toastMsg') || {}).textContent || ''; }""")
            if "не сохранился" not in т:
                плохо(f"при полной памяти без связи не сказано, что пресет не сохранился: {т!r}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()

            # 2. Старая копия: свежее, чем в базе, — уходит; старее — снимается.
            в_браузере = старые("preset_fresh", "preset_stale")
            в_браузере["preset_fresh"]["state"]["savedAt"] = "2026-09-24T10:00:00Z"
            в_браузере["preset_fresh"]["state"]["mark"] = "правка"
            стр, ошибки = страница(бр, порт, в_браузере, база=[
                {"id": "preset_fresh", "user_id": "u-проба", "name": "Старый preset_fresh",
                 "state": {"savedAt": "2026-09-01T10:00:00Z", "mark": "первая"},
                 "updated_at": "2026-09-01T10:05:00Z", "deleted_at": None},
                {"id": "preset_stale", "user_id": "u-проба", "name": "Старый preset_stale",
                 "state": {"savedAt": "2026-09-15T10:00:00Z", "mark": "база"},
                 "updated_at": "2026-09-15T10:00:00Z", "deleted_at": None}])
            р = стр.evaluate(f"""async () => {{ await sbSyncPresets(true);
              const Б = window.__ТАБЛИЦЫ.presets;
              return {{ ключ: localStorage.getItem('{КЛЮЧ}'),
                       свежий: Б.find(x => x.id === 'preset_fresh').state.mark,
                       старый: Б.find(x => x.id === 'preset_stale').state.mark }}; }}""")
            if р["свежий"] != "правка":
                плохо("правка из старой копии, которой нет в базе, не ушла туда")
            if р["старый"] != "база":
                плохо("старая копия затёрла в базе более новую версию")
            if р["ключ"] is not None:
                плохо("после переноса старая копия осталась в браузере")
            print(f"  старая копия: свежая правка — {р['свежий']}, более старая — {р['старый']}")
            стр.close()

            # 3. Старый пресет не лёг в базу — ключ остаётся.
            стр, ошибки = страница(бр, порт, старые("preset_keep1", "preset_fail"), отказ="preset_fail")
            р = стр.evaluate(f"""async () => {{ await sbSyncPresets(true);
              return {{ ключ: localStorage.getItem('{КЛЮЧ}') }}; }}""")
            if р["ключ"] is None:
                плохо("старая копия удалена, хотя пресет не лёг в базу")
            print(f"  отказ при переносе: ключ {'остался' if р['ключ'] else 'удалён'}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: со связью пресеты и правки пишутся в базу; без связи ложатся в очередь в браузере и уходят "
          "сами, когда связь вернулась; новое в базе не затирается, удалённое не воскресает; коды не двоятся.")


if __name__ == "__main__":
    главная()
