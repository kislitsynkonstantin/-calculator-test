#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск проекта понимает текст, набранный не в той раскладке.

Константин 30.09.2026: «в поиске калькулятора когда вбиваешь русский текст
английской раскладкой клавиатуры — чтобы распознавал и искал проекты».

Проба набирает в поле «Поиск по названию…» и держит:
  • слово из названия проекта, набранное латиницей на тех же клавишах
    («,fyz» вместо «баня»), находит тот же проект, что и русское слово;
  • набранное как есть по-прежнему находит;
  • два слова — одно в раскладке, другое как есть — сужают так же, как оба
    как есть;
  • бессмыслица не находит ничего.

    python3 check_project_search_layout.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЛАТ = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
РУС = "йцукенгшщзхъфывапролджэячсмитьбюё"


def латиницей(т):
    return "".join(ЛАТ[РУС.index(ч)] if ч in РУС else ч for ч in т.lower())


def найдено(стр, запрос):
    стр.fill("#projectSearch", запрос); стр.wait_for_timeout(250)
    return стр.evaluate("() => filteredProjects.map(p => p[0])")


def прогон(бр, порт, шир, выс):
    н = f"[{шир}]"
    стр = бр.new_page(viewport={"width": шир, "height": выс})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    имена = стр.evaluate("() => PROJECTS.map(p => p[0])")
    # Русское слово из названия — не короче четырёх букв.
    слово = next((с for имя in имена for с in имя.split() if len(с) >= 4 and all(ч.lower() in РУС for ч in с)), None)
    if not слово:
        НАХОДКИ.append(f"{н} в названиях проектов нет русского слова для пробы: {имена[:5]}"); стр.close(); return
    как_есть = найдено(стр, слово)
    в_раскладке = найдено(стр, латиницей(слово))
    if not как_есть:
        НАХОДКИ.append(f"{н} «{слово}» как есть ничего не нашло")
    if sorted(в_раскладке) != sorted(как_есть):
        НАХОДКИ.append(f"{н} «{латиницей(слово)}» нашло {len(в_раскладке)}, а «{слово}» — {len(как_есть)}")
    второе = next((с for имя in как_есть for с in имя.split() if с.lower() != слово.lower() and len(с) >= 3), None)
    if второе:
        оба = найдено(стр, слово + " " + второе)
        смесь = найдено(стр, латиницей(слово) + " " + второе)
        if sorted(смесь) != sorted(оба):
            НАХОДКИ.append(f"{н} два слова в разных раскладках сузили иначе: {len(смесь)} против {len(оба)}")
    if найдено(стр, "щщщжжж"):
        НАХОДКИ.append(f"{н} бессмыслица что-то нашла")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 1440, 900)
            прогон(бр, порт, 390, 844)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: поиск проекта находит слово, набранное латиницей на тех же клавишах, так же, как набранное "
          "по-русски, и вместе с другим словом сужает так же; бессмыслица не находит ничего — на 1440 и 390.")


if __name__ == "__main__":
    главная()
