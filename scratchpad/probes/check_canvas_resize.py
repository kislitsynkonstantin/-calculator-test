#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба уголка размера у снимков в разделе «Визуализация и планировка».

Держит то, из-за чего уголок на телефоне не работал вовсе: он слушал мышь,
а касание мыши не присылает. Проверяется обоими путями — пальцем и мышью, —
и отдельно то, что браузер не забирает жест себе (`touch-action: none`).

Крестик проверяется рядом: он работал и раньше, и проба обязана отличать
«уголок починили» от «сломали заодно крестик».
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
    print("Чисто: уголок тянется пальцем и мышью, жест не уходит браузеру, крестик цел.")


if __name__ == "__main__":
    главная()
