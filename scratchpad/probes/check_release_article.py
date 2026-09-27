#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Статья о выпуске: ссылка в журнале, окно справки, цвет калькулятора.

Константин 27.09.2026, снимком карточки v2.5.12 в журнале обновлений:
«Ссылку на статью к версии 2.5.12 внедри сюда. Цвет оформления статьи сделай
под цветовую схему калькулятора, также как справку».

Проба держит, на 390 и 1440 px:
  • в карточке v2.5.12 видна ссылка на статью (без калькулятора, который её
    раскрывает, она спрятана — справка одна на тест и бой);
  • нажатие открывает статью в том же окне: заголовок «Версия 2.5.12», все
    снимки загрузились с assets/releases/2.5.12/ (ширина картинки не ноль);
  • статья в цвете калькулятора: у бирюзы боковое меню бирюзовое, у
    «Зелёного-графита» — графитовое; ночью фон тёмный;
  • переходы по разделам не уводят кадр со статьи (в srcdoc «#раздел»
    открыл бы в кадре сам калькулятор);
  • пункты разделов пронумерованы «1.1…4.1»; на компьютере они подпунктами в
    меню, на телефоне — в панели «Оглавление», которая выезжает справа, как в
    базе знаний, закрывается после перехода и уходит свайпом вправо; нажатие по подпункту
    приводит к его пункту и отмечает его в меню (Константин, 27.09.2026:
    «внутри в разделах подпункты поставь»);
  • «Журнал обновлений» наверху статьи возвращает в журнал.

    python3 check_release_article.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
СТАТЬЯ = (справка.ПАПКА / "release--2.5.12.html").read_text(encoding="utf-8").strip("\n")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
ЦЕНЫ = {"pricing_projects": [{"product": "frame", "sort": 1, "slug": "проба", "name": "Проба 6×4",
        "price_100": 100000, "price_150": 150000, "price_200": 200000, "floors": 1, "roof_type": "двускатная",
        "warm": True, "open_area": 10, "closed_area": 20, "facade_area": 60, "paint_area": 60, "roof_area": 40}],
        "pricing_matrix": [], "pricing_options": [], "pricing_sections": []}


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


def ждать_кадр(стр, признак):
    for _ in range(40):
        стр.wait_for_timeout(200)
        try:
            if стр.frame_locator("#manualFrame").locator(признак).count():
                return стр.frame_locator("#manualFrame")
        except Exception:
            pass
    return None


