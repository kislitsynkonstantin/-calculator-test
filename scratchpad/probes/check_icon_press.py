#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: нажатие значка — рисунок проседает и пружинит обратно.

Константин 25.09.2026, вариант «Нажатие» из mockups/press-anim-v1.html:
«анимацию на значки эту внедряй». Проба меряет отрисовку, а не стили, в обеих
темах оформления, днём и ночью, на 390 и 1440 px:

  • значки шапки и строки опции (глаз цены, подсветка, подарок, звезда): пока
    палец держит значок, рисунок сжат до 0,86 и больше не меньше;
  • коробка кнопки при этом не двигается и не меняет размер — соседи и
    линейки остаются на месте (сжимается рисунок, а не кнопка);
  • отпустил — через треть секунды рисунок снова в полный размер;
  • у звезды остаётся её собственный сдвиг: кнопка стоит там же, где стояла;
  • при «уменьшить движение» в системе рисунок не сжимается вовсе;
  • в «Бланке» значок шапки на время нажатия берёт цвет акцента.

    python3 check_icon_press.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_palette_tone as осн  # noqa: E402  страница с заглушкой базы — та же
from playwright.sync_api import sync_playwright  # noqa: E402

НАХОДКИ = []
ЗНАЧКИ = ["#headerBtns .btn-hide-global.btn-icon", ".opt-item .price-eye-btn",
          ".opt-item .opt-highlight-btn", ".opt-item .opt-gift-btn", ".opt-item .opt-star-btn"]
ЗАМЕР = """(сел) => {
  const к = [...document.querySelectorAll(сел)].find(э => э.offsetParent && э.querySelector('svg'));
  if (!к) return null;
  const р = к.getBoundingClientRect(), с = к.querySelector('svg');
  const м = getComputedStyle(с).transform;
  const масштаб = м === 'none' ? 1 : new DOMMatrixReadOnly(м).a;
  return { x: р.x + р.width / 2, y: р.y + р.height / 2, короб: [р.x, р.y, р.width, р.height].map(v => Math.round(v * 10) / 10),
           масштаб: Math.round(масштаб * 1000) / 1000, цвет: getComputedStyle(к).color };
}"""


def плохо(где, т):
    НАХОДКИ.append(f"[{где}] {т}")


def проверить(бр, порт, ш, бланк, ночь, меньше_движения=False):
    к, стр, ошибки = осн.открыть(бр, порт, ш, 900, бланк, ночь)
    if меньше_движения:
        стр.emulate_media(reduced_motion="reduce")
    где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px" + (" · меньше движения" if меньше_движения else "")
    for сел in ЗНАЧКИ:
        # Сначала прокрутка, потом замер: после прокрутки встаёт липкая шапка,
        # и строка сдвигается — точка, снятая сразу, приходится мимо значка.
        стр.evaluate("""(сел) => { const к = [...document.querySelectorAll(сел)]
          .find(э => э.offsetParent && э.querySelector('svg')); if (к) к.scrollIntoView({ block: 'center' }); }""", сел)
        стр.wait_for_timeout(350)
        до = стр.evaluate(ЗАМЕР, сел)
        if not до:
            плохо(где, f"значка {сел} на странице не видно — проверить нечем")
            continue
        стр.mouse.move(до["x"], до["y"])
        стр.mouse.down()
        стр.wait_for_timeout(200)
        жмём = стр.evaluate(ЗАМЕР, сел)
        под = стр.evaluate("([x, y, сел]) => { const к = [...document.querySelectorAll(сел)].find(э => э.offsetParent && э.querySelector('svg')); const э = document.elementFromPoint(x, y); return !!(к && э && к.contains(э)); }",
                           [до["x"], до["y"], сел])
        if not под:
            плохо(где, f"{сел}: в точке значка лежит что-то другое — нажать его нельзя")
        стр.mouse.up()
        стр.wait_for_timeout(450)
        после = стр.evaluate(ЗАМЕР, сел)
        # Нажатие могло открыть окно или переключить значок — закрываем окна.
        стр.keyboard.press("Escape")
        стр.wait_for_timeout(150)
        if меньше_движения:
            if жмём["масштаб"] != 1:
                плохо(где, f"{сел}: при «уменьшить движение» рисунок всё равно сжат до {жмём['масштаб']}")
            continue
        if not (0.84 <= жмём["масштаб"] <= 0.88):
            плохо(где, f"{сел}: пока значок нажат, рисунок в масштабе {жмём['масштаб']}, ждали 0,86")
        if жмём["короб"] != до["короб"]:
            плохо(где, f"{сел}: при нажатии сдвинулась или сжалась сама кнопка: {до['короб']} → {жмём['короб']}")
        if после["масштаб"] != 1:
            плохо(где, f"{сел}: отпущенный значок не вернулся в полный размер: {после['масштаб']}")
        if бланк and "btn-icon" in сел and жмём["цвет"] == до["цвет"]:
            плохо(где, f"{сел}: в «Бланке» нажатый значок шапки не взял цвет акцента ({до['цвет']})")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()


def главная():
    с, порт = осн.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=осн.хром(), args=["--no-sandbox"])
            for ш in (1440, 390):
                for бланк in (True, False):
                    for ночь in (False, True):
                        проверить(бр, порт, ш, бланк, ночь)
            проверить(бр, порт, 390, True, False, меньше_движения=True)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: у значков шапки и строки опции рисунок при нажатии сжат до 0,86, кнопка "
          "не двигается, после отпускания размер полный; при «уменьшить движение» — без сжатия.")


if __name__ == "__main__":
    главная()
