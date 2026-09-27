#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет, найденный поиском по коду, открывается.

Константин 26.09.2026: «проверь, почему пресет пишет, что не найден. Взял номер
из журнала событий по коду». Поиск по коду кладёт найденное в
`_foundByCodeCache`, а «Открыть» искало в `window._privatePresetCache`, в
который не писал никто: всякий пресет, которого нет среди общих (чужой
неопубликованный, отозванный), отвечал «Пресет не найден».

Проба на 390, в «Мои», «Общих» и «Поиске по всем», ищет по коду чужой
неопубликованный пресет (функция базы подменена), жмёт «Открыть» и держит:
  • сообщения «Пресет не найден» нет;
  • пресет открыт: активный код — этот, полоска общего пресета на экране,
    проект расчёта — из пресета;
  • чужой неопубликованный открыт только на просмотр (`canEditPublic` — нет);
  • в список «Общие» он не попал.

    python3 check_open_by_code.py
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





СЦЕНАРИЙ = """async (вкладка) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  selectProjectOption(0); await ждать(700);
  const снимок = collectState(); снимок.tech = 'frame';
  selectProjectOption(1); await ждать(500);
  const проектПресета = снимок.project && снимок.project.name;
  window.__RPC = window.__RPC || {};
  window.__RPC.get_preset_by_code = а => а.code === '365484' ? [{ short_code: '365484', preset_id: 'preset_x', author_id: 'u-другой',
    author_name: 'Максим Григорьев', name: 'Атапин Юрий Иванович · Фахверковая баня «Берлин» 9х5 · 14.09.26', state: снимок,
    is_public: false, visibility: 'public', created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z', locked: false }] : [];
  const тосты = []; window.showToast = т => тосты.push(String(т));
  _sharedPresets.length = 0;
  try { _общиеЗагружены = true; } catch (e) {}
  openPresetPanel(); await ждать(200);
  const поле = { my: 'presetSearchInput', shared: 'sharedSearchInput', search: 'globalSearchInput' }[вкладка];
  const список = { my: 'presetList', shared: 'sharedPresetList', search: 'globalSearchResults' }[вкладка];
  _presetTab = вкладка;
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === вкладка);
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === вкладка ? 'flex' : 'none'; });
  const п = document.getElementById(поле);
  if (!п) return { нетПоля: поле };
  п.value = '365484'; п.dispatchEvent(new Event('input', { bubbles: true }));
  await ждать(600);
  const кнопка = [...document.querySelectorAll('.btn-shared-use')].find(к => /365484/.test(к.getAttribute('onclick') || '') && к.offsetWidth);
  if (!кнопка) return { нетКнопки: true, html: (document.getElementById(список) || {}).innerHTML?.slice(0, 200) };
  кнопка.click(); await ждать(900);
  // Полоска общего пресета стала значком в углу (27.09.2026).
  const полоска = document.getElementById('presetChip');
  return { тосты, активный: _activeSharedCode, полоска: !!(полоска && полоска.classList.contains('pc-shared') && полоска.offsetWidth),
    проект: selectedProject && selectedProject[0], проектПресета, правка: canEditPublic(),
    вОбщих: (() => { try { return _sharedPresets.filter(sp => sp.is_public).some(sp => sp.short_code === '365484'); } catch (e) { return null; } })() };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for вкладка in ("my", "shared", "search"):
                стр = бр.new_page(viewport={"width": 390, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; applyUiStyle('blank', false); }")
                р = стр.evaluate(СЦЕНАРИЙ, вкладка)
                н = f"[{вкладка}]"
                print("  " + н, json.dumps(р, ensure_ascii=False)[:400])
                if р.get("нетПоля") or р.get("нетКнопки"):
                    плохо(н + f" поиск по коду не показал карточку с «Открыть» ({р})"); стр.close(); continue
                if any("не найден" in т for т in р["тосты"]):
                    плохо(н + f" «Открыть» ответило «Пресет не найден» ({р['тосты']})")
                if р["активный"] != "365484" or not р["полоска"]:
                    плохо(н + f" пресет не открылся (активный {р['активный']!r}, полоска {р['полоска']})")
                elif р["проект"] != р["проектПресета"]:
                    плохо(н + f" открыт, но проект не из пресета ({р['проект']!r} вместо {р['проектПресета']!r})")
                if р["правка"]:
                    плохо(н + " чужой неопубликованный пресет открыт на правку, а не на просмотр")
                if р["вОбщих"]:
                    плохо(н + " неопубликованный пресет попал в «Общие»")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: пресет, найденный по коду, открывается из «Моих», «Общих» и «Поиска по всем»; чужой "
          "неопубликованный — на просмотр и в «Общие» не попадает.")


if __name__ == "__main__":
    главная()
