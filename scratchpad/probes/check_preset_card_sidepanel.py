#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мини-окно и боковая панель «Спецификация»: без выезда за край экрана.

Константин 29.09.2026, снимком с телефона: боковая панель открыта, а
раскрытое мини-окно уехало влево за край экрана — видна только его правая
часть. Сдвиг «мимо панели» решался по ширине значка: значок «Мой пресет»
помещался левее панели, и вместе с ним сдвигалось мини-окно шириной 316 px.
«Боковая панель на мобильном пусть закрывает мини-окно, когда нет места».

Проба на телефонах 390, 414 и 430 px (касание) и на 768 и 1440 px, с открытым мини-окном
и открытой панелью, держит:
  • ни значок, ни мини-окно не выходят за левый край экрана;
  • сдвинутые — не заходят под панель: если сдвиг есть, мини-окно целиком
    левее её кромки; если места нет — они на месте, а панель стоит слоем
    выше и накрывает их; из-под панели не торчит полоса мини-окна — оно
    скрыто целиком;
  • закрыли панель — мини-окно снова видно, на своём месте.

    python3 check_preset_card_sidepanel.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ГДЕ = """() => { const з = document.getElementById('presetChip').getBoundingClientRect(), о = document.getElementById('presetChipCard').getBoundingClientRect();
  const п = document.getElementById('sideNav'), пп = п.getBoundingClientRect();
  const zп = +getComputedStyle(п).zIndex || 0, zо = +getComputedStyle(document.getElementById('presetChipCard')).zIndex || 0;
  return { сдвиг: document.body.classList.contains('pc-shift'), панель: document.body.classList.contains('side-nav-open'),
    значок: [Math.round(з.left), Math.round(з.right)], окно: [Math.round(о.left), Math.round(о.right)], кромка: Math.round(пп.left), ширПанели: Math.round(пп.width),
    выше: zп > zо, видно: getComputedStyle(document.getElementById('presetChipCard')).visibility !== 'hidden' && document.getElementById('presetChipCard').classList.contains('show') }; }"""


ШРИФТЫ = (pathlib.Path(__file__).parent / "шрифты_google.css").read_text(encoding="utf-8")


def прогон(бр, порт, ш, в, касание):
    н = f"[{ш}{' касание' if касание else ''}]"
    # Настоящие Geologica и Unbounded: сдвиг решается шириной значка, а в
    # подменном шрифте значок шире и сдвига не было бы вовсе — проба прошла бы
    # и на сборке с ошибкой (так и было при первом прогоне).
    контекст = бр.new_context(viewport={"width": ш, "height": в}, has_touch=касание, is_mobile=касание)
    контекст.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    контекст.route("**/fonts.gstatic.com/**", lambda r: r.abort())

    class Страница:  # к.начать открывает страницу через new_page(viewport=…)
        def new_page(self, **_):
            return контекст.new_page()
    стр, ошибки = к.начать(Страница(), порт, ш, в, False)
    if стр.evaluate("() => { const e = document.createElement('span'); e.style.cssText = 'position:absolute;font:40px Geologica,monospace'; e.textContent = 'Мой пресет'; document.body.appendChild(e); const a = e.offsetWidth; e.style.fontFamily = 'monospace'; const b = e.offsetWidth; e.remove(); return a === b; }"):
        НАХОДКИ.append(f"{н} настоящий шрифт не лёг — проба мерила бы подменным"); стр.close(); return
    if not стр.evaluate("() => activePresetId"):
        НАХОДКИ.append(f"{н} пресет не сохранился"); стр.close(); return
    к.открыть(стр); стр.wait_for_timeout(300)
    стр.evaluate("() => openSideNav()"); стр.wait_for_timeout(700)
    стр.evaluate("() => значокМимоПанели()"); стр.wait_for_timeout(300)
    г = стр.evaluate(ГДЕ)
    if not г["панель"] or not г["ширПанели"]:
        НАХОДКИ.append(f"{н} боковая панель не открылась — проверка вслепую: {г}")
    elif г["значок"][0] < 0 or г["окно"][0] < 0:
        НАХОДКИ.append(f"{н} мини-окно или значок за левым краем экрана: {г}")
    elif г["сдвиг"] and г["окно"][1] > г["кромка"] + 1:
        НАХОДКИ.append(f"{н} мини-окно сдвинуто, но заходит под панель: {г}")
    elif not г["сдвиг"] and г["окно"][1] > г["кромка"] and not г["выше"]:
        НАХОДКИ.append(f"{н} места нет, а панель не накрывает мини-окно: {г}")
    elif not г["сдвиг"] and г["окно"][0] < г["кромка"] and г["окно"][1] > г["кромка"] and г["видно"]:
        НАХОДКИ.append(f"{н} из-под панели торчит полоса мини-окна: окно {г['окно']}, кромка панели {г['кромка']}")
    стр.screenshot(path=str(м.СНИМКИ / f"card-sidepanel-{ш}.png"))
    # Закрыли панель — мини-окно снова видно, на своём месте.
    стр.evaluate("() => closeSideNav()"); стр.wait_for_timeout(500)
    г2 = стр.evaluate(ГДЕ)
    if not г2["видно"] or г2["окно"][0] < 0 or г2["сдвиг"]:
        НАХОДКИ.append(f"{н} после закрытия панели мини-окно не вернулось: {г2}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            # Телефоны разной ширины: на 390 места нет вовсе, а на 414–430
            # значок уже помещается левее панели — там и уезжало мини-окно.
            for ш, в in ((390, 844), (414, 896), (430, 932)):
                прогон(бр, порт, ш, в, True)
            прогон(бр, порт, 768, 1024, False)
            прогон(бр, порт, 1440, 900, False)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: при открытой боковой панели мини-окно и значок не выходят за край экрана — сдвинуты целиком левее "
          "панели, а где места нет, стоят на месте под панелью — на телефонах 390, 414 и 430, на 768 и 1440.")


if __name__ == "__main__":
    главная()
