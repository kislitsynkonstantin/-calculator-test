#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Код пресета — в шапке мини-окна, на любой вкладке.

Константин 18.10.2026, снимком мини-окна с названием «Хай-тек баня «Виго»
7,7x8,2 · 25.09.26»: «Тут Код пресета всегда пиши, чтобы был виден на любом
скриншоте чата».

Проба держит, на заглушке базы:
  • на всех пяти вкладках — «Пресет», «Сводка», «Журнал», «Проверка»,
    «Чат» — сразу за названием стоит «код NNN NNN» с кодом этого пресета;
  • код не рвётся переносом и не выходит за мини-окно, крестик закрытия
    его не накрывает — и при длинном названии в три строки;
  • код читается: контраст не меньше 4.5, днём и ночью;
  • 390 и 1440 px.

    python3 check_preset_code_header.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


КОД = """() => { const к = document.getElementById('presetChipCard'), с = к && к.querySelector('.pc-nm-code'); if (!с) return null;
  const r = с.getBoundingClientRect(), кр = к.getBoundingClientRect(), x = к.querySelector('.pc-x').getBoundingClientRect();
  const свет = ц => { const м_ = ц.match(/[\\d.]+/g).map(Number).slice(0, 3).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
    return .2126 * м_[0] + .7152 * м_[1] + .0722 * м_[2]; };
  let фон = 'rgba(0, 0, 0, 0)', э = с;
  while (э && /rgba\\(0, 0, 0, 0\\)|transparent/.test(фон)) { фон = getComputedStyle(э).backgroundColor; э = э.parentElement; }
  const а = свет(getComputedStyle(с).color), б = свет(фон);
  const накрыт = !(r.right <= x.left || r.left >= x.right || r.bottom <= x.top || r.top >= x.bottom);
  return { текст: с.textContent.trim(), строк: Math.round(r.height / parseFloat(getComputedStyle(с).lineHeight || r.height)) || 1,
    выс: r.height, внутри: r.left >= кр.left && r.right <= кр.right, накрыт, контраст: (Math.max(а, б) + .05) / (Math.min(а, б) + .05) }; }"""


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    ждём = "код " + код[:3] + " " + код[3:]
    стр.evaluate("() => { window.__RPC.preset_chat_join = () => new Date().toISOString(); window.__RPC.preset_chat_read = () => null; }")
    ч.открыть(стр)
    for вк in ("p", "s", "l", "c", "m"):
        ч.вкладка(стр, вк)
        к_ = стр.evaluate(КОД)
        if not к_:
            плохо(f"{н} на вкладке «{вк}» в шапке нет кода пресета"); continue
        if к_["текст"] != ждём:
            плохо(f"{н} на вкладке «{вк}» в шапке {к_['текст']!r}, ждали {ждём!r}")
        if not к_["внутри"] or к_["накрыт"]:
            плохо(f"{н} на вкладке «{вк}» код за краем мини-окна или под крестиком: {к_}")
        if к_["контраст"] < 4.5:
            плохо(f"{н} код плохо читается: контраст {к_['контраст']:.2f}")
    ч.вкладка(стр, "m")
    стр.locator("#presetChipCard").screenshot(path=str(СНИМКИ / f"code-header-{ш}{'-n' if ночь else ''}.png"))
    # Длинное название — код не рвётся и не уходит под крестик.
    стр.evaluate("() => { const п = loadAllPresets(); п[activePresetId].name = 'Хай-тек баня «Виго» 7,7x8,2 с террасой, барбекю-зоной и купелью · 25.09.26'; saveAllPresets(п); заполнитьКарточкуЗначка(); }")
    стр.wait_for_timeout(400)
    к_ = стр.evaluate(КОД)
    if not к_ or к_["выс"] > 24 or not к_["внутри"] or к_["накрыт"]:
        плохо(f"{н} при длинном названии код разорван, за краем или под крестиком: {к_}")
    стр.locator("#presetChipCard").screenshot(path=str(СНИМКИ / f"code-header-long-{ш}{'-n' if ночь else ''}.png"))
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                for ш, в, ночь in ((1440, 900, False), (390, 844, False), (390, 844, True)):
                    прогон(бр, порт, ш, в, ночь)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: код пресета стоит за названием на всех пяти вкладках мини-окна, не рвётся, не уходит под крестик и за край, "
          "читается днём и ночью — на 390 и 1440, и при длинном названии.")


if __name__ == "__main__":
    главная()