def прогон(бр, порт, ш, тон, ночь):
    н = f"[{ш} {тон or 'бирюза'}{' ночь' if ночь else ''}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\nwindow.__ТАБЛИЦЫ.app_docs = "
                        + json.dumps(ряды(), ensure_ascii=False) + ";\nObject.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(ЦЕНЫ, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""([тон, ночь]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      if (тон) applyTone(тон, false); document.body.classList.toggle('dark', ночь); try { localStorage.setItem('banya_dark', ночь ? '1' : '0'); } catch (e) {} }""", [тон, ночь])
    стр.evaluate("async () => { await openManual(); closeManual(); }"); стр.wait_for_timeout(300)
    стр.evaluate("() => openManual()")
    кадр = ждать_кадр(стр, "#ch-updates")
    if not кадр:
        плохо(f"{н} справка не открылась"); стр.close(); return
    стр.wait_for_timeout(700)
    ссылка = кадр.locator('[data-release="2.5.12"]')
    видна = ссылка.count() and ссылка.evaluate("э => getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().height > 0")
    if not видна:
        плохо(f"{н} в карточке v2.5.12 нет видимой ссылки на статью"); стр.close(); return
    ссылка.locator("[role=link]").click()
    кадр = ждать_кадр(стр, "h1")
    if not кадр:
        плохо(f"{н} статья не открылась"); стр.close(); return
    стр.wait_for_timeout(1200)
    р = кадр.locator("body").evaluate("""async () => {
      await Promise.all([...document.images].map(и => и.complete ? 0 : new Promise(r => { и.onload = и.onerror = r; })));
      const sb = document.querySelector('.sb');
      return { заголовок: (document.querySelector('h1') || {}).textContent || '',
        снимков: document.images.length, пустых: [...document.images].filter(и => !и.naturalWidth).map(и => и.getAttribute('src')),
        меню: sb ? getComputedStyle(sb).backgroundColor : '', фон: getComputedStyle(document.body).backgroundColor,
        тон: document.documentElement.dataset.tone || '', тёмная: document.body.classList.contains('dark'),
        скролл: document.documentElement.scrollWidth > innerWidth + 1 };
    }""")
    print("  " + н, json.dumps(р, ensure_ascii=False))
    if "2.5.12" not in р["заголовок"]:
        плохо(f"{н} открылась не статья: «{р['заголовок']}»")
    if р["снимков"] < 8 or р["пустых"]:
        плохо(f"{н} снимки не загрузились: {р['пустых'][:3]} из {р['снимков']}")
    if р["скролл"]:
        плохо(f"{н} статья шире окна")
    if ш >= 900:
        ждём = "rgb(36, 39, 31)" if тон == "bmsk" else ("rgb(30, 108, 114)" if not тон else None)
        if ждём and р["меню"] != ждём:
            плохо(f"{н} боковое меню статьи не в цвете калькулятора: {р['меню']}, ждали {ждём}")
    if тон and р["тон"] != тон:
        плохо(f"{н} статья не получила тон калькулятора ({р['тон']!r})")
    if ночь and (not р["тёмная"] or р["фон"] in ("rgb(255, 255, 255)", "rgb(240, 246, 246)")):
        плохо(f"{н} ночью статья светлая: {р['фон']}")
    стр.screenshot(path=str(СНИМКИ / f"release-{ш}-{тон or 'teal'}{'-n' if ночь else ''}.png"))
    # подпункты: номера «1.1…»; на компьютере — вложенное меню, на телефоне — панель
    # «Оглавление» справа, как в базе знаний, уходящая свайпом вправо
    п = кадр.locator("body").evaluate('''() => {
      const номера = [...document.querySelectorAll('.it h3 .num')].map(н => н.textContent);
      const вид = э => !!э && getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().height > 0;
      const к = document.getElementById('tocBtn'), кр = к ? к.getBoundingClientRect() : null;
      return { номера, подменю: document.querySelectorAll('.sb .sb-s').length, меню: вид(document.querySelector('.sb')),
               кнопка: вид(к), кнопкаВысота: кр ? Math.round(кр.height) : 0, вПанели: document.querySelectorAll('#tocList a.s').length };
    }''')
    if len(п["номера"]) != 12 or п["номера"][0] != "1.1" or п["номера"][-1] != "4.1":
        плохо(f"{н} пункты разделов не пронумерованы: {п['номера'][:4]}…")
    if ш >= 900 and (not п["меню"] or п["подменю"] != 12):
        плохо(f"{н} в меню статьи нет подпунктов разделов: {п['подменю']}")
    до = None
    if ш < 720:
        if not п["кнопка"] or п["кнопкаВысота"] < 36 or п["вПанели"] != 12:
            плохо(f"{н} на телефоне нет «Оглавления» с 12 подпунктами: {п}")
        else:
            # крестик окна справки стоит поверх кадра — кнопка не должна под ним прятаться
            кр = кадр.locator("#tocBtn").bounding_box(); кх = стр.locator("#manualCloseBtn").bounding_box()
            if кр and кх and кр["x"] + кр["width"] > кх["x"] - 4 and кр["y"] < кх["y"] + кх["height"] and кр["y"] + кр["height"] > кх["y"]:
                плохо(f"{н} «Оглавление» заходит под крестик окна справки: {кр} / {кх}")
            кадр.locator("#tocBtn").click(); стр.wait_for_timeout(450)
            справа = кадр.locator("body").evaluate("() => { const к = document.getElementById('tocPanel').getBoundingClientRect(); return { открыта: document.getElementById('tocPanel').classList.contains('open'), справа: Math.round(innerWidth - к.right), слева: Math.round(к.left) }; }")
            if not справа["открыта"] or abs(справа["справа"]) > 1 or справа["слева"] < 30:
                плохо(f"{н} «Оглавление» не выехало панелью справа: {справа}")
            кадр.locator("#tocList a[data-to='spec-2']").click(); стр.wait_for_timeout(900)
            до = кадр.locator("body").evaluate("() => Math.round(document.getElementById('spec-2').getBoundingClientRect().top)")
            if кадр.locator(".toc-panel.open").count():
                плохо(f"{н} после перехода «Оглавление» осталось открытым")
            # свайп вправо закрывает
            кадр.locator("#tocBtn").click(); стр.wait_for_timeout(450)
            кадр.locator("body").evaluate('''async () => {
              const п = document.getElementById('tocPanel'), к = п.getBoundingClientRect(), y = к.top + 200;
              const т = x => new Touch({ identifier: 1, target: п, clientX: x, clientY: y });
              п.dispatchEvent(new TouchEvent('touchstart', { touches: [т(к.left + 40)], bubbles: true }));
              for (const x of [к.left + 90, к.left + 160, к.left + 240]) п.dispatchEvent(new TouchEvent('touchmove', { touches: [т(x)], bubbles: true }));
              п.dispatchEvent(new TouchEvent('touchend', { touches: [], bubbles: true }));
              await new Promise(r => setTimeout(r, 400));
            }''')
            if кадр.locator(".toc-panel.open").count():
                плохо(f"{н} свайп вправо не закрыл «Оглавление»")
    else:
        цель = ".sb-s[data-to='spec-2']"
        if not кадр.locator(цель).count():
            плохо(f"{н} подпункта 2.2 нет в меню")
        else:
            кадр.locator(цель).click(); стр.wait_for_timeout(900)
            до = кадр.locator("body").evaluate("() => Math.round(document.getElementById('spec-2').getBoundingClientRect().top)")
            if not кадр.locator(".sb-s.on[data-to='spec-2']").count():
                плохо(f"{н} в меню не отмечен подпункт 2.2, к которому прокрутили")
    if до is not None and not (-5 <= до <= 60):
        плохо(f"{н} подпункт 2.2 не прокрутился к своему пункту: верх на {до} px")
    # переход по разделу не уводит кадр
    if ш >= 900:
        кадр.locator('.sb-a[data-to="log"]').click(); стр.wait_for_timeout(700)
        ещё = кадр.locator("body").evaluate("() => ({ h1: !!document.querySelector('h1'), y: Math.round(scrollY) })")
        if not ещё["h1"] or ещё["y"] < 200:
            плохо(f"{н} переход к разделу увёл кадр или не прокрутил: {ещё}")
    # назад к журналу
    кадр.locator("button.back").click()
    кадр = ждать_кадр(стр, "#ch-updates.on")
    if not кадр:
        плохо(f"{н} «Журнал обновлений» не вернул в журнал")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тон, ночь in (("", False), ("bmsk", False), ("bmsk", True)):
                    прогон(бр, порт, ш, тон, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в карточке v2.5.12 ссылка на статью; статья открывается в окне справки со всеми снимками, "
          "в цвете калькулятора — бирюзой, «Зелёным-графитом» и ночью; разделы листаются на месте, "
          "«Журнал обновлений» возвращает в журнал — на 390 и 1440.")


if __name__ == "__main__":
    главная()
