#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба раздела «Визуализация и планировка»: уголок размера и надпись кнопки.

Держит то, из-за чего уголок на телефоне не работал вовсе: он слушал мышь,
а касание мыши не присылает. Проверяется обоими путями — пальцем и мышью, —
и отдельно то, что браузер не забирает жест себе (`touch-action: none`).

Крестик проверяется рядом: он работал и раньше, и проба обязана отличать
«уголок починили» от «сломали заодно крестик».

Вторая половина — надпись на кнопке расстановки. Она называет то, что сделает
следующее нажатие: после расстановки «Поменять местами» у двух снимков и
«Сдвинуть по кругу» у трёх, а стоит тронуть снимок — снова «Авто-расстановка».
Надпись обязана быть верной в каждый момент, иначе она хуже молчания.
"""
import os
import pathlib
import sys
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent.parent
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []
# Однопиксельная картинка: содержимое снимка пробе безразлично.
ТОЧКА = ("data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==")


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium не найден — запусти .claude/hooks/session-start.sh")
    return str(найденные[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ПОЛОЖИТЬ = """(точка) => {
  const беда = document.getElementById('pricingErrorScreen');
  if (беда) беда.style.display = 'none';
  // Раздел свёрнут по умолчанию — свёрнутый холст нулевой ширины, и снимку
  // в нём негде встать. Разворачиваем так же, как это делает нажатие.
  const кнопка = document.getElementById('btnCollapseImageCard');
  if (кнопка && кнопка.classList.contains('collapsed')) toggleImageCard();
  document.querySelectorAll('.canvas-img-item').forEach(э => э.remove());
  canvasItems = [];
  canvasAddImageAt(точка, 20, 20, 300, 200);
  const снимок = document.querySelector('.canvas-img-item');
  // Уголок показывается по наведению; пробе наведение ни к чему.
  снимок.querySelector('.img-resize').style.display = 'flex';
  return { id: снимок.id, ш: снимок.offsetWidth, вы: снимок.offsetHeight };
}"""

# Жест пальцем: браузер такие события шлёт сам, проба шлёт их руками — именно
# по ним и видно, слушает ли уголок указатель или по-прежнему одну мышь.
ПАЛЬЦЕМ = """([дх, ду]) => {
  const уголок = document.querySelector('.canvas-img-item .img-resize');
  const r = уголок.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const событие = (имя, кх, ку) => уголок.dispatchEvent(new PointerEvent(имя, {
    bubbles: true, cancelable: true, pointerId: 7, pointerType: 'touch',
    isPrimary: true, clientX: кх, clientY: ку, buttons: 1,
  }));
  // Захват указателя проба не переживёт: узел не в поле зрения указателя.
  уголок.setPointerCapture = () => {};
  событие('pointerdown', x, y);
  событие('pointermove', x + дх, y + ду);
  событие('pointerup', x + дх, y + ду);
  const снимок = document.querySelector('.canvas-img-item');
  return { ш: снимок.offsetWidth, вы: снимок.offsetHeight };
}"""


# Перенос снимка. Мышью — сразу, пальцем — после удержания: провёл пальцем
# раньше срока — это листание страницы, и снимок стоять должен на месте.
ПЕРЕНОС_ПАЛЬЦЕМ = """async ([держать, дх, ду]) => {
  const снимок = document.querySelector('.canvas-img-item');
  const r = снимок.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  снимок.setPointerCapture = () => {};
  const шли = (имя, кх, ку, куда) => (куда || снимок).dispatchEvent(new PointerEvent(имя, {
    bubbles: true, cancelable: true, pointerId: 11, pointerType: 'touch',
    isPrimary: true, clientX: кх, clientY: ку, buttons: 1,
  }));
  const было = { л: parseInt(снимок.style.left) || 0, в: parseInt(снимок.style.top) || 0 };
  шли('pointerdown', x, y);
  await new Promise(р => setTimeout(р, держать));
  шли('pointermove', x + дх, y + ду, document);
  const взят = снимок.classList.contains('тянут');
  шли('pointerup', x + дх, y + ду, document);
  await new Promise(р => setTimeout(р, 60));
  return { было, стало: { л: parseInt(снимок.style.left) || 0, в: parseInt(снимок.style.top) || 0 },
           взят, жест: getComputedStyle(снимок).touchAction };
}"""

ПЕРЕНОС_МЫШЬЮ = """([дх, ду]) => {
  const снимок = document.querySelector('.canvas-img-item');
  const r = снимок.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  снимок.setPointerCapture = () => {};
  const шли = (имя, кх, ку, куда) => (куда || снимок).dispatchEvent(new PointerEvent(имя, {
    bubbles: true, cancelable: true, pointerId: 12, pointerType: 'mouse',
    isPrimary: true, clientX: кх, clientY: ку, buttons: 1,
  }));
  const было = { л: parseInt(снимок.style.left) || 0, в: parseInt(снимок.style.top) || 0 };
  шли('pointerdown', x, y);
  шли('pointermove', x + дх, y + ду, document);
  шли('pointerup', x + дх, y + ду, document);
  return { было, стало: { л: parseInt(снимок.style.left) || 0, в: parseInt(снимок.style.top) || 0 } };
}"""

# Выгрузка снимков в облако обязана подменять адрес и на самой странице:
# снимок для клиентской ссылки собирается из холста, и пока в нём стоит data:,
# полоска пишет «фото не ушли» при уже уехавших фото.
ВЫГРУЗКА = """async () => {
  const ф = [...document.querySelectorAll('.canvas-img-item')].map(э => {
    const и = э.querySelector('img');
    return { src: и.src, left: parseInt(э.style.left) || 0, top: parseInt(э.style.top) || 0,
             width: э.offsetWidth, height: э.offsetHeight };
  });
  const доData = ф.filter(и => и.src.startsWith('data:')).length;
  const адреса = await uploadCanvasToStorage('проба', ф);
  const после = [...document.querySelectorAll('.canvas-img-item img')].map(и => и.src);
  return { доData, ушло: адреса.length,
           осталосьData: после.filter(с => с.startsWith('data:')).length };
}"""


def главная():
    с, порт = сервер()
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
        к = бр.new_context(viewport={"width": 390, "height": 844},
                           has_touch=True, is_mobile=True)
        стр = к.new_page()
        стр.add_init_script(ЗАГЛУШКА)
        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
        стр.wait_for_timeout(1400)

        было = стр.evaluate(ПОЛОЖИТЬ, ТОЧКА)
        if not было or not было["ш"]:
            НАХОДКИ.append("снимок не встал на холст — проверять нечего")
            print("НАХОДКИ:\n  ✗", НАХОДКИ[0]); sys.exit(1)

        # ── пальцем ──────────────────────────────────────────────────────────
        стало = стр.evaluate(ПАЛЬЦЕМ, [70, 50])
        if стало["ш"] <= было["ш"] + 5 or стало["вы"] <= было["вы"] + 5:
            НАХОДКИ.append(f"пальцем уголок не тянется: было {было['ш']}×{было['вы']}, "
                           f"стало {стало['ш']}×{стало['вы']}")

        # Браузер не должен забирать жест себе — иначе до обработчиков он
        # не дойдёт даже при верном коде.
        жест = стр.evaluate("() => getComputedStyle("
                            "document.querySelector('.canvas-img-item .img-resize')).touchAction")
        if жест != "none":
            НАХОДКИ.append(f"у уголка touch-action: {жест} — палец листает страницу вместо тяги")


        # ── поле нажатия и вес ───────────────────────────────────────────────
        поле = стр.evaluate("""() => {
          const у = document.querySelector('.canvas-img-item .img-resize');
          const с = getComputedStyle(у, '::before');
          const ч = з => parseFloat(з) || 0;
          const r = у.getBoundingClientRect();
          return { коробка: r.width,
                   поле: r.width - ч(с.left) - ч(с.right) };
        }""")
        if поле["поле"] < 43.5:
            НАХОДКИ.append(f"поле нажатия уголка {поле['поле']:.0f} px, нужно 44")
        if поле["коробка"] > 30:
            НАХОДКИ.append(f"уголок нарисован {поле['коробка']:.0f} px — вес оплачен размером")

        # ── перенос снимка: мышью сразу, пальцем после удержания ─────────────
        # Пальцем снимок не двигался вовсе, а «просто отдать палец» нельзя:
        # снимки занимают весь холст, и страница под ними перестала бы
        # листаться. Удержание разводит жесты (Константин, 17.09.2026).
        мышью = стр.evaluate(ПЕРЕНОС_МЫШЬЮ, [60, 40])
        if abs(мышью["стало"]["л"] - мышью["было"]["л"] - 60) > 4:
            НАХОДКИ.append(f"мышью снимок не переносится: было {мышью['было']}, "
                           f"стало {мышью['стало']}")

        листание = стр.evaluate(ПЕРЕНОС_ПАЛЬЦЕМ, [40, 60, 40])   # раньше срока
        if листание["взят"]:
            НАХОДКИ.append("палец провёл сразу, а снимок уже в руке — страницу "
                           "под холстом не пролистать")
        if листание["стало"] != листание["было"]:
            НАХОДКИ.append(f"снимок поехал за листанием: {листание['было']} → "
                           f"{листание['стало']}")
        if листание["жест"] == "none":
            НАХОДКИ.append("снимок забрал жест себе вне тяги — холст перестанет листаться")

        держали = стр.evaluate(ПЕРЕНОС_ПАЛЬЦЕМ, [420, 50, 30])   # с удержанием
        if not держали["взят"]:
            НАХОДКИ.append("после удержания снимок не поднялся — пальцу нечем "
                           "отличить взятый снимок от невзятого")
        if abs(держали["стало"]["л"] - держали["было"]["л"] - 50) > 4:
            НАХОДКИ.append(f"после удержания снимок не поехал за пальцем: "
                           f"{держали['было']} → {держали['стало']}")
        # Отпустили — жест возвращается странице.
        жестПосле = стр.evaluate("() => getComputedStyle(document.querySelector('.canvas-img-item')).touchAction")
        if жестПосле == "none":
            НАХОДКИ.append("после переноса снимок так и держит жест — холст не листается")

        # ── выгруженные фото подменяют адрес и на странице ───────────────────
        # Иначе снимок для клиентской ссылки видит их как data: и считает
        # неотправленными: «фото не ушли (2)» при уехавших фото.
        выгрузка = стр.evaluate(ВЫГРУЗКА)
        if not выгрузка["доData"]:
            НАХОДКИ.append("проба не нашла неотправленных снимков — проверять нечего")
        elif выгрузка["осталосьData"]:
            НАХОДКИ.append(f"после выгрузки на странице осталось {выгрузка['осталосьData']} "
                           "картинок как data: — полоска будет писать «фото не ушли» "
                           "при уехавших фото")

        # ── расстановка после ручного переноса сохраняет порядок ─────────────
        # Кнопка перекидывала снимки в своём порядке, а менеджер уже поставил
        # их так, как хочет видеть (Константин, 18.09.2026). Порядок берётся
        # с холста: строками сверху вниз, внутри строки слева направо.
        порядок = стр.evaluate("""(точка) => {
          document.querySelectorAll('.canvas-img-item').forEach(э => э.remove());
          canvasItems = []; _слепокРаскладки = null;
          canvasAddImageAt(точка, 0, 0, 200, 140);      // будет третьим
          canvasAddImageAt(точка, 0, 0, 200, 140);      // первым
          canvasAddImageAt(точка, 0, 0, 200, 140);      // вторым
          const [а, б, в] = [...document.querySelectorAll('.canvas-img-item')];
          canvasAutoCenter();                            // первый раз — по сетке
          // Руками: «б» ставим первым в верхней строке, «в» — рядом,
          // «а» уводим вниз. Порядок на холсте: б, в, а.
          const пост = (э, л, вх) => { э.style.left = л + 'px'; э.style.top = вх + 'px'; };
          пост(б, 0, 0); пост(в, 220, 4); пост(а, 0, 200);
          холстИзменился();
          const надписьДо = document.querySelector('#btnAutoCenterImgs .ac-t').textContent.trim();
          canvasAutoCenter();                            // второй раз — закрепить
          const после = [...document.querySelectorAll('.canvas-img-item')].map(э => э.id);
          const места = {};
          [...document.querySelectorAll('.canvas-img-item')].forEach(э => {
            места[э.id] = { л: parseInt(э.style.left) || 0, в: parseInt(э.style.top) || 0 };
          });
          return { ожидали: [б.id, в.id, а.id], вышло: после, места,
                   надписьДо, очередь: canvasItems.slice() };
        }""", ТОЧКА)
        if порядок["вышло"] != порядок["ожидали"]:
            НАХОДКИ.append(f"расстановка перетасовала снимки: ожидали {порядок['ожидали']}, "
                           f"вышло {порядок['вышло']} — рука не закреплена")
        if порядок["очередь"] != порядок["вышло"]:
            НАХОДКИ.append("очередь снимков разошлась с разметкой — в печать уйдёт "
                           "другой порядок")
        первый, второй, третий = порядок["ожидали"]
        м = порядок["места"]
        if not (м[первый]["в"] == м[второй]["в"] and м[первый]["л"] < м[второй]["л"]):
            НАХОДКИ.append(f"первые два снимка встали не в одну строку: {м[первый]} и {м[второй]}")
        if not (м[третий]["в"] > м[первый]["в"]):
            НАХОДКИ.append(f"третий снимок не ушёл во вторую строку: {м[третий]}")
        if порядок["надписьДо"] != "Расставить":
            НАХОДКИ.append(f"после ручного переноса кнопка зовётся {порядок['надписьДо']!r}, "
                           "а она теперь не тасует, а выравнивает по сетке")

        # ── надпись кнопки называет следующее нажатие ────────────────────────
        def надпись():
            return стр.evaluate("() => { const к = document.getElementById('btnAutoCenterImgs');"
                                " return { текст: к.querySelector('.ac-t').textContent.trim(),"
                                " залито: к.classList.contains('btn-canvas-swap') }; }")

        стр.evaluate(ПОЛОЖИТЬ, ТОЧКА)          # один снимок на холсте
        # На одном снимке менять нечего, и кнопка обязана молчать: сдвиг
        # у неё начинается с двух. Иначе надпись обещала бы то, чего нажатие
        # не сделает, — а это хуже молчания.
        стр.evaluate("() => canvasAutoCenter()")
        стр.wait_for_timeout(80)
        один = надпись()
        if один["текст"] != "Авто-расстановка" or один["залито"]:
            НАХОДКИ.append(f"на одном снимке кнопка зовётся {один['текст']!r}, "
                           "а менять местами нечего")

        стр.evaluate("(т) => canvasAddImageAt(т, 60, 60, 200, 140)", ТОЧКА)
        до = надпись()
        if до["текст"] != "Авто-расстановка" or до["залито"]:
            плохо = f"до расстановки кнопка зовётся {до['текст']!r} (залито: {до['залито']})"
            НАХОДКИ.append(плохо)
        стр.evaluate("() => canvasAutoCenter()")
        стр.wait_for_timeout(80)
        пара = надпись()
        if пара["текст"] != "Поменять местами":
            НАХОДКИ.append(f"на двух снимках после расстановки кнопка зовётся {пара['текст']!r}, "
                           "а следующее нажатие поменяет их местами")
        if not пара["залито"]:
            НАХОДКИ.append("второе состояние кнопки ничем не отличается от обычного")

        # Тронули снимок — сдвига уже не будет. Надпись при этом говорит
        # «Расставить»: следующее нажатие выровняет по сетке, сохранив порядок,
        # в котором снимки лежат, а не перетасует (Константин, 18.09.2026).
        стр.evaluate("""() => {
          const с = document.querySelector('.canvas-img-item');
          с.style.left = (parseInt(с.style.left) + 24) + 'px';
          холстИзменился();
        }""")
        стр.wait_for_timeout(80)
        назад = надпись()
        if назад["текст"] != "Расставить" or назад["залито"]:
            НАХОДКИ.append(f"снимок подвинули, а кнопка зовётся {назад['текст']!r} — "
                           "надпись обещает то, чего нажатие не сделает")

        # Три снимка — не обмен, а круг, и надпись другая.
        стр.evaluate("(т) => canvasAddImageAt(т, 90, 90, 200, 140)", ТОЧКА)
        стр.evaluate("() => canvasAutoCenter()")
        стр.wait_for_timeout(80)
        трое = надпись()
        if трое["текст"] != "Сдвинуть по кругу":
            НАХОДКИ.append(f"на трёх снимках кнопка зовётся {трое['текст']!r}, "
                           "а нажатие сдвинет их по кругу")

        стр.evaluate("() => { document.querySelectorAll('.canvas-img-item').forEach(э => э.remove());"
                     " canvasItems = []; }")
        стр.evaluate(ПОЛОЖИТЬ, ТОЧКА)

        # ── крестик рядом не сломан ──────────────────────────────────────────
        стр.evaluate("() => document.querySelector('.canvas-img-item .img-delete').click()")
        стр.wait_for_timeout(150)
        if стр.evaluate("() => document.querySelectorAll('.canvas-img-item').length") != 0:
            НАХОДКИ.append("крестик перестал удалять снимок")
        к.close()

        # ── мышью, на столе ──────────────────────────────────────────────────
        # Отдельным окном: в облике телефона Chromium шлёт только касания,
        # и настоящую мышь там не проверить — проверка выглядела бы пройденной
        # ни за что.
        к2 = бр.new_context(viewport={"width": 1280, "height": 900})
        стр2 = к2.new_page()
        стр2.add_init_script(ЗАГЛУШКА)
        стр2.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
        стр2.wait_for_timeout(1400)
        было2 = стр2.evaluate(ПОЛОЖИТЬ, ТОЧКА)
        уголок = стр2.locator(".canvas-img-item .img-resize")
        # Коробка приходит в координатах страницы, а мышь ходит по окну: без
        # прокрутки нажатие уезжало мимо уголка, и проба ругалась на верный код.
        уголок.scroll_into_view_if_needed()
        стр2.wait_for_timeout(120)
        к1 = уголок.bounding_box()
        стр2.mouse.move(к1["x"] + к1["width"] / 2, к1["y"] + к1["height"] / 2)
        стр2.mouse.down()
        стр2.mouse.move(к1["x"] + к1["width"] / 2 + 60, к1["y"] + к1["height"] / 2 + 40, steps=6)
        стр2.mouse.up()
        стр2.wait_for_timeout(150)
        стало2 = стр2.evaluate("() => { const с = document.querySelector('.canvas-img-item');"
                               " return { ш: с.offsetWidth, вы: с.offsetHeight }; }")
        if стало2["ш"] <= было2["ш"] + 5 or стало2["вы"] <= было2["вы"] + 5:
            НАХОДКИ.append(f"мышью уголок не тянется: было {было2['ш']}×{было2['вы']}, "
                           f"стало {стало2['ш']}×{стало2['вы']}")
        к2.close()

        бр.close()
    с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: уголок тянется пальцем и мышью, надпись кнопки верна в каждом состоянии,\n       жест не уходит браузеру, крестик цел.")


if __name__ == "__main__":
    главная()
