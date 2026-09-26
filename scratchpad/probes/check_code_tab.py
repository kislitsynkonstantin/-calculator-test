#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно «Пресеты»: вкладка «По коду» — найденные по коду пресеты и избранные.

Константин 26.09.2026, снимком окна «Пресеты»: «тут добавь ещё вкладку „По
коду“ — найденные пресеты по коду будут там. И когда добавляю звезду, чтобы
этот пресет там отображался как избранный».

Проба на 390 и 1440, в «Бланке», с чужим неопубликованным пресетом 365 484
(функция базы подменена), держит:
  • третья вкладка «По коду» стоит в ряду с «Моими» и «Общими», ряд не
    вылезает за окно;
  • код, набранный в «Моих», которого там нет, уводит во вкладку «По коду»,
    и найденная карточка стоит там;
  • пресет открывается с этой карточки; звезда на полоске открытого пресета
    кладёт его в «Избранные — 1» вкладки «По коду»;
  • с пустым поиском вкладка показывает список найденных, звёздный сверху;
    снятая звезда переносит его в «Найденные»;
  • список живёт в настройках аккаунта (`codeFound`), а строки, которых нет
    в памяти страницы, дочитываются из базы;
  • возврат в «Мои» с кодом в поле не уводит обратно — там ссылка словами;
  • карточка не вылезает за край окна;
  • у неопубликованного значок — облако с галочкой, у опубликованного — глобус.

    python3 check_code_tab.py
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
  const снимок = collectState(); снимок.tech = 'frame';
  selectProjectOption(1); await ждать(500);
  window.__вызововКода = 0;
  window.__RPC = window.__RPC || {};
  window.__RPC.get_preset_by_code = а => { window.__вызововКода++; return а.code === '365484' ? [{ short_code: '365484', preset_id: 'preset_x', author_id: 'u-другой',
    author_name: 'Максим Григорьев', name: 'Атапин Юрий Иванович · Фахверковая баня «Берлин» 9х5 · 14.09.26', state: снимок,
    is_public: false, visibility: 'public', created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z', locked: false }] : []; };
  _sharedPresets.length = 0;
  try { _общиеЗагружены = true; } catch (e) {}
  appSettings.sharedStars = []; _sharedStars = new Set(); appSettings.codeFound = [];
  openPresetPanel(); await ждать(300);
  return true;
}"""

ВКЛАДКИ = """() => {
  const ряд = document.querySelector('.ptabs');
  const к = [...ряд.querySelectorAll('.ptab')].filter(x => x.offsetWidth);
  const р = ряд.getBoundingClientRect();
  return { имена: к.map(x => x.textContent.trim()),
    вРяд: к.every(x => Math.abs(x.getBoundingClientRect().top - к[0].getBoundingClientRect().top) < 2),
    заКрай: к.some(x => x.getBoundingClientRect().right > Math.min(р.right, innerWidth) + 0.5),
    активная: (ряд.querySelector('.ptab-active') || {}).id || null };
}"""

СОСТОЯНИЕ = """() => {
  const сп = document.getElementById('codePresetList');
  const карт = [...сп.querySelectorAll('.shared-pcard')];
  return { вкладка: _presetTab,
    видна: getComputedStyle(document.getElementById('ptab-content-code')).display !== 'none',
    метки: [...сп.querySelectorAll('.preset-section-label')].map(м => м.textContent.trim()),
    карточки: карт.map(к => к.dataset.scode),
    заКрай: карт.some(к => к.getBoundingClientRect().right > innerWidth + 0.5 || к.getBoundingClientRect().left < -0.5),
    ширинаСтраницы: document.documentElement.scrollWidth > innerWidth + 1,
    сохранено: (appSettings.codeFound || []).slice(), звёзды: [..._sharedStars] };
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
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate(ПОДГОТОВКА)
                в = стр.evaluate(ВКЛАДКИ)
                print("  " + н, "вкладки", в)
                if в["имена"] != ["Мои", "Общие", "По коду"]:
                    плохо(f"{н} вкладки {в['имена']} — ждали «Мои», «Общие», «По коду»")
                    стр.close(); continue
                if not в["вРяд"] or в["заКрай"]:
                    плохо(f"{н} вкладки не в один ряд или за краем окна: {в}")

                # 1. код в «Моих» уводит во вкладку «По коду»
                стр.click("#ptab-my"); стр.wait_for_timeout(200)
                стр.fill("#presetSearchInput", "365484"); стр.wait_for_timeout(700)
                р = стр.evaluate(СОСТОЯНИЕ)
                print("  " + н, "набор в «Моих»", р)
                if р["вкладка"] != "code" or not р["видна"] or р["карточки"] != ["365484"]:
                    плохо(f"{н} код из «Моих» не увёл в «По коду» с карточкой: {р}")
                if р["сохранено"] != ["365484"]:
                    плохо(f"{н} найденный код не лёг в список аккаунта: {р['сохранено']}")
                if р["заКрай"] or р["ширинаСтраницы"]:
                    плохо(f"{н} карточка или страница шире окна")
                стр.screenshot(path=str(СНИМКИ / f"code-tab-{ш}-found.png"))
                # значок: неопубликованный — облако, опубликованный — глобус
                зн = стр.evaluate("""async () => {
                  const к = document.querySelector('#codePresetList .shared-pcard[data-scode="365484"]');
                  const скрыт = к ? { облако: !!к.querySelector('.pst:not(.pst-pub)'), глобус: !!к.querySelector('.pst-pub') } : null;
                  const снимок = (_foundByCodeCache['365484'] || {}).state;
                  _sharedPresets.push({ short_code: '540117', id: '540117', preset_id: 'x540117', author_id: 'u-другой',
                    author_name: 'Павел Жуков', name: 'Опубликованный пресет пробы', state: снимок, is_public: true,
                    visibility: 'public', created_at: '2026-09-20T10:00:00Z', updated_at: '2026-09-20T10:00:00Z', locked: false });
                  const п = document.getElementById('codeSearchInput'); п.value = '540117';
                  п.dispatchEvent(new Event('input', { bubbles: true }));
                  await new Promise(r => setTimeout(r, 400));
                  const о = document.querySelector('#codePresetList .shared-pcard[data-scode="540117"]');
                  const откр = о ? { облако: !!о.querySelector('.pst:not(.pst-pub)'), глобус: !!о.querySelector('.pst-pub') } : null;
                  // Пробный опубликованный уходит из списка: дальше проба считает карточки.
                  appSettings.codeFound = (appSettings.codeFound || []).filter(к => к !== '540117');
                  for (let и = _sharedPresets.length - 1; и >= 0; и--) if (_sharedPresets[и].short_code === '540117') _sharedPresets.splice(и, 1);
                  п.value = '365484'; п.dispatchEvent(new Event('input', { bubbles: true }));
                  await new Promise(r => setTimeout(r, 300));
                  return { скрыт, откр }; }""")
                if not зн["скрыт"] or зн["скрыт"]["глобус"] or not зн["скрыт"]["облако"]:
                    плохо(f"{н} у неопубликованного по коду не облако, а {зн['скрыт']}")
                if not зн["откр"] or not зн["откр"]["глобус"]:
                    плохо(f"{н} у опубликованного по коду нет глобуса: {зн['откр']}")

                # 2. открыть и отметить звездой на полоске
                кн = стр.locator("#codePresetList .btn-shared-use").first
                if not кн.count():
                    плохо(f"{н} на карточке нет «Открыть»"); стр.close(); continue
                кн.click(); стр.wait_for_timeout(900)
                открыт = стр.evaluate("() => _activeSharedCode")
                if открыт != "365484":
                    плохо(f"{н} пресет не открылся с карточки ({открыт!r})")
                стр.evaluate("() => document.getElementById('presetStarBtn').click()")
                стр.wait_for_timeout(300)
                стр.evaluate("() => { openPresetPanel(); }"); стр.wait_for_timeout(300)
                стр.click("#ptab-code"); стр.wait_for_timeout(300)
                стр.evaluate("() => { const п = document.getElementById('codeSearchInput'); п.value = ''; п.dispatchEvent(new Event('input', { bubbles: true })); }")
                стр.wait_for_timeout(500)
                р = стр.evaluate(СОСТОЯНИЕ)
                print("  " + н, "звезда", р)
                if not р["метки"] or not р["метки"][0].startswith("Избранные") or р["карточки"] != ["365484"]:
                    плохо(f"{н} после звезды на полоске пресет не стоит в «Избранных» вкладки «По коду»: {р['метки']} {р['карточки']}")
                стр.screenshot(path=str(СНИМКИ / f"code-tab-{ш}-starred.png"))

                # 3. снять звезду на карточке — в «Найденные»
                стр.evaluate("() => { const к = document.querySelector('#codePresetList .shared-pcard[data-scode=\"365484\"] .shared-pcard-top button'); к && к.click(); }")
                стр.wait_for_timeout(400)
                р = стр.evaluate(СОСТОЯНИЕ)
                if not р["метки"] or not р["метки"][0].startswith("Найденные") or р["звёзды"]:
                    плохо(f"{н} снятая звезда не перенесла пресет в «Найденные»: {р['метки']} {р['звёзды']}")

                # 4. строки нет в памяти страницы — дочитывается из базы
                стр.evaluate("() => { delete _foundByCodeCache['365484']; for (let и = _sharedPresets.length - 1; и >= 0; и--) if (_sharedPresets[и].short_code === '365484') _sharedPresets.splice(и, 1); window.__вызововКода = 0; renderCodeList(); }")
                стр.wait_for_timeout(700)
                р = стр.evaluate(СОСТОЯНИЕ)
                вызовов = стр.evaluate("() => window.__вызововКода")
                if р["карточки"] != ["365484"] or not вызовов:
                    плохо(f"{н} список не дочитал строку из базы: карточки {р['карточки']}, запросов {вызовов}")

                # 5. возврат в «Мои» с кодом в поле — без возврата обратно
                стр.fill("#codeSearchInput", "365484"); стр.wait_for_timeout(500)
                стр.click("#ptab-my"); стр.wait_for_timeout(500)
                р2 = стр.evaluate("() => ({ вкладка: _presetTab, ссылка: !!document.querySelector('#presetList .pcode-go') })")
                if р2["вкладка"] != "my" or not р2["ссылка"]:
                    плохо(f"{н} «Мои» с кодом в поле: {р2} — ждали вкладку «Мои» со ссылкой на «По коду»")
                else:
                    к = стр.evaluate("() => { const б = document.querySelector('#presetList .pcode-go'); const r = б.getBoundingClientRect(); const bf = getComputedStyle(б, '::before'); return { h: r.height - 2 * (parseFloat(bf.top) || 0) }; }")
                    if к["h"] < 32:
                        плохо(f"{н} поле нажатия ссылки «Искать во вкладке…» {к['h']:.0f} px")
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
    print("Чисто: вкладка «По коду» собирает найденные по коду пресеты, звезда с полоски ставит пресет "
          "в её «Избранные», список живёт в аккаунте и дочитывается из базы; «Мои» с кодом в поле не уводят обратно.")


if __name__ == "__main__":
    главная()
