#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Меню документа в окне печати закрывается нажатием в любом месте мимо него.

Константин, 22.10.2026, снимком телефона с открытым меню поверх правил
эксплуатации: «когда открыто выпадающее меню нажатие в любой области вне меню
закрывай его». Меню закрывалось только по click в окне калькулятора, а лист
документа — отдельный кадр (iframe): нажатие по нему до окна не доходило, а
Safari на телефоне не шлёт click и с мест, на которые нечем нажать.

Проба на 390 и 1440 открывает меню и нажимает: по листу документа (в кадре),
по шапке окна печати мимо меню, по затемнению. После каждого — меню закрыто.
Нажатие по самой кнопке меню его не закрывает, а пункт меню выбирает документ.

Там же — номера договоров бруса (тот же снимок): в данных договора сохранено
«5997878-КАР» и общий «№ договора» пуст. Основной договор бруса выходит
«-КБ», а покраска, у которой своего поля нет, — «-ПОК» от того же номера, а
не «№ ____».

    python3 check_entity_menu_outside.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
import check_glulam_contracts as кд
import check_glulam_sections as г
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ОТКРЫТО = "() => document.getElementById('previewEntityMenu').style.display !== 'none'"
# Нажатие в точке: pointerdown по элементу под ней, внутри кадра — по элементу кадра.
НАЖАТЬ_БЕЗ_CLICK = """(т) => { let д = document, x = т.x, y = т.y, э = д.elementFromPoint(x, y), где = 'окно';
  if (э && э.tagName === 'IFRAME') { const р = э.getBoundingClientRect(); д = э.contentDocument; x -= р.left; y -= р.top; э = д.elementFromPoint(x, y); где = 'кадр'; }
  if (!э) return 'пусто';
  э.dispatchEvent(new (д.defaultView.PointerEvent)('pointerdown', { bubbles: true, cancelable: true, composed: true, clientX: x, clientY: y, pointerType: 'touch', isPrimary: true }));
  return где + ':' + э.tagName.toLowerCase(); }"""


def открыть_меню(стр):
    if not стр.evaluate(ОТКРЫТО):
        стр.locator('#previewEntityBtn').click(); стр.wait_for_timeout(250)
    return стр.evaluate(ОТКРЫТО)


def проверить(стр, ш):
    # Документом — правила: лист в кадре, как на снимке.
    о.выбрать(стр, 'rules')
    кадр = стр.evaluate("""() => { const к = [...document.querySelectorAll('#printOverlay iframe')].find(к => к.getClientRects().length && к.getBoundingClientRect().height > 200);
      if (!к) return null; const р = к.getBoundingClientRect(); return { x: р.left + р.width / 2, y: Math.max(р.top + 20, Math.min(р.bottom, innerHeight) - 60) }; }""")
    if not кадр:
        НАХОДКИ.append(f"[{ш}] лист документа в кадре не найден"); return
    меню = lambda: стр.evaluate("() => { const р = document.getElementById('previewEntityMenu').getBoundingClientRect(); return { l: р.left, r: р.right, t: р.top, b: р.bottom }; }")
    for имя, точка in (("по листу документа", lambda: кадр),
                       ("по шапке окна мимо меню", lambda: {"x": ш - 70, "y": стр.evaluate("() => document.getElementById('previewEntityBtn').getBoundingClientRect().top + 10")}),
                       ("у нижнего края окна", lambda: {"x": 12, "y": 880})):
        if not открыть_меню(стр):
            НАХОДКИ.append(f"[{ш}] меню документа не открылось кнопкой"); return
        т = точка(); р = меню()
        if р["l"] <= т["x"] <= р["r"] and р["t"] <= т["y"] <= р["b"]:
            continue  # точка под самим меню — не «мимо»
        # Как Safari на телефоне: нажатие приходит pointerdown, а click с места,
        # на которое нечем нажать, не приходит вовсе. Chromium шлёт click с
        # любого места, и проба мышью прежний дефект не видела.
        куда = стр.evaluate(НАЖАТЬ_БЕЗ_CLICK, т); стр.wait_for_timeout(250)
        if стр.evaluate(ОТКРЫТО):
            НАХОДКИ.append(f"[{ш}] нажатие {имя} ({round(т['x'])}, {round(т['y'])}, {куда}) не закрыло меню")
    # Нажатие по кнопке меню — переключатель, а не «мимо».
    открыть_меню(стр)
    стр.locator('#previewEntityBtn').click(); стр.wait_for_timeout(250)
    if стр.evaluate(ОТКРЫТО):
        НАХОДКИ.append(f"[{ш}] кнопка меню не закрыла открытое меню")
    стр.locator('#previewEntityBtn').click(); стр.wait_for_timeout(250)
    if not стр.evaluate(ОТКРЫТО):
        НАХОДКИ.append(f"[{ш}] кнопка меню не открыла его повторно")
    о.выбрать(стр, '1')
    if стр.evaluate("() => previewEntity") not in ('contract', 'kar', '1') and 'договор' not in стр.evaluate("() => document.getElementById('previewEntityBtn').textContent").lower():
        НАХОДКИ.append(f"[{ш}] пункт меню не выбрал основной договор")


def номера_бруса(бр, порт):
    к = бр.new_context(viewport={"width": 1440, "height": 900})
    стр = к.new_page(); ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(кд.таблицы(), ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    кд.открыть(стр, 'glulam')
    н = стр.evaluate("""() => { document.getElementById('contractNumber').value = '';
      const з = (id, в) => { const э = document.getElementById(id); if (э) э.value = в; };
      з('cdContractNumKar', '5997878-КАР'); з('cdContractNumO', '5997878-ОТД');
      return [1, 2, 3].map(и => естьДоговор(и) ? getContractVarsKar(и).contractNumKar : null); }""")
    ждём = ['5997878-КБ', '5997878-ОТД', '5997878-ПОК']
    if н != ждём:
        НАХОДКИ.append(f"номера договоров бруса при сохранённом «-КАР» и пустом общем номере: {н}, ждём {ждём}")
    стр.evaluate("() => { document.getElementById('cdContractNumKar').value = ''; document.getElementById('contractNumber').value = '777'; openContractDataModal(); }")
    стр.wait_for_timeout(300)
    поле = стр.evaluate("() => { const п = document.getElementById('cdContractNumKar'); return [п.value, п.placeholder, п.previousElementSibling.textContent]; }")
    if поле[0] != '777-КБ' or 'КБ' not in поле[1] or 'КБ' not in поле[2]:
        НАХОДКИ.append(f"окно данных договора у бруса подставляет основной договор не с «-КБ»: {поле}")
    if ош:
        НАХОДКИ.append(f"ошибки страницы: {ош[:3]}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                к, стр, ош = о.начать(бр, порт, ш, "admin")
                проверить(стр, ш)
                if ош:
                    НАХОДКИ.append(f"[{ш}] ошибки страницы: {ош[:3]}")
                к.close()
            номера_бруса(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: меню документа закрывается нажатием по листу, по шапке окна и у края, кнопка его переключает, пункт выбирает документ — на 390 и 1440; у бруса основной договор «-КБ», покраска «-ПОК» и без общего номера.")


if __name__ == "__main__":
    главная()
