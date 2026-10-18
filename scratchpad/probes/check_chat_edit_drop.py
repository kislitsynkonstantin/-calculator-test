#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Проверка»: администратор убирает правку из чата свайпом влево.

Константин 18.10.2026, снимком вкладки «Проверка»: «Тут на пункты проверки
для администратора по свайпу влево сделай удалить пункт (именно в
проверке). В чате он остаётся».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • у администратора правка из чата сдвигается влево; дальше 60 px — в базу
    уходит preset_chat_mark с пустой отметкой, правки в «Проверке» больше
    нет, а сообщение в чате на месте, без метки «в правках»; сказано словами;
  • короткий сдвиг (меньше 60 px) ничего не снимает;
  • под правками у администратора — строка-подсказка про свайп влево; у
    менеджера её нет, и сдвиг влево ничего не делает;
  • свайп вправо по пункту автоматической проверки по-прежнему пропускает его;
  • вёрстка на 390 и 1440 — как в пробе чата.

    python3 check_chat_edit_drop.py
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


ПРАВКИ = """(роль) => { const т = window.__ТАБЛИЦЫ.preset_messages;
  т[0].review_state = 'done'; т[2].review_state = 'open'; т[3].review_state = 'open';
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  try { localStorage.removeItem('banya_chat_edits_done_hidden'); localStorage.removeItem('banya_chat_edits_folded'); } catch (e) {}
  _правкиЧатаСкрыты = false; _правкиЧатаСвёрнуты = false;
  window._sbProfile = Object.assign({}, window._sbProfile || {}, { role: роль }); }"""

СОСТ = """() => { const к = document.getElementById('presetChipCard');
  return { правок: к.querySelectorAll('.pc-pr li').length, сдвигаемых: к.querySelectorAll('.pc-pr li[data-drop]').length,
    подсказка: [...к.querySelectorAll('.pc-ck-f')].map(х => х.textContent).join(' | '),
    отметки: (window.__ОТМЕТКИ || []).slice(), тост: (window.__тосты || []).slice(-1)[0] || '' }; }"""


def сдвиг(стр, сел, dx):
    п = стр.locator(сел).first.bounding_box()
    x, y = п["x"] + п["width"] * 0.6, п["y"] + п["height"] / 2
    стр.mouse.move(x, y); стр.mouse.down()
    for i in range(1, 9):
        стр.mouse.move(x + dx * i / 8, y + 1)
    стр.mouse.up(); стр.wait_for_timeout(600)


def прогон(бр, порт, ш, в, ночь, роль):
    н = f"[{ш}{' ночь' if ночь else ''} {роль}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    стр.evaluate(ПРАВКИ, роль)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(600); ч.вкладка(стр, "c"); стр.wait_for_timeout(500)
    до = стр.evaluate(СОСТ)
    админ = роль == "admin"
    if до["правок"] != 3 or до["сдвигаемых"] != (3 if админ else 0) or (("Свайп влево" in до["подсказка"] or "Перетащите правку влево" in до["подсказка"]) != админ):
        плохо(f"{н} до свайпа: {до}")
    ч.вёрстка(стр, н, "«Проверка» с подсказкой")
    сел = "#presetChipCard .pc-pr li"
    if not админ:
        # У менеджера сдвиг мышью — обычное нажатие по правке (ведёт в чат);
        # важно одно: отметка не ушла.
        сдвиг(стр, сел, -110)
        if len(стр.evaluate(СОСТ)["отметки"]) != len(до["отметки"]):
            плохо(f"{н} у менеджера свайп влево снял правку: {стр.evaluate(СОСТ)}")
        ч.вкладка(стр, "c"); стр.wait_for_timeout(400)
        if стр.evaluate(СОСТ)["правок"] != 3:
            плохо(f"{н} у менеджера правок в «Проверке» не три после сдвига")
        стр.close(); return
    # Короткий сдвиг — ничего.
    сдвиг(стр, сел, -40)
    п = стр.evaluate(СОСТ)
    if п["правок"] != 3 or len(п["отметки"]) != len(до["отметки"]):
        плохо(f"{н} короткий сдвиг влево что-то снял: {п}")
    сдвиг(стр, сел, -110)
    п = стр.evaluate(СОСТ)
    первая = "11111111-1111-4111-8111-111111111111"
    сообщение = стр.evaluate(f"() => {{ const с = сообщениеЧата('{первая}'); return с ? {{ есть: true, отметка: с.review_state || null }} : {{ есть: false }}; }}")
    if админ:
        последняя = п["отметки"][-1] if п["отметки"] else {}
        if п["правок"] != 2 or последняя.get("p_state") is not None or последняя.get("p_id") != первая or not сообщение["есть"] \
                or сообщение.get("отметка") or "убрана из проверки" not in п["тост"]:
            плохо(f"{н} свайп влево у администратора: {п}, сообщение {сообщение}")
        ч.вкладка(стр, "m"); стр.wait_for_timeout(500)
        м_ = стр.evaluate(f"() => {{ const м = document.querySelector('#presetChipCard .pc-chm[data-mid=\"{первая}\"]'); return м ? {{ метка: (м.querySelector('.pc-cht') || {{}}).textContent || '' }} : null; }}")
        if not м_ or м_["метка"]:
            плохо(f"{н} сообщение в чате после снятия: {м_}")
        ч.вкладка(стр, "c"); стр.wait_for_timeout(400)
    elif п["правок"] != 3 or len(п["отметки"]) != len(до["отметки"]):
        плохо(f"{н} у менеджера свайп влево снял правку: {п}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"drop-{ш}-{роль}{'-n' if ночь else ''}.png"))
    # Свайп вправо по автоматическому пункту — по-прежнему «пропустить».
    было = стр.evaluate("() => document.querySelectorAll('#presetChipCard .pc-skip').length")
    сдвиг(стр, "#presetChipCard [data-skip]", 110)
    стало = стр.evaluate("() => document.querySelectorAll('#presetChipCard .pc-skip').length")
    if стало != было + 1:
        плохо(f"{н} свайп вправо по пункту проверки не пропустил его: было {было}, стало {стало}")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, False, "admin")
                прогон(бр, порт, 390, 844, True, "admin")
                прогон(бр, порт, 390, 844, False, "manager")
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: администратор свайпом влево убирает правку из проверки, сообщение в чате остаётся; короткий сдвиг и менеджер — ничего; подсказка только у администратора; свайп вправо пропускает пункт; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
