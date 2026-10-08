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
import re, functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
# Версия статьи: BM_RELEASE=2.5.13 python3 check_release_article.py
ВЕРСИЯ = os.environ.get("BM_RELEASE", "2.5.12")
СТАТЬЯ = (справка.ПАПКА / f"release--{ВЕРСИЯ}.html").read_text(encoding="utf-8").strip("\n")
# Число пунктов берётся из самой статьи: пункт добавили — проба не требует правки.
ПУНКТОВ = len(re.findall(r'<div class="it">\s*<h3', СТАТЬЯ))
# Разделы у каждой статьи свои: переходы проверяются по разделам самой статьи
# (у 2.5.14 нет «Журнала действий», 08.10.2026). Подпункт — второй пункт
# раздела «spec», если он есть, иначе второго раздела; раздел для перехода — «log»
# или последний.
СЕКЦИИ = re.findall(r'<section class="grp" id="([\w-]+)"', СТАТЬЯ)
ПОДПУНКТ = ("spec" if "spec" in СЕКЦИИ else СЕКЦИИ[1]) + "-2"
РАЗДЕЛ = "log" if "log" in СЕКЦИИ else СЕКЦИИ[-1]
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
    р.append({"doc": "release", "part": ВЕРСИЯ, "ord": 0, "staff_only": False, "html": СТАТЬЯ})
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


