#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Скачать все» — только во вкладке «Мои» и только личные пресеты.

Константин 19.10.2026, снимком вкладки «Общие»: «В общих убери кнопку
„Скачать все“, только в Личных оставь. Скачивает только личные».

Проба держит, на заглушке базы, на 390 и 1440:
  • в «Моих» кнопка видна, в «Общих» и «По коду» её нет, при возврате в
    «Мои» — снова есть;
  • файл несёт личные пресеты и ни одного опубликованного (тот же запрет, что
    у скачивания по одному);
  • когда личных нет — файла нет, а слова говорят почему;
  • ряд кнопок без «Скачать все» не вылезает за окно.

    python3 check_preset_export_all.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []

ВИДНА = """() => { const к = document.getElementById('presetExportAll'); if (!к) return null;
  const р = к.getBoundingClientRect(); return !!(р.width && р.height && getComputedStyle(к).display !== 'none'); }"""

РЯД = """() => { const р = document.querySelector('.ptoolbar'), п = р.closest('#presetScroll') || р.parentElement, н = [];
  const кр = п.getBoundingClientRect();
  р.querySelectorAll('.ptoolbar-btn').forEach(б => { const в = б.getBoundingClientRect();
    if (в.width && (в.right > кр.right + 1 || в.left < кр.left - 1)) н.push(б.innerText.trim() + ' за краем'); });
  return н; }"""


def плохо(т):
    НАХОДКИ.append(т)


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    стр.evaluate("""() => {
      const все = loadAllPresets(), ид = Object.keys(все)[0];
      if (ид) все['опубликованный-проба'] = Object.assign({}, все[ид], { id: 'опубликованный-проба', name: 'Опубликованный', publishedAs: '611111' });
      saveAllPresets(все);
      window.__файлы = []; window.triggerDownload = (т, имя) => window.__файлы.push([имя, JSON.parse(т)]);
      openPresetPanel(); switchPresetTab('my'); }""")
    стр.wait_for_timeout(600)
    if стр.evaluate(ВИДНА) is not True:
        плохо(f"{н} в «Моих» нет кнопки «Скачать все»")
    for т in стр.evaluate(РЯД):
        плохо(f"{н} «Мои»: {т}")
    for вкладка, имя in (("shared", "Общих"), ("code", "«По коду»")):
        стр.evaluate("(т) => switchPresetTab(т)", вкладка); стр.wait_for_timeout(500)
        if стр.evaluate(ВИДНА):
            плохо(f"{н} в {имя} видна «Скачать все»")
        for т in стр.evaluate(РЯД):
            плохо(f"{н} {имя}: {т}")
        if вкладка == "shared":
            стр.screenshot(path=str(СНИМКИ / f"preset-export-shared-{ш}.png"))
    стр.evaluate("() => switchPresetTab('my')"); стр.wait_for_timeout(400)
    if стр.evaluate(ВИДНА) is not True:
        плохо(f"{н} при возврате в «Мои» кнопка не вернулась")
    стр.screenshot(path=str(СНИМКИ / f"preset-export-my-{ш}.png"))

    # Файл: личные есть, опубликованных нет.
    стр.evaluate("() => exportAllPresets()")
    ф = стр.evaluate("() => window.__файлы.slice()")
    if len(ф) != 1:
        плохо(f"{н} «Скачать все» дало файлов: {len(ф)}")
    else:
        пресеты = ф[0][1].get("presets", {})
        опубл = [к for к, п in пресеты.items() if п.get("publishedAs")]
        if опубл or not пресеты:
            плохо(f"{н} в файле опубликованные {опубл} или нет личных: {list(пресеты)}")
    # Личных нет — файла нет, слова объясняют.
    стр.evaluate("""() => { const все = loadAllPresets(); Object.keys(все).forEach(к => { все[к].publishedAs = все[к].publishedAs || '600000'; });
      saveAllPresets(все); window.__файлы = []; window.__тосты = []; exportAllPresets(); }""")
    з = стр.evaluate("() => [window.__файлы.length, window.__тосты.slice()]")
    if з[0] or not any("Личных пресетов" in т for т in з[1]):
        плохо(f"{н} без личных: файлов {з[0]}, слова {з[1]}")
    for о in ошибки[:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 390, 844)
                прогон(бр, порт, 1440, 900)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Скачать все» — только в «Моих», в «Общих» и «По коду» её нет; в файле только личные, "
          "без личных — файла нет и слова объясняют; ряд кнопок в окне; 390 и 1440.")


if __name__ == "__main__":
    главная()
