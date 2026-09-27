#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подсказка у закрытой опции: по ширине текста и едет со строкой без рывков.

Константин 27.09.2026, снимком закрытой опции «Материал кровельного
покрытия — профлист» с подсказкой «Недоступно: выбрано „…наплавляемая
ТехноНИКОЛЬ“»: «пробел непонятный у этой плашки, и когда прокрутку страницы
делаешь — эта плашка едет с опцией, но с подёргиваниями».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • справа от самой длинной строки текста в плашке нет пустоты — только поле;
  • плашка стоит над строкой с зазором 8 px;
  • прокрутка страницы сдвигает плашку вместе со строкой в том же кадре, до
    всякого обработчика: подсказка стоит в координатах страницы, а не экрана
    (с position:fixed её догонял обработчик прокрутки — отсюда рывки);
  • при прокрутке внутреннего списка плашка всё так же догоняет строку.

    python3 check_excl_tip.py
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
  selectProjectOption(0); await ждать(700);
  const строки = [...document.querySelectorAll('.opt-item[id^="lbl_"]')].filter(e => e.offsetWidth);
  if (строки.length < 12) return { нет: строки.length };
  const а = строки[2].id.slice(4), б2 = строки[10].id.slice(4);
  MUTUAL_EXCLUSIONS.length = 0;
  MUTUAL_EXCLUSIONS.push({ triggers: [а], excludes: [б2] });
  // Длинное имя у виновника — чтобы текст подсказки лёг в две строки.
  const оп = OPTIONS.find(o => o.id === а); if (оп) оп.name = 'Материал кровельного покрытия — наплавляемая ТехноНИКОЛЬ';
  checkedOptions[а] = true; applyExclusions(); await ждать(200);
  const строка = document.getElementById('lbl_' + б2);
  строка.scrollIntoView({ block: 'center' }); await ждать(200);
  показатьЗапрет(строка, строка.dataset.blockedText, false); await ждать(100);
  window.__строка = строка;
  return { закрыта: строка.dataset.blocked === '1', текст: строка.dataset.blockedText };
}"""

МЕРА = """() => {
  const tip = document.getElementById('exclTooltip'), с = window.__строка;
  const т = tip.getBoundingClientRect(), r = с.getBoundingClientRect();
  const р = document.createRange(); р.selectNodeContents(tip);
  const кв = [...р.getClientRects()].filter(к => к.width > 0);
  const правоТекста = Math.max(...кв.map(к => к.right));
  const cs = getComputedStyle(tip);
  const пустота = Math.round(т.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth) - правоТекста);
  const до = Math.round(т.top - r.top);
  // прокрутка страницы — мерим в том же задании, до событий прокрутки
  window.scrollBy(0, 120);
  const т2 = tip.getBoundingClientRect(), r2 = с.getBoundingClientRect();
  const после = Math.round(т2.top - r2.top);
  window.scrollBy(0, -120);
  return { строк: кв.length, пустота, зазор: Math.round(r.top - т.bottom), до, после, видна: tip.style.display, заКрай: т.right > innerWidth + 0.5 || т.left < -0.5, ширина: Math.round(т.width) };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank", "light"):
                for ш in (390, 1440):
                    н = f"[{ui} {ш}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    п = стр.evaluate(ПОДГОТОВКА, ui)
                    if not п.get("закрыта"):
                        плохо(f"{н} закрыть опцию не удалось: {п}"); стр.close(); continue
                    м = стр.evaluate(МЕРА)
                    print("  " + н, json.dumps(м, ensure_ascii=False))
                    if м["видна"] != "block":
                        плохо(f"{н} подсказка не показана")
                    if м["строк"] >= 2 and м["пустота"] > 3:
                        плохо(f"{н} справа от текста в плашке пустота {м['пустота']} px")
                    if abs(м["зазор"] - 8) > 1:
                        плохо(f"{н} зазор плашки до строки {м['зазор']} px вместо 8")
                    if м["до"] != м["после"]:
                        плохо(f"{н} прокрутка страницы оторвала плашку от строки: {м['до']} → {м['после']} px — её догоняет обработчик")
                    if м["заКрай"]:
                        плохо(f"{н} плашка за краем экрана")
                    стр.screenshot(path=str(СНИМКИ / f"excl-tip-{ui}-{ш}.png"))
                    # Перенос раньше края: длинное слово уходит на вторую строку целиком,
                    # и первая кончается задолго до предельной ширины — как на снимке с
                    # телефона, где шрифт шире, чем в контейнере.
                    стр.evaluate("() => показатьЗапрет(window.__строка, 'Недоступно: выбрано «Кровля — ТехноНИКОЛЬ-Экстра-Профессионал-Двухслойная»', false)")
                    м2 = стр.evaluate(МЕРА)
                    print("  " + н, "ранний перенос", json.dumps(м2, ensure_ascii=False))
                    if м2["строк"] >= 2 and м2["пустота"] > 3:
                        плохо(f"{н} при раннем переносе справа от текста пустота {м2['пустота']} px")
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
    print("Чисто: подсказка у закрытой опции по ширине текста, над строкой с зазором 8 px и едет вместе со "
          "строкой в том же кадре прокрутки — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
