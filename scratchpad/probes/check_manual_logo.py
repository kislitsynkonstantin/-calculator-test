#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Логотип «Баня МСК» в цвет тона — в меню справки и статей о выпуске.

Константин 14.10.2026, ответом на вопрос «поставить в справку такой же
логотип, как в базе знаний?»: «Логотип везде да поставь в цвет темы».

Справка и статьи лежат в базе одни на тест и бой, поэтому логотип дают не
они, а калькулятор (`логотипМенюСправки`). Проба держит, через калькулятор на
1440 и 390 px, в «Бирюзовом», «Зелёном-графите» днём и ночью и в «Синем»:
  • в меню справки и статьи 2.5.17 — логотип, плашки «БМСК» нет;
  • логотип перекрашен под тон калькулятора: у «Бирюзового» и «Зелёного-
    графита» разные картинки, у тона — не исходная;
  • крыша видна на заливке меню — основной цвет крыши даёт с фоном не меньше
    3 : 1 (в «Бирюзовом» крыша того же цвета, что меню, без подъёма 1,6 : 1);
  • логотип внутри меню, не заходит на заголовок под ним (зазор от 4 px);
  • калькулятор без этой функции (BM_PROD=1, бой до 2.5.18) — в меню прежняя
    плашка «БМСК», логотипа нет, ошибок нет.

    python3 check_manual_logo.py
    BM_ROOT=/home/user/calculator BM_PROD=1 python3 check_manual_logo.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ЦЕНЫ = (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8")
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
БОЙ = os.environ.get("BM_PROD") == "1"
ВЕРСИЯ = "2.5.17"
СТАТЬЯ = (справка.ПАПКА / f"release--{ВЕРСИЯ}.html").read_text(encoding="utf-8").strip("\n")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


def ряды():
    р = [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"], "staff_only": ч["staff_only"], "html": ч["html"]}
         for ч in справка.части("manual") if not ч["staff_only"]]
    р.append({"doc": "release", "part": ВЕРСИЯ, "ord": 0, "staff_only": False, "html": СТАТЬЯ})
    return р


ЗАМЕР = """async () => {
  const д = document, лого = д.getElementById('sbLogo'), плашка = д.getElementById('sbBadge');
  const вид = э => !!э && getComputedStyle(э).display !== 'none' && э.getClientRects().length > 0;
  const меню = лого && лого.closest('.sb');
  const rgb = s => (/rgba?\\(([^)]+)\\)/.exec(s) || [0, '0,0,0'])[1].split(',').slice(0, 3).map(Number);
  const я = ([r, g, b]) => { const к = v => (v /= 255) <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; return .2126 * к(r) + .7152 * к(g) + .0722 * к(b); };
  const к = (а, б) => (Math.max(а, б) + .05) / (Math.min(а, б) + .05);
  const р = { лого: вид(лого), плашка: вид(плашка), src: лого && лого.src ? лого.src.slice(0, 22) : '', длина: лого && лого.src ? лого.src.length : 0 };
  if (!р.лого) return р;
  if (!лого.complete) await new Promise(ok => { лого.onload = лого.onerror = ok; });
  const фон = rgb(getComputedStyle(меню).backgroundColor);
  // Крыша — цветные пиксели картинки (не белые и не прозрачные); берём самый частый цвет.
  const х = д.createElement('canvas'); х.width = лого.naturalWidth; х.height = лого.naturalHeight;
  const кн = х.getContext('2d'); кн.drawImage(лого, 0, 0);
  const пк = кн.getImageData(0, 0, х.width, х.height).data, счёт = new Map();
  for (let i = 0; i < пк.length; i += 4) {
    if (пк[i + 3] < 200) continue;
    const M = Math.max(пк[i], пк[i + 1], пк[i + 2]), m = Math.min(пк[i], пк[i + 1], пк[i + 2]);
    if (M - m < 25) continue;
    const ключ = пк[i] + ',' + пк[i + 1] + ',' + пк[i + 2]; счёт.set(ключ, (счёт.get(ключ) || 0) + 1);
  }
  const главный = [...счёт].sort((а, б) => б[1] - а[1])[0];
  const крыша = главный ? главный[0].split(',').map(Number) : null;
  const л = лого.getBoundingClientRect(), мн = меню.getBoundingClientRect();
  const под = лого.parentElement.nextElementSibling || (лого.parentElement.parentElement.querySelector('h1, .t'));
  const п = под ? под.getBoundingClientRect() : null;
  р.отпечаток = лого.src.length + ':' + лого.src.slice(-40);
  р.крыша = крыша; р.фон = фон; р.контраст = крыша ? Math.round(к(я(крыша), я(фон)) * 100) / 100 : 0;
  р.внутри = л.left >= мн.left - .5 && л.right <= мн.right + .5 && л.height > 10;
  р.зазор = п ? Math.round(п.top - л.bottom) : null;
  return р;
}"""


def кадр_с(стр, признак):
    for _ in range(50):
        стр.wait_for_timeout(200)
        try:
            if стр.frame_locator("#manualFrame").locator(признак).count():
                return стр.frame_locator("#manualFrame")
        except Exception:
            pass
    return None


socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])
отпечатки = {}

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш in (1440, 390):
        for тон, ночь in (("", False), ("bmsk", False), ("bmsk", True), ("blue", False)):
            н = f"[{ш} {тон or 'бирюза'}{' ночь' if ночь else ''}]"
            стр = бр.new_page(viewport={"width": ш, "height": 900}, device_scale_factor=2 if ш == 1440 else 1)
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
            стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + ЦЕНЫ + ");\n"
                                "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(ряды(), ensure_ascii=False) + ";")
            стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("""([тон, ночь]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
              applyTone(тон || 'teal', false); document.body.classList.toggle('dark', ночь); }""", [тон, ночь])
            стр.wait_for_timeout(500)
            # Статья на телефоне меню не показывает (вместо него «Оглавление»),
            # поэтому там её не меряем. Статья открывается из открытой справки,
            # как переходом из журнала.
            for что, открыть, признак in (("справка", "() => openManual()", ".ch.on"),
                                          ("статья", f"() => открытьСтатьюВыпуска('{ВЕРСИЯ}')", "#tocList")):
                if что == "статья" and ш < 720:
                    continue
                стр.evaluate(открыть)
                кадр = кадр_с(стр, признак)
                if not кадр:
                    факт(False, f"{н} {что}: окно не открылось"); continue
                стр.wait_for_timeout(1200)
                if ш < 720:   # меню справки на телефоне выдвижное — выдвигаем, как кнопкой
                    кадр.locator("body").evaluate("() => { const м = document.querySelector('.sb'); if (м) м.classList.add('mob-open'); }")
                    стр.wait_for_timeout(400)
                р = кадр.locator("body").evaluate("(_, з) => (eval('(' + з + ')'))()", ЗАМЕР)
                if БОЙ:
                    факт(р["плашка"] and not р["лого"], f"{н} {что}, бой: плашка «БМСК», логотипа нет: {р}")
                    continue
                факт(р["лого"] and not р["плашка"] and р["src"].startswith("data:image/png"), f"{н} {что}: логотип вместо плашки: {р.get('src')}, плашка {р['плашка']}")
                if not р["лого"]:
                    continue
                факт(р["контраст"] >= 3, f"{н} {что}: крыша видна на меню — {р['крыша']} на {р['фон']}: {р['контраст']} : 1")
                факт(р["внутри"] and (р["зазор"] is None or р["зазор"] >= 4), f"{н} {что}: логотип в меню, до заголовка {р['зазор']} px")
                отпечатки[(что, тон)] = р["отпечаток"]
                if ш == 1440 and not ночь:
                    стр.screenshot(path=str(СНИМКИ / f"logo-{что}-{тон or 'teal'}.png"))
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                факт(False, f"{н} ошибка страницы: {о[:160]}")
            стр.close()
    бр.close()
с.shutdown()

if not БОЙ:
    for что in ("справка", "статья"):
        а, б = отпечатки.get((что, "")), отпечатки.get((что, "bmsk"))
        факт(а and б and а != б, f"{что}: у «Бирюзового» и «Зелёного-графита» логотипы разные")

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: " + ("в бою — прежняя плашка «БМСК»." if БОЙ else
      "в меню справки и статьи — логотип в цвет тона, крыша видна на заливке, плашки нет; 1440 и 390, четыре вида."))
