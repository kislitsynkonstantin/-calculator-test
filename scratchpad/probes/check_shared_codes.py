#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Общие пресеты после входа и коды пресетов: список, один код, публикация.

Константин 26.09.2026, со снимками: «все публичные пресеты пропали и не даёт
мне публичный опубликовать». Разбор по журналу базы: после входа синхронизация
кладёт свои строки в кэш «Общих» урезанными (без названия и расчёта), и вкладка
принимала их за загруженный список; выдача кода обгоняла чтение своих строк и
давала пресету второй код (у «D1» — 112 529 при опубликованном 235 788); а
флаги пресета брали последнюю из нескольких строк.

Проба держит:
  • урезанные свои строки в кэше не мешают вкладке «Общие» прочитать полный
    список: на ней все опубликованные, с названиями;
  • выдача кода пресету, чья строка уже есть в базе, но ещё не в кэше, не
    заводит вторую строку и не меняет код на карточке;
  • у пресета с двумя строками на карточке код опубликованной, и он помечен
    опубликованным;
  • лёгкая синхронизация своих строк читает и замок — без него публикация
    запертого пресета шла мимо снятия замка и падала на правиле доступа.

    python3 check_shared_codes.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];")
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


СЦЕНАРИЙ = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const я = _sbUser && _sbUser.id;
  const ст = { project: { name: 'Хай-тек баня «Виго» 7,7х8,2' }, thickness: 1, totalNum: 5897478, tech: 'frame' };
  const строка = (код, преcет, свой, общий, замок, когда, имя) => ({ short_code: код, preset_id: преcет, author_id: свой ? я : 'u-другой',
    author_name: свой ? 'Проба' : 'Анатолий', name: имя, state: ст, is_public: общий, visibility: 'public', locked: замок,
    created_at: когда, updated_at: когда });
  window.__ТАБЛИЦЫ.preset_links = [
    строка('235788', 'P1', true, true, true, '2026-09-24T06:50:00Z', 'D1_Хай-тек баня «Виго»'),
    строка('112529', 'P1', true, false, false, '2026-09-26T16:57:00Z', 'D1_Хай-тек баня «Виго»'),
    строка('775165', 'PX', false, true, false, '2026-09-02T10:05:00Z', 'Чужой общий'),
    строка('574573', 'PY', false, false, false, '2026-09-02T10:05:00Z', 'Чужой личный'),
    строка('404040', 'P2', true, false, false, '2026-09-20T10:00:00Z', 'Второй свой') ];
  // 1. После входа: в кэше урезанные свои строки, признак кодов стоит.
  _sharedPresets = window.__ТАБЛИЦЫ.preset_links.filter(r => r.author_id === я)
    .map(r => ({ short_code: r.short_code, id: r.short_code, preset_id: r.preset_id, author_id: r.author_id, is_public: r.is_public, visibility: r.visibility }));
  _кодыПресетовИзБазы = true;
  try { _общиеЗагружены = false; } catch (e) {}
  openPresetPanel();
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  let упало = '';
  try { setSharedFilter('all'); await loadSharedPresets(); } catch (e) { упало = String(e && e.message || e); }
  await ждать(200);
  const карточки = [...document.querySelectorAll('#sharedPresetList .shared-pcard')].map(к => ({ код: к.dataset.scode,
    имя: ((к.querySelector('.shared-pcard-name') || {}).textContent || '').trim() }));
  const пусто = /Нет опубликованных/.test(document.getElementById('sharedPresetList').textContent);
  closePresetPanel();
  // 2. Выдача кода обгоняет чтение своих строк: в кэше пусто, в базе строка есть.
  const все = loadAllPresets();
  все.P2 = { id: 'P2', name: 'Второй свой', savedAt: '2026-09-20T10:00:00Z', shortCode: '404040', sharedId: '404040', state: ст };
  все.P1 = { id: 'P1', name: 'D1_Хай-тек баня «Виго»', savedAt: '2026-09-26T16:57:00Z', shortCode: '112529', sharedId: '112529', state: ст };
  saveAllPresets(все);
  _sharedPresets = [];
  try { await sharePreset('P2', true); } catch (e) {}
  await ждать(100);
  const строкP2 = window.__ТАБЛИЦЫ.preset_links.filter(r => r.preset_id === 'P2').map(r => r.short_code);
  const кодP2 = (loadAllPresets().P2 || {}).shortCode;
  // 3. Две строки у пресета: карточка берёт опубликованную.
  _sharedPresets = window.__ТАБЛИЦЫ.preset_links.map(r => ({ ...r, id: r.short_code }));
  syncPublishedFlags();
  const p1 = loadAllPresets().P1 || {};
  return { упало, карточки, пусто, строкP2, кодP2, кодP1: p1.shortCode, опублP1: p1.publishedAs || '' };
}"""


def главная():
    с, порт = сервер()
    # 4. Лёгкая синхронизация своих строк читает замок.
    текст = (КОРЕНЬ / "index.html").read_text(encoding="utf-8")
    import re
    лёгкие = re.findall(r"from\('preset_links'\)\.select\('([^']*)'\)\s*\.eq\('author_id', _sbUser\.id\)\s*\.then", текст)
    if not лёгкие: плохо("не нашлась лёгкая синхронизация своих строк — проба устарела")
    for поля in лёгкие:
        if "locked" not in поля.split(","): плохо(f"лёгкая синхронизация не читает замок: select('{поля}')")
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                н = f"{ш}"
                try:
                    р = стр.evaluate(СЦЕНАРИЙ)
                except Exception as e:
                    плохо(f"{н}: сценарий упал: {str(e)[:160]}"); стр.close(); continue
                print("  " + н + ": " + json.dumps(р, ensure_ascii=False))
                коды = {к["код"] for к in р["карточки"]}
                if р["упало"]: плохо(н + f": вкладка «Общие» упала на урезанной строке: {р['упало'][:90]}")
                if р["пусто"] or not {"235788", "775165"} <= коды:
                    плохо(н + f": на «Общих» нет опубликованных после входа (карточки: {sorted(коды)})")
                if any(not к["имя"] for к in р["карточки"]): плохо(н + ": на «Общих» карточка без названия — урезанная строка")
                if "574573" in коды or "112529" in коды: плохо(н + ": на «Общих» показан неопубликованный пресет")
                if р["строкP2"] != ["404040"]: плохо(н + f": пресет получил второй код, строки в базе: {р['строкP2']}")
                if р["кодP2"] != "404040": плохо(н + f": код на карточке сменился: {р['кодP2']}")
                if р["кодP1"] != "235788" or not р["опублP1"]:
                    плохо(н + f": у пресета с двумя строками на карточке {р['кодP1']} ({р['опублP1'] or 'не опубликован'}), а не опубликованный 235788")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{н}: ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: после входа «Общие» читают полный список, урезанные свои строки ему не мешают; пресет со строкой в базе "
          "второго кода не получает; из двух строк карточка берёт опубликованную; лёгкая синхронизация читает замок.")


if __name__ == "__main__":
    главная()
