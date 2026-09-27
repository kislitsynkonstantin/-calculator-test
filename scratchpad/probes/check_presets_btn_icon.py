#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок открытого пресета на кнопке «Пресеты» в шапке.

Константин 27.09.2026: «на кнопке Пресеты показывай иконку активного пресета
(облако, глобус и глобус закрашенный)».

Проба держит, на 390 и 1440, в «Бланке» и «Модерне», днём и ночью:
  • ничего не открыто — прежняя дискета;
  • свой пресет в базе — облако, как на его карточке;
  • свой, ждущий связи в браузере, — экран, и сразу, как пресет лёг в очередь, без
    перерисовки списка; очередь ушла в базу — снова облако;
  • свой опубликованный — глобус цветом схемы, тем же, что у глобуса на карточке;
  • чужой общий — серый глобус, цветом подписи кнопки;
  • отозвали публикацию — снова облако; закрыли пресет — снова дискета;
  • значок 13 px и стоит в строке с подписью, кнопка не выросла.

    python3 check_presets_btn_icon.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а): pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


# Что на кнопке: форма значка по его рисунку, цвет, размер, строка.
ВИД = """() => {
  const к = document.getElementById('presetsBtn'), м = к && к.querySelector('#presetsIco, svg');
  const svg = м ? (м.tagName.toLowerCase() === 'svg' ? м : м.querySelector('svg')) : null;
  const р = svg ? svg.innerHTML : '';
  const форма = /M17\\.5 19H9a7/.test(р) ? 'облако' : /rect x="3" y="4"/.test(р) ? 'экран'
    : /circle cx="12" cy="12" r="9\\.2"/.test(р) ? 'глобус' : /polyline points="17 21 17 13/.test(р) ? 'дискета' : '?';
  const б = svg ? svg.getBoundingClientRect() : { width: 0, height: 0, top: 0, bottom: 0 };
  const т = [...к.childNodes].find(у => у.nodeType === 3 && у.textContent.trim());
  const д = document.createRange(); if (т) д.selectNodeContents(т);
  const тб = т ? д.getBoundingClientRect() : б;
  return { форма, цвет: svg ? getComputedStyle(svg).color : '', подпись: getComputedStyle(к).color,
           ш: Math.round(б.width), в: Math.round(б.height), высотаКнопки: Math.round(к.getBoundingClientRect().height),
           сдвиг: Math.round(Math.abs((б.top + б.bottom) / 2 - (тб.top + тб.bottom) / 2)) };
}"""

ЦВЕТ_СВОЕГО = """() => { const в = document.createElement('button'); в.className = 'pst pst-pub mine';
  в.style.position = 'absolute'; в.style.left = '-999px'; document.body.appendChild(в);
  const ц = getComputedStyle(в).color; в.remove(); return ц; }"""


def прогон(бр, порт, ш, ui, ночь):
    н = f"[{ш} {ui}{' ночь' if ночь else ''}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""([ui, ночь]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle(ui, false); document.body.classList.toggle('dark', ночь); }""", [ui, ночь])
    стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 700)); }")
    до = стр.evaluate(ВИД)
    свой_цвет = стр.evaluate(ЦВЕТ_СВОЕГО)

    def шаг(что, js, ждём, цвет=None):
        стр.evaluate(js); стр.wait_for_timeout(250)
        в = стр.evaluate(ВИД)
        if в["форма"] != ждём:
            НАХОДКИ.append(f"{н} {что}: на кнопке «{в['форма']}», ждали «{ждём}»")
        if цвет == "свой" and в["цвет"] != свой_цвет:
            НАХОДКИ.append(f"{н} {что}: глобус не цветом схемы ({в['цвет']} против {свой_цвет} у карточки)")
        if цвет == "серый" and в["цвет"] != в["подпись"]:
            НАХОДКИ.append(f"{н} {что}: чужой глобус не серый, как подпись ({в['цвет']} против {в['подпись']})")
        if в["ш"] != 13 or в["в"] != 13 or в["сдвиг"] > 2 or в["высотаКнопки"] != до["высотаКнопки"]:
            НАХОДКИ.append(f"{н} {что}: значок {в['ш']}×{в['в']}, сдвиг от строки {в['сдвиг']} px, кнопка {в['высотаКнопки']} (была {до['высотаКнопки']})")
        return в

    if до["форма"] != "дискета":
        НАХОДКИ.append(f"{н} без пресета на кнопке «{до['форма']}», ждали дискету")
    шаг("свой в базе", """() => { const в = loadAllPresets(); в['проба-зн'] = { id: 'проба-зн', name: 'Проба значка',
          savedAt: new Date().toISOString(), state: collectState() }; saveAllPresets(в); setActivePreset('проба-зн'); }""", "облако")
    # Без связи пресет ложится в очередь браузера настоящим путём — и только им:
    # список при этом не перерисовывается, а значок на кнопке обязан смениться
    # сам (Константин, 27.09.2026, режим самолёта). Связь вернулась — облако.
    шаг("свой ушёл в очередь без связи", "() => { _вОчередь(loadAllPresets()['проба-зн']); }", "экран")
    шаг("очередь ушла в базу", "() => { _изОчереди('проба-зн'); }", "облако")
    шаг("свой опубликованный", """() => { const в = loadAllPresets(); в['проба-зн'].publishedAs = 'public'; saveAllPresets(в); renderPresetList(); }""", "глобус", "свой")
    стр.screenshot(path=str(СНИМКИ / f"presets-btn-{ш}-{ui}{'-n' if ночь else ''}.png"),
                   clip=dict(zip(("x", "y", "width", "height"), стр.evaluate("() => { const б = document.getElementById('presetsBtn').getBoundingClientRect(); return [Math.max(0, б.left - 40), Math.max(0, б.top - 20), 260, б.height + 40]; }"))))
    шаг("отозвали", """() => { const в = loadAllPresets(); delete в['проба-зн'].publishedAs; saveAllPresets(в); renderPresetList(); }""", "облако")
    шаг("чужой общий", """() => { _sharedPresets.push({ short_code: '777888', id: '777888', name: 'Чужой', author_id: 'u-другой', author_name: 'Ирина В.',
          is_public: true, locked: true, state: {} }); setActivePreset(null); _activeSharedCode = '777888'; updateSharedModeIndicator(); }""", "глобус", "серый")
    шаг("свой общий из «Общих»", """() => { _sharedPresets.push({ short_code: '777999', id: '777999', name: 'Свой', author_id: _sbUser.id,
          is_public: true, locked: true, state: {} }); _activeSharedCode = '777999'; updateSharedModeIndicator(); }""", "глобус", "свой")
    шаг("закрыли", "() => { _activeSharedCode = null; setActivePreset(null); updateSharedModeIndicator(); }", "дискета")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for ui in ("blank", "light"):
                    for ночь in (False, True):
                        прогон(бр, порт, ш, ui, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: на кнопке «Пресеты» значок открытого пресета — дискета, облако, экран, глобус цветом схемы у своего "
          "опубликованного, серый у чужого; меняется с публикацией и отзывом, 13 px в строке с подписью — "
          "на 390 и 1440, в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
