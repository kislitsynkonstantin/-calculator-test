#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real calculator page with a demo catalog, filled and ready for the five windows.

    python3 harness.py shots [--glass glass.css] [--out DIR] [--w 390,1440] [--mode blank-dark,...]
    import harness; harness.открыть(pw, ш, режим, стекло) -> page
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading, time

ЗДЕСЬ = pathlib.Path(__file__).parent
КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or "/home/user/-calculator-test")
ПРОБЫ = КОРЕНЬ / "scratchpad" / "probes"
ЗАГЛУШКА = (ПРОБЫ / "stub_sb.js").read_text(encoding="utf-8")
ДЕМО = json.loads((ЗДЕСЬ / "demo_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДЕМО, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Андрей', last_name: 'Мельников', full_name: 'Андрей Мельников', app_settings: {} }];\n"
              "window.__ТАБЛИЦЫ.events = window.__ТАБЛИЦЫ.events || [];\n")


# Без программного GL Chromium в контейнере не рисует backdrop-filter вовсе.
АРГИ = ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


_сервер = None


def сервер():
    global _сервер
    if _сервер:
        return _сервер
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    _сервер = (с, с.server_address[1])
    return _сервер


НАПОЛНИТЬ = r"""async ([ui, ночь, тон]) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
  window.showToast = () => {};
  applyUiStyle(ui, false); applyThemeMode(ночь ? 'dark' : 'light', false); applyTone(тон, false);
  // ── расчёты для «Моих» и «Общих» ──
  const снимки = [];
  for (const [и, опции, скидка] of [[1, ['f5','ex11','w8','r6'], 0], [2, ['fr12','s9','in6','st1'], 2], [0, ['f5','f12','in6','ex11','ex14','ex17','w8','w10','w12','r6','r8','p13','i4','i6','s9','s12','st1','st6','st20','e10','eng11','eng15'], 3]]) {
    selectProjectOption(и); await ждать(500);
    опции.forEach(о => { try { if (!checkedOptions[о]) toggleOpt(о); } catch (e) {} });
    document.getElementById('discountPctInput').value = String(скидка);
    calc();
    снимки.push(collectState());
  }
  document.getElementById('managerName').value = 'Мельников Андрей';
  document.getElementById('clientName').value = 'Орлов Сергей Петрович';
  document.getElementById('contractNumber').value = '2609-14';
  const дата = document.getElementById('contractDate'); дата.value = '2026-09-15'; дата.classList.remove('empty');
  document.getElementById('cashDiscountCheck').checked = true;
  document.getElementById('discountUntilDate').value = '2026-10-15';
  calc();
  const сейчас = Date.now();
  const iso = мин => new Date(сейчас - мин * 60000).toISOString();
  // Мои
  const мои = {};
  [['Орлов С. П. · Фахверковая баня «Берлин» 9×5', 2, 'berlin', 0, '365484', 'public'],
   ['Соколова А. В. · Хай-тек баня «Виго» 7,7×8,2', 1, 'vigo', 190, '321910', null],
   ['Демин П. С. · Каркасная баня «Лагом» 6×6', 0, 'lagom', 1500, '235788', null]].forEach(([имя, сн, _, мин, код, пуб], и) => {
    const ид = 'p' + (и + 1);
    мои[ид] = { id: ид, name: имя, state: снимки[сн], savedAt: iso(мин), shortCode: код, sharedId: код,
                publishedAs: пуб || undefined, starred: и === 0 };
  });
  saveAllPresets(мои);
  // Общие
  const строка = (код, имя, автор, аид, сн, мин, закрыт) => ({ short_code: код, id: код, preset_id: 'x' + код,
    author_id: аид, author_name: автор, name: имя, state: снимки[сн], is_public: true, visibility: 'public',
    created_at: iso(мин + 600), updated_at: iso(мин), last_edited_at: iso(мин), locked: !!закрыт });
  _sharedPresets.length = 0;
  _sharedPresets.push(
    строка('365484', 'Орлов С. П. · Фахверковая баня «Берлин» 9×5', 'Андрей Мельников', _sbUser.id, 2, 2, true),
    строка('718203', 'Лаптев К. О. · Хай-тек баня «Виго» 7,7×8,2', 'Анна Кузнецова', 'u-2', 1, 64, false),
    строка('540117', 'Шестаков Р. М. · Каркасная баня «Лагом» 6×6', 'Павел Жуков', 'u-3', 0, 380, false));
  try { _общиеЗагружены = true; } catch (e) {}
  window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(х => Object.assign({}, х));
  // Журнал действий
  const с = (и, вид, мин, кто, пары, код, пресет) => ({ id: и, user_id: кто, event_type: вид,
    project_name: 'Фахверковая баня «Берлин» 9×5', total_price: 5339818, options_count: 74, thickness: 150,
    discount: 3, cash_discount: true, checked_options: {}, created_at: iso(мин),
    details: { obj: 'Фахверковая баня «Берлин» 9×5', rows: пары || [], presetCode: код, preset: пресет } });
  const пр = 'Орлов С. П. · Фахверковая баня «Берлин» 9×5';
  window.__ТАБЛИЦЫ.events = [
    с(1, 'print', 3, _sbUser.id, [], '365484', пр),
    с(2, 'discount_changed', 9, _sbUser.id, [{k:'Скидка',a:'0 %',b:'3 %'},{k:'Итог',a:'',b:'5 179 623 ₽'}], '365484', пр),
    с(3, 'share_created', 26, _sbUser.id, [], '365484', пр),
    с(4, 'preset_saved', 41, _sbUser.id, [], '365484', пр),
    с(5, 'options_batch', 58, _sbUser.id, [{k:'Добавлены',a:'',b:'Планкен из лиственницы 20×140\nПанорамное остекление комнаты отдыха\nПарная канадским кедром'},{k:'Итог',a:'4 812 300 ₽',b:'5 339 818 ₽'}], '365484', пр),
    с(6, 'print', 140, 'u-2', [], '718203', 'Лаптев К. О. · Хай-тек баня «Виго» 7,7×8,2'),
    с(7, 'preset_opened', 260, _sbUser.id, [], '540117', 'Шестаков Р. М. · Каркасная баня «Лагом» 6×6'),
  ];
  window.__ТАБЛИЦЫ.profiles.push({ id: 'u-2', role: 'manager', full_name: 'Анна Кузнецова', first_name: 'Анна', last_name: 'Кузнецова' },
                                 { id: 'u-3', role: 'manager', full_name: 'Павел Жуков', first_name: 'Павел', last_name: 'Жуков' });
  // Открытый расчёт — «Берлин» из «Моих», активный.
  try { loadPreset('p1'); } catch (e) {}
  await ждать(900);
  document.getElementById('managerName').value = 'Мельников Андрей';
  document.getElementById('clientName').value = 'Орлов Сергей Петрович';
  calc();
  window.scrollTo(0, 0);
  return { итог: _currentTotal, проект: selectedProject && selectedProject[0] };
}"""

ОКНА = {
    "presets":  "async () => { openPresetPanel(); await new Promise(r => setTimeout(r, 700)); }",
    "shared":   "async () => { openPresetPanel(); await new Promise(r => setTimeout(r, 300)); switchPresetTab('shared'); await new Promise(r => setTimeout(r, 700)); }",
    "plan":     "async () => { openPaymentPlan(); await new Promise(r => setTimeout(r, 700)); }",
    "settings": "async () => { openSettings(); switchSettingsTab('set'); await new Promise(r => setTimeout(r, 700)); }",
    "log":      "async () => { openActionLog(); await new Promise(r => setTimeout(r, 1200)); }",
    "print":    "async () => { openPrintPreview(); await new Promise(r => setTimeout(r, 1500)); }",
}
ЗАКРЫТЬ = """() => { ['closePresetPanel','closePaymentPlan','closeSettings','closeActionLog','closePrintPreview']
  .forEach(ф => { try { window[ф](); } catch (e) {} }); }"""

РЕЖИМЫ = {"blank-dark": ("blank", True, "bmsk"), "blank-light": ("blank", False, "teal"),
          "modern-dark": ("light", True, "teal"), "modern-light": ("light", False, "teal"),
          "blank-dark-teal": ("blank", True, "teal")}


def открыть(бр, ш, режим, стекло=None, высота=None):
    с, порт = сервер()
    стр = бр.new_page(viewport={"width": ш, "height": высота or (844 if ш < 500 else 900)},
                      device_scale_factor=2 if ш < 500 else 1)
    стр._ошибки = []
    стр.on("pageerror", lambda e: стр._ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    # Шрифты вшиты: Chromium в контейнере до Google Fonts не ходит.
    стр.add_style_tag(content=(ЗДЕСЬ / "fonts-embedded.css").read_text(encoding="utf-8"))
    стр.wait_for_timeout(2500)
    ui, ночь, тон = РЕЖИМЫ[режим]
    стр._итог = стр.evaluate(НАПОЛНИТЬ, [ui, ночь, тон])
    if стекло:
        стр.add_style_tag(content=pathlib.Path(стекло).read_text(encoding="utf-8"))
        стр.evaluate("() => document.body.classList.add('ui-glass')")
        стр.wait_for_timeout(200)
    return стр


def кадры(стекло=None, выход="shots", ширины=(390, 1440), режимы=("blank-dark",), окна=None, прокрутка=True):
    from playwright.sync_api import sync_playwright
    выход = pathlib.Path(выход); выход.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром(), args=АРГИ)
        for режим in режимы:
            for ш in ширины:
                стр = открыть(бр, ш, режим, стекло)
                стр.screenshot(path=str(выход / f"{режим}-{ш}-page.png"))
                if прокрутка:
                    стр.evaluate("() => { const с = document.getElementById('optionSections'); if (с) с.scrollIntoView(); window.scrollBy(0, 300); }")
                    стр.wait_for_timeout(400)
                    стр.screenshot(path=str(выход / f"{режим}-{ш}-spec.png"))
                    стр.evaluate("() => window.scrollTo(0, 0)")
                for имя, код in ОКНА.items():
                    if окна and имя not in окна:
                        continue
                    стр.evaluate(код)
                    стр.screenshot(path=str(выход / f"{режим}-{ш}-{имя}.png"))
                    стр.evaluate(ЗАКРЫТЬ); стр.wait_for_timeout(300)
                if стр._ошибки:
                    print(режим, ш, "ошибки:", стр._ошибки[:3])
                print(режим, ш, стр._итог)
                стр.close()
        бр.close()


if __name__ == "__main__":
    арг = sys.argv[1:]
    стекло = арг[арг.index("--glass") + 1] if "--glass" in арг else None
    выход = арг[арг.index("--out") + 1] if "--out" in арг else str(ЗДЕСЬ / "shots")
    ширины = tuple(int(х) for х in (арг[арг.index("--w") + 1] if "--w" in арг else "390,1440").split(","))
    режимы = tuple((арг[арг.index("--mode") + 1] if "--mode" in арг else "blank-dark").split(","))
    окна = set(арг[арг.index("--win") + 1].split(",")) if "--win" in арг else None
    кадры(стекло, выход, ширины, режимы, окна)
