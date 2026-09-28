#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: ссылка на статью о выпуске.

Константин 28.09.2026: «к этой статье добавь ссылку, чтобы можно было в
браузере скопировать и отправить, но доступна только тем, кто вошёл».

Держит:
  • адрес калькулятора с #release=2.5.12 у вошедшего открывает окно справки
    сразу на статье, и адрес в строке браузера остаётся тем же;
  • у невошедшего по той же ссылке — экран входа, окна нет и текст статьи
    из базы не запрашивается; после входа статья открывается сама;
  • «Скопировать ссылку» в статье видна, стоит в строке надзаголовка без
    наездов и кладёт в буфер именно этот адрес; подпись сообщает об успехе;
  • статья, открытая из журнала, ставит адрес в строку браузера; «К журналу»
    и крестик окна его снимают, а история браузера не растёт;
  • статья, открытая сама по себе (без калькулятора, который ссылку примет),
    кнопку не показывает — так она выглядит в прежней версии в бою.
На 390 и 1440 px.
"""
import functools, http.server, json, os, pathlib, re, socketserver, sys, threading
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
СТАТЬЯ = (справка.ПАПКА / "release--2.5.12.html").read_text(encoding="utf-8").strip("\n")
ЦЕНЫ = {"pricing_projects": [{"product": "frame", "sort": 1, "slug": "проба", "name": "Проба 6×4",
        "price_100": 100000, "price_150": 150000, "price_200": 200000, "floors": 1, "roof_type": "двускатная",
        "warm": True, "open_area": 10, "closed_area": 20, "facade_area": 60, "paint_area": 60, "roof_area": 40}],
        "pricing_matrix": [], "pricing_options": [], "pricing_sections": []}
# Без входа: сессии нет, а «вход» проба делает сама, вызывая подписчика.
БЕЗ_ВХОДА = """(function () {
  var исх = window.supabase.createClient;
  window.supabase.createClient = function () {
    var к = исх.apply(this, arguments), сессия = null;
    window.__ЗАПРОСЫ_СТАТЕЙ = 0;
    var from = к.from.bind(к);
    к.from = function (т) { if (т === 'app_docs') window.__ЗАПРОСЫ_СТАТЕЙ++; return from(т); };
    к.auth.getSession = function () { return Promise.resolve({ data: { session: сессия }, error: null }); };
    к.auth.onAuthStateChange = function (об) {
      window.__ВОЙТИ = function () { к.auth.getUser().then(function (r) {
        сессия = { user: r.data.user, access_token: 'проба', refresh_token: 'проба' }; об('SIGNED_IN', сессия); }); };
      return { data: { subscription: { unsubscribe: function () {} } } };
    };
    return к;
  };
})();"""
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
        def log_message(self, *а): pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def ряды():
    р = [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"], "staff_only": ч["staff_only"], "html": ч["html"]}
         for ч in справка.части("manual") if not ч["staff_only"]]
    р.append({"doc": "release", "part": "2.5.12", "ord": 0, "staff_only": False, "html": СТАТЬЯ})
    return р


def страница(бр, ш, вход=True):
    конт = бр.new_context(viewport={"width": ш, "height": 900})
    стр = конт.new_page()
    стр.ошибки = []
    стр.on("pageerror", lambda e: стр.ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    if not вход:
        стр.add_init_script(БЕЗ_ВХОДА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\nwindow.__ТАБЛИЦЫ.app_docs = "
                        + json.dumps(ряды(), ensure_ascii=False) + ";\nObject.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(ЦЕНЫ, ensure_ascii=False) + ");")
    # Буфер обмена: запись перехватывается, чтобы прочитать, что туда легло.
    стр.add_init_script("""(() => { window.__БУФЕР = null;
      const пост = (т) => { try { window.top.__БУФЕР = т; } catch (e) {} return Promise.resolve(); };
      try { Object.defineProperty(navigator, 'clipboard', { value: { writeText: пост }, configurable: true }); } catch (e) {} })();""")
    return конт, стр


def состояние(стр):
    return стр.evaluate("""() => {
      const ов = document.getElementById('manualOverlay'), к = document.getElementById('manualFrame');
      let статья = false, кнопка = null;
      try { const д = к.contentDocument; статья = !!(д && д.querySelector('h1') && /2\\.5\\.12/.test(д.querySelector('h1').textContent));
        const б = д && д.getElementById('shareBtn'); if (б) { const р = б.getBoundingClientRect(); кнопка = { видна: !б.hidden && р.width > 0, р: [р.left, р.top, р.right, р.bottom] }; } } catch (e) {}
      const вход = document.getElementById('loginScreen');
      return { окно: !!ов && ов.style.display === 'block', статья, кнопка, хэш: location.hash, история: history.length,
               экранВхода: !!вход && getComputedStyle(вход).display !== 'none' && вход.getBoundingClientRect().height > 0 };
    }""")


def ждать(стр, условие, раз=40):
    for _ in range(раз):
        стр.wait_for_timeout(200)
        if стр.evaluate(условие):
            return True
    return False


СТАТЬЯ_ОТКРЫТА = """() => { try { const д = document.getElementById('manualFrame').contentDocument;
  return document.getElementById('manualOverlay').style.display === 'block' && !!д.getElementById('shareBtn')
    && /2\\.5\\.12/.test(д.querySelector('h1').textContent); } catch (e) { return false; } }"""


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    адрес = f"http://127.0.0.1:{порт}/index.html#release=2.5.12"

    # ── вошедший: ссылка открывает статью ─────────────────────────────────────
    конт, стр = страница(бр, ш)
    стр.goto(адрес, wait_until="load")
    if not ждать(стр, СТАТЬЯ_ОТКРЫТА):
        плохо(f"{н} вошедший по ссылке: статья не открылась — {состояние(стр)}"); конт.close(); return
    стр.wait_for_timeout(500)
    с = состояние(стр)
    if с["хэш"] != "#release=2.5.12":
        плохо(f"{н} вошедший по ссылке: адрес в строке стал {с['хэш']!r}")
    if not (с["кнопка"] and с["кнопка"]["видна"]):
        плохо(f"{н} в статье нет видимой «Скопировать ссылку»")
    # Место и вес кнопки: в строке надзаголовка, не налезает на него, в кадре,
    # поле нажатия не меньше 32 px по высоте.
    м = стр.frame_locator("#manualFrame").locator("body").evaluate("""() => {
      const б = document.getElementById('shareBtn'), т = document.querySelector('.tagrow .tag');
      const рб = б.getBoundingClientRect(), рт = т.getBoundingClientRect(), п = getComputedStyle(б, '::before');
      return { зазор: Math.round(рб.left - рт.right), одинРяд: рб.top < рт.bottom && рб.bottom > рт.top,
               справа: Math.round(document.documentElement.clientWidth - рб.right), вКадре: рб.right <= document.documentElement.clientWidth,
               поле: Math.round(рб.height - 2 * (parseFloat(п.top) || 0)), высота: Math.round(рб.height), шрифт: parseFloat(getComputedStyle(б).fontSize) };
    }""")
    print(н, "кнопка:", м)
    if not м["вКадре"]:
        плохо(f"{н} кнопка ссылки выходит за край статьи")
    if м["одинРяд"] and м["зазор"] < 12:
        плохо(f"{н} кнопка ссылки прижата к надзаголовку: {м['зазор']} px")
    if м["поле"] < 32:
        плохо(f"{н} поле нажатия кнопки ссылки {м['поле']} px — меньше 32")
    if м["высота"] > 24:
        плохо(f"{н} кнопка ссылки раздута до {м['высота']} px — вес второстепенный")
    # Копирование.
    кадр = стр.frame_locator("#manualFrame")
    кадр.locator("#shareBtn").click()
    стр.wait_for_timeout(300)
    буфер = стр.evaluate("() => window.__БУФЕР")
    if буфер != адрес:
        плохо(f"{н} в буфер легло {буфер!r}, ждали {адрес!r}")
    подпись = кадр.locator("#shareTxt").text_content()
    if подпись != "Ссылка скопирована":
        плохо(f"{н} после нажатия подпись {подпись!r}")
    стр.screenshot(path=f"/tmp/release_link_{ш}.png")
    # «К журналу» снимает адрес, статья из журнала ставит его снова, крестик снимает.
    история = стр.evaluate("() => history.length")
    кадр.locator("button.back").click()
    ждать(стр, "() => { try { return !!document.getElementById('manualFrame').contentDocument.getElementById('ch-updates'); } catch (e) { return false; } }")
    if стр.evaluate("() => location.hash"):
        плохо(f"{н} «К журналу» не снял адрес статьи: {стр.evaluate('() => location.hash')!r}")
    стр.evaluate("() => открытьСтатьюВыпуска('2.5.12')")
    ждать(стр, СТАТЬЯ_ОТКРЫТА)
    if стр.evaluate("() => location.hash") != "#release=2.5.12":
        плохо(f"{н} статья из журнала не поставила адрес в строку браузера")
    стр.evaluate("() => closeManual()")
    if стр.evaluate("() => location.hash"):
        плохо(f"{н} крестик не снял адрес статьи")
    if стр.evaluate("() => history.length") != история:
        плохо(f"{н} история браузера выросла: переходы по статьям листались бы «Назад»")
    if стр.ошибки:
        плохо(f"{н} ошибки скрипта: {стр.ошибки}")
    конт.close()

    # ── невошедший: экран входа, после входа — статья ─────────────────────────
    конт, стр = страница(бр, ш, вход=False)
    стр.goto(адрес, wait_until="load")
    стр.wait_for_timeout(2500)
    с = состояние(стр)
    запросов = стр.evaluate("() => window.__ЗАПРОСЫ_СТАТЕЙ")
    if not с["экранВхода"] or с["окно"] or с["статья"]:
        плохо(f"{н} невошедший по ссылке: {с}")
    if запросов:
        плохо(f"{н} невошедший: к таблице статей ушло {запросов} запросов")
    стр.evaluate("() => window.__ВОЙТИ()")
    if not ждать(стр, СТАТЬЯ_ОТКРЫТА, 60):
        плохо(f"{н} после входа статья не открылась — {состояние(стр)}")
    if стр.ошибки:
        плохо(f"{н} невошедший: ошибки скрипта: {стр.ошибки}")
    конт.close()

    # ── статья сама по себе: кнопки нет ───────────────────────────────────────
    конт = бр.new_context(viewport={"width": ш, "height": 900})
    стр = конт.new_page()
    стр.set_content(СТАТЬЯ)
    стр.wait_for_timeout(300)
    if стр.evaluate("() => { const б = document.getElementById('shareBtn'); return !!б && !б.hidden && б.getBoundingClientRect().width > 0; }"):
        плохо(f"{н} статья без калькулятора показывает «Скопировать ссылку» — в прежней версии она вела бы в никуда")
    конт.close()


def main():
    с, порт = сервер()
    with sync_playwright() as p:
        бр = p.chromium.launch(executable_path=хром())
        for ш in (390, 1440):
            прогон(бр, порт, ш)
        бр.close()
    с.shutdown()
    if НАХОДКИ:
        print("\nНАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("\nЧисто: ссылка на статью открывает её вошедшему и ждёт входа у невошедшего, копируется из статьи "
          "тем же адресом, стоит в строке браузера, пока статья открыта, и снимается без следа в истории — на 390 и 1440.")


if __name__ == "__main__":
    main()
