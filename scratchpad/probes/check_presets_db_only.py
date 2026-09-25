#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресеты хранятся только в базе, в браузере — ни одной записи.

Константин 25.09.2026: «запрети сохранение пресетов локально в браузере.
Только в базу». Повод — разбор того же дня: у менеджеров память браузера
была переполнена, копия пресета не записывалась, и вместе с ней терялся код.

Проба держит:
  • старая копия из браузера переезжает: пресет, живший только в браузере,
    первая синхронизация доливает в базу, и лишь тогда ключ удаляется;
  • если хоть один старый пресет в базу не лёг — ключ остаётся, расчёт не
    пропадает;
  • новое сохранение не пишет в браузер ни байта под ключом пресетов, строка
    появляется в базе, код выдаётся; «Пресет сохранён» — после ответа базы,
    отказ базы назван словами;
  • после «перезагрузки» (память страницы пуста) синхронизация возвращает
    пресеты из базы;
  • пока коды не прочитаны из базы, новые номера не раздаются — иначе
    пресет получил бы второй код.

    python3 check_presets_db_only.py
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


def страница(бр, порт, в_браузере, отказ=None):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    # Старая копия кладётся до первого сценария страницы — как у менеджера.
    стр.add_init_script(f"try {{ if (!sessionStorage.getItem('засеяно')) {{ localStorage.setItem('{КЛЮЧ}', "
                        f"{json.dumps(json.dumps(в_браузере, ensure_ascii=False), ensure_ascii=False)}); "
                        "sessionStorage.setItem('засеяно', '1'); } } catch (e) {}")
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
            # Отказ базы назван словами.
            т = стр.evaluate("""async () => { const был = window.sbSavePreset; window.sbSavePreset = async () => false;
              await сохранитьНовыйПресет('Отказ', 'Отказ', collectState()); window.sbSavePreset = был;
              return (document.getElementById('toastMsg') || {}).textContent || ''; }""")
            if "не сохранился в базе" not in т:
                плохо(f"отказ базы не назван: {т!r}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()

            # 2. Старый пресет не лёг в базу — ключ остаётся.
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
    print("Чисто: пресеты пишутся только в базу; старая копия переезжает и удаляется, лишь когда база "
          "подтвердила всё; после перезагрузки пресеты возвращаются из базы; коды не двоятся.")


if __name__ == "__main__":
    главная()
