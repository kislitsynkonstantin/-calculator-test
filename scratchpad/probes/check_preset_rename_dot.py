#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Переименование пресета: точка активного не попадает в имя.

Константин 17.10.2026, двумя снимками окна «Пресеты»: «Когда нажимаешь
редактировать активный пресет, то точка переходит в редактирование и потом
сохраняется, если её не удалить». Перед именем активного пресета стоит зелёная
точка отдельным span без пробела после неё, а переименование брало текст
карточки и отрезало только «● » с пробелом.

Проба держит, на 390 и 1440:
  • у активного пресета поле переименования начинается с имени, без точки;
  • Enter, ничего не меняя, оставляет имя прежним — и в записи пресета, и в
    карточке (на карточке точка по-прежнему стоит, но в имени её нет);
  • новое имя сохраняется как набрано;
  • у неактивного пресета поле — тоже ровно имя.

    python3 check_preset_rename_dot.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      selectProjectOption(1); await new Promise(r => setTimeout(r, 700)); }""")
    # Два пресета: первый — неактивный, второй — активный.
    for и in range(2):
        if и:
            стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 700)); }")
        стр.evaluate("() => { activePresetId = null; try { отрисоватьЗначокПресета(); } catch (e) {} }")
        стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
        стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
        if стр.locator("#pcName").count():
            стр.locator("#pcName").press("Enter")
        стр.wait_for_timeout(1800)
    д = стр.evaluate("() => { const в = loadAllPresets(); return { активный: activePresetId, все: Object.values(в).map(п => ({ id: п.id, имя: п.name })) }; }")
    if len(д["все"]) < 2 or not д["активный"]:
        НАХОДКИ.append(f"{н} не удалось сохранить два пресета: {д}"); стр.close(); return
    акт = next(п for п in д["все"] if п["id"] == д["активный"])
    неакт = next(п for п in д["все"] if п["id"] != д["активный"])
    стр.evaluate("() => { openPresetPanel(); }"); стр.wait_for_timeout(700)
    карточка = стр.evaluate("(ид) => (document.getElementById('pname-' + ид) || {}).textContent || ''", акт["id"])
    if not карточка.startswith("●"):
        НАХОДКИ.append(f"{н} у активного пресета на карточке нет точки — проба проверяет не то: «{карточка}»")

    def переименовать(ид):
        стр.evaluate("(ид) => renamePreset(ид)", ид); стр.wait_for_timeout(200)
        return стр.evaluate("() => (document.querySelector('.pcard-rename-input') || {}).value")

    поле = переименовать(акт["id"])
    if поле != акт["имя"]:
        НАХОДКИ.append(f"{н} поле переименования активного: «{поле}», а имя «{акт['имя']}»")
    стр.locator(".pcard-rename-input").press("Enter"); стр.wait_for_timeout(500)
    после = стр.evaluate("(ид) => ({ имя: loadAllPresets()[ид].name, карточка: (document.getElementById('pname-' + ид) || {}).textContent || '' })", акт["id"])
    if после["имя"] != акт["имя"] or "●●" in после["карточка"] or after_dot(после["карточка"]) != акт["имя"]:
        НАХОДКИ.append(f"{н} Enter без правки изменил имя активного: «{после['имя']}», карточка «{после['карточка']}»")
    переименовать(акт["id"])
    стр.locator(".pcard-rename-input").fill("Новое имя пресета"); стр.locator(".pcard-rename-input").press("Enter"); стр.wait_for_timeout(500)
    if стр.evaluate("(ид) => loadAllPresets()[ид].name", акт["id"]) != "Новое имя пресета":
        НАХОДКИ.append(f"{н} новое имя активного пресета не сохранилось как набрано")
    поле = переименовать(неакт["id"])
    if поле != неакт["имя"]:
        НАХОДКИ.append(f"{н} поле переименования неактивного: «{поле}», а имя «{неакт['имя']}»")
    if ошибки:
        НАХОДКИ.append(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def after_dot(т):
    return т.lstrip("●").strip()


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
    print("Чисто: у активного и неактивного пресета поле переименования — ровно имя, без точки; Enter без правки имя не меняет, "
          "новое сохраняется как набрано — на 390 и 1440.")


if __name__ == "__main__":
    главная()
