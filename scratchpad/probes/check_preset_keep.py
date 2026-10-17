#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет с перепиской в чате или согласованием не удаляется.

Константин 17.10.2026: «Пресет, который отправили на согласование или у
которого есть переписка в чате, удалить нельзя. Можно только отозвать из
публичных автору. Но доступ к нему также останется по коду».

Держит база (триггеры миграции preset_approval); проба держит страницу, на
заглушке базы:
  • база говорит «нельзя» (preset_can_delete = false) — вместо подтверждения
    окно-сообщение «Пресет удалить нельзя» с кодом, одна кнопка «Понятно»,
    не красная; пресет в списке, строка кода и облачная запись не тронуты;
  • «можно» — обычное подтверждение с красным «Удалить» и «Отмена»;
    удаление идёт, как прежде;
  • база отказала уже при удалении (42501) — пресет вернулся в список, строка
    кода не удалена, сказано словами;
  • база не ответила (нет функции) — удаление идёт, как прежде;
  • окно на 390 и 1440: кнопка в поле окна, «Отмена» не видна.

    python3 check_preset_keep.py
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


ОКНО = """() => { const д = document.getElementById('confirmDialog'), ок = document.getElementById('confirmDialogOk'), от = document.getElementById('confirmDialogCancel');
  const б = document.getElementById('confirmDialogBox').getBoundingClientRect(), ко = ок.getBoundingClientRect();
  return { открыто: д.classList.contains('show'), инфо: д.classList.contains('cd-info'), заголовок: document.getElementById('confirmDialogTitle').textContent,
    текст: document.getElementById('confirmDialogMsg').textContent, ок: ок.textContent, отменаВидна: getComputedStyle(от).display !== 'none',
    цвет: getComputedStyle(ок).backgroundColor, кнопкаВОкне: ко.left >= б.left && ко.right <= б.right && ко.width > 0 }; }"""

СОСТОЯНИЕ = """(ид) => ({ вСписке: !!loadAllPresets()[ид], строкаКода: (window.__ТАБЛИЦЫ.preset_links || []).some(х => х.preset_id === ид),
  облако: ((window.__ТАБЛИЦЫ.presets || []).find(х => х.id === ид) || {}).deleted_at || null })"""


def новый(стр):
    """Сохранить расчёт новым пресетом — вернуть его id и код."""
    стр.evaluate("() => { закрытьКарточкуЗначка(); setActivePreset(null); }")
    стр.wait_for_timeout(300)
    стр.evaluate("() => { if (typeof updatePresetSaveBtn === 'function') updatePresetSaveBtn(); отрисоватьЗначокПресета(); }")
    стр.wait_for_timeout(300)
    стр.evaluate("() => { const { state, autoName } = данныеНовогоПресета(); сохранитьНовыйПресет(autoName + ' ' + Math.random().toString(36).slice(2, 5), autoName, state); }")
    стр.wait_for_timeout(2600)
    return стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return [activePresetId, p && (p.shortCode || p.sharedId)]; }")


def нажать(стр, н, что):
    """Нажать кнопку окна; окна нет — находка, а не падение пробы."""
    if not стр.evaluate("() => document.getElementById('confirmDialog').classList.contains('show')"):
        плохо(f"{н} {что}: окно не открыто, нажимать нечего")
        return False
    стр.locator("#confirmDialogOk").click()
    return True