def раскрыть_выпуск(кадр):
    """Карточка выпуска может быть не первой — над ней карточка следующей версии
    «на тесте», и раскрыта по умолчанию та. Раскрываем её, как менеджер."""
    кадр.locator("body").evaluate('''(_, в) => { const к = [...document.querySelectorAll('#ch-updates .upd')]
      .find(у => (у.querySelector('.upd-ver') || {}).textContent === 'v' + в); if (к && !к.classList.contains('open')) к.querySelector('.upd-head').click(); }''', ВЕРСИЯ)


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
      applyTone(тон || 'teal', false); document.body.classList.toggle('dark', ночь); try { localStorage.setItem('banya_dark', ночь ? '1' : '0'); } catch (e) {} }""", [тон, ночь])
    стр.evaluate("async () => { await openManual(); closeManual(); }"); стр.wait_for_timeout(300)
    стр.evaluate("() => openManual()")
    кадр = ждать_кадр(стр, "#ch-updates")
    if not кадр:
        плохо(f"{н} справка не открылась"); стр.close(); return
    стр.wait_for_timeout(700)
    раскрыть_выпуск(кадр); стр.wait_for_timeout(300)
    ссылка = кадр.locator(f'[data-release="{ВЕРСИЯ}"]')
    видна = ссылка.count() and ссылка.evaluate("э => getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().height > 0")
    if not видна:
        плохо(f"{н} в карточке v{ВЕРСИЯ} нет видимой ссылки на статью"); стр.close(); return
    # Значок статьи в шапке свёрнутой карточки (Константин, 27.09.2026): виден
    # только свёрнутой, стоит справа от счёта правок, поле нажатия 44 px, нажатие
    # открывает статью, а не раскрывает карточку. Без класса от калькулятора
    # (так в бою, где статей ещё нет) его нет вовсе.
    знач = кадр.locator("body").evaluate("""async (_, в) => {
      const ждать = мс => new Promise(r => setTimeout(r, мс));
      const к = document.querySelector('[data-release-ico="' + в + '"]').closest('.upd'), ш = к.querySelector('.upd-head');
      const и = к.querySelector('.upd-art'), с = к.querySelector('.upd-chev');
      const вид = э => getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().width > 0;
      const открытВид = вид(и);
      ш.click(); await ждать(250);
      const свёрнут = !к.classList.contains('open');
      const а = и.getBoundingClientRect(), б = с.getBoundingClientRect(), ш2 = ш.getBoundingClientRect(), п = getComputedStyle(и, '::before');
      const состояние = к.querySelector('.upd-state').getBoundingClientRect(), счёт = к.querySelector('.upd-count').getBoundingClientRect();
      const глиф = и.querySelector('svg').getBoundingClientRect();
      const r = { открытВид, свёрнут, виден: вид(и), зазорСтрелка: Math.round(б.left - а.right), доКраяШапки: Math.round(ш2.right - б.right),
        поле: Math.round(а.height - 2 * (parseFloat(п.top) || 0)), отСчёта: Math.round(глиф.left - счёт.right), доМетки: Math.round(состояние.left - глиф.right),
        стрелкаСправа: Math.round(ш2.right - б.right) };
      // Шапка — одной строкой, и с запасом по ширине: в пробе нет фирменных
      // шрифтов, а Unbounded и Geologica шире подменных — на снимке 390 с ними
      // стрелка ушла на вторую строку, а проба этого не видела.
      const дети = [...ш.children].filter(э => getComputedStyle(э).display !== 'none'), сш = getComputedStyle(ш);
      r.строк = new Set(дети.map(э => Math.round((э.getBoundingClientRect().top + э.getBoundingClientRect().bottom) / 8))).size;
      r.запас = Math.round(ш.clientWidth - parseFloat(сш.paddingLeft) - parseFloat(сш.paddingRight)
        - дети.reduce((s, э) => s + э.getBoundingClientRect().width, 0) - (дети.length - 1) * parseFloat(сш.columnGap));
      к.classList.remove('upd-art-on'); r.безКласса = вид(и); к.classList.add('upd-art-on');
      return r; }""", ВЕРСИЯ)
    if знач["открытВид"]:
        плохо(f"{н} значок статьи виден и в развёрнутой карточке, рядом с блоком «Журнал выпуска»: {знач}")
    if not знач["свёрнут"] or not знач["виден"]:
        плохо(f"{н} в свёрнутой карточке v{ВЕРСИЯ} нет значка статьи: {знач}")
    elif not (6 <= знач["отСчёта"] <= 18) or not (6 <= знач["доМетки"] <= 18) or знач["поле"] < 44 or знач["стрелкаСправа"] > 8:
        # справа от счёта правок, перед меткой (Константин, 27.09.2026), стрелка — у правого края
        плохо(f"{н} значок статьи не между счётом правок и меткой, поле меньше 44 px или стрелка не у края: {знач}")
    if знач.get("строк", 1) > 1 or знач.get("запас", 99) < 30:
        плохо(f"{н} шапка свёрнутой карточки v{ВЕРСИЯ} со значком не в одну строку или впритык (запас {знач.get('запас')} px без фирменных шрифтов, нужно от 30): {знач}")
    if знач["безКласса"]:
        плохо(f"{н} значок статьи виден без класса от калькулятора — в бою он появился бы без статьи: {знач}")
    кадр.locator(f'[data-release-ico="{ВЕРСИЯ}"]').click()
    if ждать_кадр(стр, "h1"):
        стр.evaluate("() => { const ф = document.getElementById('manualFrame'); ф.contentWindow.postMessage({ type: 'backToManual' }, '*'); }")
        стр.evaluate("() => openManual()"); кадр = ждать_кадр(стр, "#ch-updates"); стр.wait_for_timeout(700)
        раскрыть_выпуск(кадр); стр.wait_for_timeout(300)
        ссылка = кадр.locator(f'[data-release="{ВЕРСИЯ}"]')
    else:
        плохо(f"{н} нажатие по значку статьи статью не открыло")
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
    if ВЕРСИЯ not in р["заголовок"]:
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
    # Последний номер — из самой статьи, как и число пунктов: раздел добавили —
    # проба не ждёт прежнего «4.1» (27.09.2026 появился раздел «Оформление»).
    разделы = re.findall(r'<section class="grp".*?</section>', СТАТЬЯ, re.S)
    последний = (str(len(разделы)) + "." + str(разделы[-1].count('<div class="it">'))) if разделы else "?"
    if len(п["номера"]) != ПУНКТОВ or п["номера"][0] != "1.1" or п["номера"][-1] != последний:
        плохо(f"{н} пункты разделов не пронумерованы: {п['номера'][:4]}…")
    if ш >= 900 and (not п["меню"] or п["подменю"] != ПУНКТОВ):
        плохо(f"{н} в меню статьи нет подпунктов разделов: {п['подменю']}")
    до = None
    if ш < 720:
        if not п["кнопка"] or п["кнопкаВысота"] < 36 or п["вПанели"] != ПУНКТОВ:
            плохо(f"{н} на телефоне нет «Оглавления» с {ПУНКТОВ} подпунктами: {п}")
        else:
            # крестик окна справки стоит поверх кадра — кнопка не должна под ним прятаться
            кр = кадр.locator("#tocBtn").bounding_box(); кх = стр.locator("#manualCloseBtn").bounding_box()
            if кр and кх and кр["x"] + кр["width"] > кх["x"] - 4 and кр["y"] < кх["y"] + кх["height"] and кр["y"] + кр["height"] > кх["y"]:
                плохо(f"{н} «Оглавление» заходит под крестик окна справки: {кр} / {кх}")
            кадр.locator("#tocBtn").click(); стр.wait_for_timeout(450)
            справа = кадр.locator("body").evaluate("() => { const к = document.getElementById('tocPanel').getBoundingClientRect(); return { открыта: document.getElementById('tocPanel').classList.contains('open'), справа: Math.round(innerWidth - к.right), слева: Math.round(к.left) }; }")
            if not справа["открыта"] or abs(справа["справа"]) > 1 or справа["слева"] < 30:
                плохо(f"{н} «Оглавление» не выехало панелью справа: {справа}")
            кадр.locator(f"#tocList a[data-to='{ПОДПУНКТ}']").click(); стр.wait_for_timeout(900)
            до = кадр.locator("body").evaluate("() => Math.round(document.getElementById('" + ПОДПУНКТ + "').getBoundingClientRect().top)")
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
            # свайп влево из середины статьи открывает — без прокрутки к кнопке
            # (Константин, 27.09.2026); вертикальная прокрутка и жест от самого
            # края панель не трогают.
            жесты = кадр.locator("body").evaluate('''async () => {
              const ждать = мс => new Promise(r => setTimeout(r, мс));
              const п = document.getElementById('tocPanel'), ф = document.getElementById('tocFon');
              const жест = async (x0, y0, шаги) => {
                const цель = document.elementFromPoint(x0, y0) || document.body;
                const т = (x, y) => new Touch({ identifier: 2, target: цель, clientX: x, clientY: y });
                цель.dispatchEvent(new TouchEvent('touchstart', { touches: [т(x0, y0)], bubbles: true }));
                for (const [x, y] of шаги) цель.dispatchEvent(new TouchEvent('touchmove', { touches: [т(x, y)], bubbles: true }));
                цель.dispatchEvent(new TouchEvent('touchend', { touches: [], bubbles: true }));
                await ждать(400);
                const открыта = п.classList.contains('open');
                if (открыта) { ф.click(); await ждать(400); }
                return открыта;
              };
              const y = Math.round(innerHeight / 2), x = Math.round(innerWidth * 0.75);
              return {
                влево: await жест(x, y, [[x - 20, y + 2], [x - 70, y + 4], [x - 140, y + 6]]),
                короткий: await жест(x, y, [[x - 20, y], [x - 40, y]]),
                вертикаль: await жест(x, y, [[x - 6, y - 40], [x - 20, y - 120], [x - 40, y - 200]]),
                сКрая: await жест(innerWidth - 6, y, [[innerWidth - 60, y], [innerWidth - 160, y]]),
                вправо: await жест(Math.round(innerWidth * 0.3), y, [[Math.round(innerWidth * 0.3) + 80, y], [Math.round(innerWidth * 0.3) + 160, y]]),
                середина: Math.round(scrollY),
              };
            }''')
            # Статья в начале — панель встаёт под ряд «К журналу» / «Оглавление»,
            # а не на него: ряд ниже крестика окна, и по одному крестику панель
            # чуть заходила на кнопки (Константин, 27.09.2026, снимок iPhone).
            for сдвиг in (0, 70):
                стр.evaluate("(с) => { document.getElementById('manualOverlay').scrollTop = с; }", сдвиг)
                кадр.locator("body").evaluate("() => window.scrollTo(0, 0)"); стр.wait_for_timeout(200)
                кадр.locator("#tocBtn").evaluate("к => к.click()"); стр.wait_for_timeout(450)
                ряд = кадр.locator("body").evaluate("""() => { const п = document.getElementById('tocPanel').getBoundingClientRect();
                  const к = [document.getElementById('tocBtn'), document.querySelector('.topbar .back')].map(э => э.getBoundingClientRect());
                  return { зазор: Math.round(Math.min(...к.map(б => п.top - б.bottom))), верх: Math.round(п.top) }; }""")
                if ряд["зазор"] < 6:
                    плохо(f"{н} [окно прокручено на {сдвиг}] «Оглавление» в начале статьи ложится на кнопки «К журналу» / «Оглавление»: зазор {ряд['зазор']} px")
                if not сдвиг:
                    стр.screenshot(path=str(СНИМКИ / f"release-toc-{ш}-{тон or 'teal'}{'-n' if ночь else ''}.png"))
                кадр.locator("#tocFon").evaluate("ф => ф.click()"); стр.wait_for_timeout(400)
            стр.evaluate("() => { document.getElementById('manualOverlay').scrollTop = 0; }")
            # Панель — в видимой полосе кадра, ниже крестика окна, со своей
            # прокруткой (Константин, 27.09.2026: панель закрывала крестик и
            # верх, а низ уходил под панель браузера). Safari моделируем так:
            # кадр выше экрана на высоту нижней панели браузера, окно справки
            # прокручено, экран короткий.
            for высота, сдвиг in ((стр.viewport_size["height"], 0), (600, 70)):
                стр.set_viewport_size({"width": ш, "height": высота}); стр.wait_for_timeout(200)
                стр.evaluate("""(сдвиг) => { const к = document.getElementById('manualFrame'), о = document.getElementById('manualOverlay');
                  к.style.minHeight = сдвиг ? (innerHeight + 90) + 'px' : ''; document.getElementById('manualPanel').style.minHeight = к.style.minHeight;
                  о.scrollTop = сдвиг; }""", сдвиг)
                стр.wait_for_timeout(200)
                кадр.locator("#tocBtn").evaluate("к => к.click()"); стр.wait_for_timeout(450)
                г = стр.evaluate("""() => { const к = document.getElementById('manualFrame'), р = к.getBoundingClientRect(), д = к.contentDocument;
                  const п = д.getElementById('tocPanel').getBoundingClientRect(), сп = д.getElementById('tocList');
                  const х = document.getElementById('manualCloseBtn').getBoundingClientRect();
                  сп.scrollTop = сп.scrollHeight; const посл = [...сп.querySelectorAll('a')].pop().getBoundingClientRect();
                  return { верх: р.top + п.top, низ: р.top + п.bottom, экран: innerHeight, крестик: х.bottom, крестикВиден: х.bottom > 0,
                           прокрутка: сп.scrollHeight > сп.clientHeight + 1, последнийНиз: р.top + посл.bottom, последнийВерх: р.top + посл.top }; }""")
                ярлык = f"{н} [экран {высота}, окно прокручено на {сдвиг}]"
                if г["верх"] < 0 or (г["крестикВиден"] and г["верх"] < г["крестик"] + 4):
                    плохо(f"{ярлык} «Оглавление» заходит под крестик окна или за верх экрана: {г}")
                if г["низ"] > г["экран"] + 0.5:
                    плохо(f"{ярлык} низ «Оглавления» уходит за экран: {г}")
                if г["последнийНиз"] > г["низ"] + 0.5 or г["последнийВерх"] < г["верх"]:
                    плохо(f"{ярлык} последний пункт не виден и после прокрутки списка: {г}")
                # строки плотные, но под палец: 32–34 px (было 39)
                # (Константин, 27.09.2026: «интервал между пунктами сделай меньше»);
                # с 2.5.13 — вдвое плотнее, 24–27 px (01.10.2026: «расстояние между
                # пунктами по высоте сделай в 2 раза меньше»)
                мин_, макс_ = (32, 34) if ВЕРСИЯ == "2.5.12" else (24, 27)
                строки = кадр.locator("#tocList a").evaluate_all("сп => сп.map(а => Math.round(а.getBoundingClientRect().height))")
                однострочные = [в for в in строки if в < 40]
                # панель по ширине строк, не шире 290 px, и ни одна строка не переносится
                # (Константин, 27.09.2026: «окно оглавления зачем такое широкое»)
                шир = кадр.locator("#tocPanel").evaluate("п => Math.round(п.getBoundingClientRect().width)")
                if шир > 290 or len(однострочные) != len(строки):
                    плохо(f"{ярлык} «Оглавление» шириной {шир} px или с перенесёнными строками: {строки}")
                if однострочные and (min(однострочные) < мин_ or max(однострочные) > макс_):
                    плохо(f"{ярлык} строки «Оглавления» {min(однострочные)}–{max(однострочные)} px — нужны {мин_}–{макс_}: {строки}")
                if высота == 600 and not г["прокрутка"]:
                    плохо(f"{ярлык} на коротком экране список «Оглавления» не прокручивается: {г}")
                кадр.locator("#tocFon").evaluate("ф => ф.click()"); стр.wait_for_timeout(400)
            стр.evaluate("""() => { const к = document.getElementById('manualFrame'); к.style.minHeight = ''; document.getElementById('manualPanel').style.minHeight = '';
              document.getElementById('manualOverlay').scrollTop = 0; }""")
            стр.set_viewport_size({"width": ш, "height": 900})
            # заголовок панели ведёт к началу статьи и закрывает панель (Константин, 27.09.2026)
            кадр.locator("body").evaluate("() => document.getElementById('spec').scrollIntoView()"); стр.wait_for_timeout(300)
            кадр.locator("#tocBtn").evaluate("к => к.click()"); стр.wait_for_timeout(450)
            кадр.locator("#tocPanel .toc-h").click(); стр.wait_for_timeout(1100)
            нач = кадр.locator("body").evaluate("() => ({ y: Math.round(scrollY), открыта: document.getElementById('tocPanel').classList.contains('open') })")
            if нач["y"] > 30 or нач["открыта"]:
                плохо(f"{н} нажатие по заголовку «Оглавления» не привело к началу статьи: {нач}")
            # Закрытая панель не торчит за край страницы: Safari подгоняет окно справки
            # под ширину содержимого, и торчащая панель делала страницу шире экрана —
            # свайп вбок телефон забирал себе (Константин, 27.09.2026). Safari здесь
            # не запустить, поэтому держим устройство: панель внутри обрезающего слоя,
            # сама страница вбок не прокручивается, жесты вбок отданы странице.
            стр_ = кадр.locator("body").evaluate("""() => { const п = document.getElementById('tocPanel'), с = п.parentElement;
              return { слой: getComputedStyle(с).overflow, фикс: getComputedStyle(с).position, панель: getComputedStyle(п).position,
                       вбок: getComputedStyle(document.documentElement).overflowX, жест: getComputedStyle(document.body).touchAction }; }""")
            if стр_["слой"] != "hidden" or стр_["фикс"] != "fixed" or стр_["панель"] != "absolute" or стр_["вбок"] not in ("hidden", "clip") or "pan-y" not in стр_["жест"]:
                плохо(f"{н} закрытая панель «Оглавления» может торчать за край страницы: {стр_}")
            if not жесты["влево"]:
                плохо(f"{н} свайп влево из середины статьи не выдвинул «Оглавление»: {жесты}")
            for что in ("короткий", "вертикаль", "сКрая", "вправо"):
                if жесты[что]:
                    плохо(f"{н} «Оглавление» выехало от жеста, который его открывать не должен ({что}): {жесты}")
    else:
        цель = f".sb-s[data-to='{ПОДПУНКТ}']"
        if not кадр.locator(цель).count():
            плохо(f"{н} подпункта 2.2 нет в меню")
        else:
            кадр.locator(цель).click(); стр.wait_for_timeout(900)
            до = кадр.locator("body").evaluate("() => Math.round(document.getElementById('" + ПОДПУНКТ + "').getBoundingClientRect().top)")
            if not кадр.locator(f".sb-s.on[data-to='{ПОДПУНКТ}']").count():
                плохо(f"{н} в меню не отмечен подпункт 2.2, к которому прокрутили")
    if до is not None and not (-5 <= до <= 60):
        плохо(f"{н} подпункт 2.2 не прокрутился к своему пункту: верх на {до} px")
    # переход по разделу не уводит кадр
    if ш >= 900:
        кадр.locator(f'.sb-a[data-to="{РАЗДЕЛ}"]').click(); стр.wait_for_timeout(700)
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
    print(f"Чисто: в карточке v{ВЕРСИЯ} ссылка на статью; статья открывается в окне справки со всеми снимками, "
          "в цвете калькулятора — бирюзой, «Зелёным-графитом» и ночью; разделы листаются на месте, "
          "«Журнал обновлений» возвращает в журнал — на 390 и 1440.")


if __name__ == "__main__":
    главная()
