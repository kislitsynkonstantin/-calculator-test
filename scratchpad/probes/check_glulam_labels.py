#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: второй раздел везде называется своим именем.

Обход калькулятора 13.10.2026 (Константин: «Проведи все тесты, понажимай все
кнопки»): у бруса второй раздел — «Стеновой комплект и перекрытия», а свод
под итогом, окно комплектаций, редактор комплектаций и подсказки клавиш в
настройках брали подписи из каркасных списков и писали «Каркас».

Проба держит, у бруса и у каркаса:
  • свод: строка второго раздела — «2. Стеновой комплект и перекрытия» у
    бруса и «2. Каркас» у каркаса;
  • окно комплектаций: заголовок второго раздела — так же;
  • подсказки клавиш в настройках: строка клавиши «2» — так же;
  • список разделов редактора комплектаций — так же.

    python3 check_glulam_labels.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИД = """() => {
  const св = [...document.querySelectorAll('#breakdownTable .bd-row .bd-name')].map(э => э.textContent.trim());
  let компл = [];
  try { openKompl(); компл = [...document.querySelectorAll('#komplOverlay .ks-name, #komplOverlay tr.sec td')].map(э => э.textContent.trim()); closeKompl(); } catch (e) { компл = ['ошибка: ' + e.message]; }
  let клавиши = [];
  try { openSettings(); if (typeof settingsTab !== 'undefined') { settingsTab = 'cmd'; renderSettingsBody(); }
        клавиши = [...document.querySelectorAll('#settingsBody .st-label')].map(э => э.textContent.trim()); closeSettings(); } catch (e) { клавиши = ['ошибка: ' + e.message]; }
  const ред = KED_SECTIONS_LIST.map(([к, л]) => подписьРаздела(к, л));
  return { св, компл, клавиши, ред };
}"""


def сверить(стр, тех, ждём):
    стр.evaluate("async (т) => { await switchTech(т); selectProjectOption(0); calc(); }", тех)
    стр.wait_for_timeout(700)
    в = стр.evaluate(ВИД)
    н = f"[{тех}]"
    чужое = "Каркас" if тех == "glulam" else "Стеновой комплект"
    if not any(с.startswith("2. ") and ждём in с for с in в["св"]):
        НАХОДКИ.append(f"{н} в своде нет строки «2. {ждём}…»: {в['св'][:4]}")
    if any(с.startswith("2. ") and чужое in с for с in в["св"]):
        НАХОДКИ.append(f"{н} в своде второй раздел назван «{чужое}»")
    if not any(ждём in с for с in в["компл"]):
        НАХОДКИ.append(f"{н} в окне комплектаций нет раздела «{ждём}»: {в['компл'][:4]}")
    if any(с.strip() == чужое or с.endswith(" " + чужое) for с in в["компл"]):
        НАХОДКИ.append(f"{н} в окне комплектаций раздел назван «{чужое}»")
    вторая = [с for с in в["клавиши"] if с.startswith("2. ")]
    if not вторая or ждём not in вторая[0]:
        НАХОДКИ.append(f"{н} подсказка клавиши «2»: {вторая[:1]}, ждали «{ждём}»")
    if not any(ждём in с for с in в["ред"]):
        НАХОДКИ.append(f"{н} разделы редактора комплектаций: {в['ред'][:3]}")
    return в


def main():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            стр = бр.new_page(viewport={"width": 1440, "height": 1000})
            ош = []
            стр.on("pageerror", lambda e: ош.append(str(e)))
            стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
            стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
            б = сверить(стр, "glulam", "Стеновой комплект и перекрытия")
            к = сверить(стр, "frame", "Каркас")
            if ош:
                НАХОДКИ.append(f"ошибки страницы: {ош[:3]}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: у бруса второй раздел — «Стеновой комплект и перекрытия» в своде, окне комплектаций, "
          "подсказках клавиш и редакторе комплектаций; у каркаса там же — «Каркас».")


if __name__ == "__main__":
    main()