def прогон(бр, порт, ш, в, полный):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    ид = стр.evaluate("() => activePresetId")
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not ид or not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate("() => { window.__СПРОШЕНО = []; window.__RPC.preset_can_delete = (а) => { window.__СПРОШЕНО.push(а.p_code); return false; }; }")
    стр.evaluate("(ид) => deletePreset(ид)", ид); стр.wait_for_timeout(500)
    о = стр.evaluate(ОКНО)
    с = стр.evaluate(СОСТОЯНИЕ, ид)
    кр = "%s %s" % (код[:3], код[3:])
    if not о["открыто"] or not о["инфо"] or о["заголовок"] != "Пресет удалить нельзя" or кр not in о["текст"] or "переписка в чате или согласование" not in о["текст"] \
            or о["ок"] != "Понятно" or о["отменаВидна"] or "224, 85, 85" in о["цвет"] or "192, 57, 43" in о["цвет"] or not о["кнопкаВОкне"]:
        плохо(f"{н} окно «нельзя удалить»: {о}")
    if not с["вСписке"] or not с["строкаКода"] or с["облако"]:
        плохо(f"{н} пресет с историей тронут: {с}")
    if стр.evaluate("() => window.__СПРОШЕНО") != [код]:
        плохо(f"{н} база не спрошена кодом пресета: {стр.evaluate('() => window.__СПРОШЕНО')}")
    стр.screenshot(path=str(СНИМКИ / f"keep-{ш}.png"))
    нажать(стр, н, "«Понятно»"); стр.wait_for_timeout(250)
    о = стр.evaluate(ОКНО)
    if о["открыто"] or о["инфо"]:
        плохо(f"{н} «Понятно» не закрыло окно или оставило вид сообщения: {о}")
    if not полный:
        if ошибки: плохо(f"{н} ошибки страницы: {ошибки[:3]}")
        стр.close(); return
    # «Можно» — обычное подтверждение, удаление как прежде.
    стр.evaluate("() => { window.__RPC.preset_can_delete = () => true; }")
    стр.evaluate("(ид) => deletePreset(ид)", ид); стр.wait_for_timeout(400)
    о = стр.evaluate(ОКНО)
    if not о["открыто"] or о["инфо"] or о["ок"] != "Удалить" or not о["отменаВидна"]:
        плохо(f"{н} подтверждение обычного удаления: {о}")
    нажать(стр, н, "обычное удаление"); стр.wait_for_timeout(900)
    с = стр.evaluate(СОСТОЯНИЕ, ид)
    if с["вСписке"] or с["строкаКода"] or not с["облако"]:
        плохо(f"{н} обычное удаление: {с}")
    # Отказ базы при удалении — пресет вернулся.
    ид2, код2 = новый(стр)
    if not ид2 or not код2:
        плохо(f"{н} второй пресет не сохранился"); стр.close(); return
    стр.evaluate("() => { window.__RPC.preset_can_delete = () => true; window.__былоУдаление = sbDeletePreset; window.sbDeletePreset = async () => ({ code: '42501', message: 'нельзя' }); }")
    стр.evaluate("(ид) => deletePreset(ид)", ид2); стр.wait_for_timeout(400)
    нажать(стр, н, "отказ базы"); стр.wait_for_timeout(900)
    с = стр.evaluate(СОСТОЯНИЕ, ид2)
    о = стр.evaluate(ОКНО)
    if not с["вСписке"] or not с["строкаКода"] or not о["открыто"] or о["заголовок"] != "Пресет удалить нельзя":
        плохо(f"{н} отказ базы при удалении: {с}, окно {о}")
    нажать(стр, н, "«Понятно» после отказа"); стр.wait_for_timeout(200)
    стр.evaluate("() => { window.sbDeletePreset = window.__былоУдаление; }")
    # Нет ответа — как прежде.
    стр.evaluate("() => { delete window.__RPC.preset_can_delete; }")
    стр.evaluate("(ид) => deletePreset(ид)", ид2); стр.wait_for_timeout(400)
    о = стр.evaluate(ОКНО)
    if not о["открыто"] or о["ок"] != "Удалить":
        плохо(f"{н} без ответа базы нет обычного подтверждения: {о}")
    нажать(стр, н, "удаление без ответа базы"); стр.wait_for_timeout(900)
    if стр.evaluate(СОСТОЯНИЕ, ид2)["вСписке"]:
        плохо(f"{н} без ответа базы пресет не удалился")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, True)
                прогон(бр, порт, 390, 844, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: пресет с историей не удаляется и объясняет это окном с кодом, обычное удаление как прежде, "
          "отказ базы возвращает пресет, без ответа базы — прежний путь, окно на 390 и 1440.")


if __name__ == "__main__":
    главная()
