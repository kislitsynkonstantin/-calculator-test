#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Бланк» с первого кадра — без единого скрипта.

Константин 19.10.2026, снимками теста и боевого с телефона: «Почему-то иногда
загружаться стала эта тема на секунду» — страница секунду стояла снятым
«Модерном». Класс темы ставил только скрипт в начале <body>, и всё, что Safari
рисовал до него или без него, выходило без темы. Теперь класс стоит в самом
теге <body>.

Проба открывает калькулятор с выключенными скриптами — так выглядит любой кадр,
нарисованный раньше скрипта, — и держит:
  • у <body> класс ui-blank;
  • шапка — шапкой «Бланка»: без заливки и скругления, а не бирюзовой плашкой;
  • карточка «Выбор проекта» — без рамки, как часть листа;
  • тон — «Зелёный-графит» (data-tone="bmsk" на <html>), а не бирюза;
  • а со скриптами выбранная руками бирюза снимает тон из разметки;
на 390 и 1440. Снимки — BM_SHOTS/theme-noscript-<ширина>.png.

    python3 check_theme_markup.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []

ВИД = """() => { const ш = document.querySelector('.header'), к = document.querySelector('.card');
  const сш = getComputedStyle(ш), ск = к ? getComputedStyle(к) : null;
  return { класс: document.body.className, тон: document.documentElement.getAttribute('data-tone'), шФон: сш.backgroundColor, шУгол: сш.borderTopLeftRadius,
    кРамка: ск ? ск.borderTopWidth + ' ' + ск.borderTopStyle : '' }; }"""


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                for ш, в in ((390, 844), (1440, 900)):
                    кт = бр.new_context(viewport={"width": ш, "height": в}, java_script_enabled=False)
                    стр = кт.new_page()
                    стр.route("**/*", lambda r: r.continue_() if "127.0.0.1" in r.request.url else r.abort())
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="domcontentloaded")
                    в_ = стр.evaluate(ВИД)
                    стр.screenshot(path=str(СНИМКИ / f"theme-noscript-{ш}.png"))
                    if "ui-blank" not in в_["класс"].split():
                        НАХОДКИ.append(f"[{ш}] без скриптов у <body> нет ui-blank: «{в_['класс']}»")
                    if в_["тон"] != "bmsk":
                        НАХОДКИ.append(f"[{ш}] без скриптов тон не «Зелёный-графит»: {в_['тон']}")
                    if в_["шФон"] not in ("rgba(0, 0, 0, 0)", "transparent") or в_["шУгол"] != "0px":
                        НАХОДКИ.append(f"[{ш}] без скриптов шапка — плашкой «Модерна»: фон {в_['шФон']}, скругление {в_['шУгол']}")
                    if в_["кРамка"] and not в_["кРамка"].startswith("0px") and "none" not in в_["кРамка"]:
                        НАХОДКИ.append(f"[{ш}] без скриптов карточка «Выбор проекта» в рамке: {в_['кРамка']}")
                    кт.close()
                # Бирюза, выбранная руками, остаётся бирюзой: тон из разметки скрипт снимает.
                кт = бр.new_context(viewport={"width": 390, "height": 844})
                кт.add_init_script("try{localStorage.setItem('appSettings_v1', JSON.stringify({tone:'teal', toneMigratedToBmsk:true}))}catch(e){}")
                # Тон — в ту минуту, когда за ранним скриптом встаёт экран входа:
                # позже его снимает и общий скрипт, и проверка после загрузки
                # ранний скрипт не видит.
                кт.add_init_script("""new MutationObserver((з, н) => { if (document.getElementById('loginScreen')) {
                  window.__тонРано = document.documentElement.getAttribute('data-tone'); н.disconnect(); } })
                  .observe(document, { childList: true, subtree: true });""")
                стр = кт.new_page()
                стр.route("**/*", lambda r: r.continue_() if "127.0.0.1" in r.request.url else r.abort())
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="domcontentloaded")
                тон = стр.evaluate("() => window.__тонРано === undefined ? 'не замерен' : window.__тонРано")
                if тон is not None:
                    НАХОДКИ.append(f"[390] выбранная бирюза не сняла тон из разметки: data-tone={тон}")
                кт.close()
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: без единого скрипта страница уже в «Бланке» — класс в теге <body>, шапка без плашки, карточка без рамки, тон «Зелёный-графит», а выбранная бирюза его снимает; 390 и 1440.")


if __name__ == "__main__":
    главная()
