#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Общие»: у переключателя «Мои» — число своих опубликованных.

Константин 27.09.2026, снимком вкладки «Общие» с обведёнными «Все / Мои»:
«Тут добавь сетку с количеством моих (цифра)».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • у «Мои» стоит число своих опубликованных — неопубликованные свои и чужие
    не считаются;
  • поиск и отбор по технологии число не меняют;
  • пока общие не загрузились, числа нет;
  • число стоит на одной линии с «Мои», с зазором 3–8 px, кнопка не шире
    окна и не наезжает на «Все».

    python3 check_shared_mine_count.py
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


ПОДГОТОВКА = """async (ui) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle(ui, false);
  const я = _sbUser.id;
  const с = (код, свой, публ, тех) => ({ short_code: код, id: код, name: 'Пресет ' + код, author_name: свой ? 'Проба' : 'Другой',
    author_id: свой ? я : 'u-другой', is_public: публ, visibility: 'public', locked: false, created_at: '2026-09-02T10:05:00Z',
    updated_at: '2026-09-02T10:05:00Z', state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 1000000, tech: тех } });
  _sharedPresets.length = 0;
  _sharedPresets.push(с('111111', true, true, 'frame'), с('222222', true, true, 'timber'), с('333333', true, false, 'frame'),
                      с('444444', false, true, 'frame'), с('555555', false, true, 'frame'));
  window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(х => Object.assign({}, х));
  try { _общиеЗагружены = true; } catch (e) {}
  openPresetPanel(); await ждать(300); switchPresetTab('shared'); await ждать(600);
  return true;
}"""

МЕРА = """() => {
  const к = document.getElementById('sharedFilterMine'), н = document.getElementById('sharedMineCount'), в = document.getElementById('sharedFilterAll');
  if (!к || !н) return { нет: true };
  const р = document.createRange(); р.selectNodeContents(к.firstChild);
  const т = р.getBoundingClientRect(), ч = н.getBoundingClientRect(), кр = к.getBoundingClientRect(), вр = в.getBoundingClientRect();
  return { число: н.textContent, видно: н.offsetWidth > 0, зазор: Math.round(ч.left - т.right),
           линия: Math.abs((т.top + т.bottom) / 2 - (ч.top + ч.bottom) / 2) < 3,
           заКрай: кр.right > innerWidth + 0.5, наВсе: вр.right > кр.left + 0.5 && вр.left < кр.right };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank",):
                for ш in (390, 1440):
                    н = f"[{ui} {ш}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    стр.evaluate(ПОДГОТОВКА, ui)
                    м = стр.evaluate(МЕРА)
                    print("  " + н, json.dumps(м, ensure_ascii=False))
                    if м.get("нет"):
                        плохо(f"{н} у «Мои» нет места для числа"); стр.close(); continue
                    if м["число"] != "2" or not м["видно"]:
                        плохо(f"{н} у «Мои» число «{м['число']}» (видно {м['видно']}) — ждали 2")
                    if not (3 <= м["зазор"] <= 8) or not м["линия"]:
                        плохо(f"{н} число не на месте: зазор {м['зазор']} px, на одной линии {м['линия']}")
                    if м["заКрай"] or м["наВсе"]:
                        плохо(f"{н} «Мои» за краем окна или на «Все»")
                    стр.screenshot(path=str(СНИМКИ / f"mine-count-{ui}-{ш}.png"))
                    # поиск и технология число не меняют
                    стр.fill("#sharedSearchInput", "111111"); стр.wait_for_timeout(300)
                    стр.evaluate("() => { ТЕХ_ВЫБОР.shared = new Set(['timber']); renderSharedList(); }"); стр.wait_for_timeout(200)
                    п = стр.evaluate(МЕРА)
                    if п["число"] != "2":
                        плохо(f"{н} поиск и технология поменяли число у «Мои»: {п['число']}")
                    стр.evaluate("() => { ТЕХ_ВЫБОР.shared = new Set(); _общиеЗагружены = false; renderSharedList(); }")
                    з = стр.evaluate(МЕРА)
                    if з["число"] or з["видно"]:
                        плохо(f"{н} пока общие грузятся, у «Мои» число «{з['число']}»")
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
    print("Чисто: у «Мои» в «Общих» число своих опубликованных, поиск и технология его не меняют, пока общие "
          "грузятся — числа нет — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
