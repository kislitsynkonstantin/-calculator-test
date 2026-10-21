#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подписанный договор замораживает каталог: правки цен и опций его не меняют.

Константин 21.10.2026: «когда договор подписан, надо зафиксировать состояние
пресета и опций всех. Чтобы когда в калькуляторе поменяем цену, удалим или
переименуем опцию, в подписанном договоре ничего не поменялось. Нужна
заморозка прям состояния».

Проба держит, на заглушке базы, на 1440 и 390:
  • при подписании каталог уходит в базу одним вызовом preset_frozen_put:
    технология, опции с ценами, проект;
  • каталог в базе меняется — опция переименована и подорожала, другая
    удалена — и цены перезагружены (свежий каталог ждёт в стороне); подписанный пресет, открытый заново,
    показывает прежнее название, прежнюю цену и прежний итог; удалённая
    опция на месте;
  • во вкладке «Пресет» сказано, что цены и опции — на день подписания;
  • закрыли подписанный пресет — расчёт идёт по живому каталогу: новое
    название и новая цена; открыли снова — опять замороженный;
  • отмена подписи возвращает живой каталог;
  • ошибок страницы нет.

    python3 check_signed_freeze.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_approval as па
import check_approval_report as з
import check_signed_lock as сл
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ОПЦИЯ, УДАЛЯЕМАЯ = "w10", "in6"


def плохо(т):
    НАХОДКИ.append(т)


ЗАГЛУШКИ = """() => { window.__ЗАМОРОЗКИ = {}; window.__ВЫЗОВЫ = window.__ВЫЗОВЫ || [];
  window.__RPC.preset_frozen_put = (а) => {
    window.__ВЫЗОВЫ.push(['frozen_put', а.p_code]);
    const с = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === а.p_code);
    if (!с || !с.signed_at) return { __ошибка: 'договор не подписан' };
    const был = window.__ЗАМОРОЗКИ[а.p_code];
    if (был && был.signed_at === с.signed_at) return с.signed_at;
    window.__ЗАМОРОЗКИ[а.p_code] = { signed_at: с.signed_at, frozen: JSON.parse(JSON.stringify(а.p_frozen)) };
    return с.signed_at; };
  window.__RPC.preset_frozen_get = (а) => {
    window.__ВЫЗОВЫ.push(['frozen_get', а.p_code]);
    const с = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === а.p_code);
    const з = window.__ЗАМОРОЗКИ[а.p_code];
    if (!с || !с.signed_at || !з || з.signed_at !== с.signed_at) return null;
    return Object.assign({}, з.frozen, { frozen_at: new Date().toISOString(), frozen_name: 'Проба' }); }; }"""

ВИД = """(ид) => { const р = document.querySelector('.opt-item[data-opt-id="' + ид + '"]');
  const т = document.getElementById('totalDisplay');
  return { есть: !!р, имя: р ? (р.querySelector('.opt-name') || {}).textContent.trim() : null,
    цена: р ? ((р.querySelector('.opt-price') || {}).textContent || '').replace(/\\s+/g, ' ').trim() : null,
    отмечена: !!checkedOptions[ид], итог: т ? т.textContent.replace(/\\s+/g, ' ').trim() : '',
    заморожен: !!(window._заморозка) }; }"""

КАТАЛОГ = """async () => { const оп = window.__ТАБЛИЦЫ.pricing_options;
  const о = оп.find(х => х.product === 'frame' && х.option_id === 'w10');
  о.name = 'Стеклопакет — переименовано в каталоге'; о.price = 99999;
  window.__ТАБЛИЦЫ.pricing_options = оп.filter(х => !(х.product === 'frame' && х.option_id === "in6"));
  await loadPricing('frame', true);
  // Названия каркаса заглушка берёт из своего списка, а не из таблицы, —
  // переименование и удаление кладём в пришедший живой каталог, как их
  // принесла бы база.
  const жд = window._живыеДанные && window._живыеДанные.data;
  if (!жд) return 'каталог не отложен в сторону: заморозки нет';
  const ж = жд.op.find(х => х.option_id === 'w10'); if (ж) ж.name = 'Стеклопакет — переименовано в каталоге';
  жд.op = жд.op.filter(х => х.option_id !== 'in6');
  return ''; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = з.начать(бр, порт, ш, в)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(па.ДАННЫЕ, код)
    стр.evaluate(з.ХРАНИЛИЩЕ)
    стр.evaluate(сл.ОТМЕНА)
    стр.evaluate(ЗАГЛУШКИ)
    стр.evaluate("""() => { window.__проверкаБыла = проверкаПоЧекЛисту;
      window.проверкаПоЧекЛисту = function () { const п = window.__проверкаБыла.apply(this, arguments); п.замечания = п.замечания.filter(з => !з.стоп); return п; }; }""")
    # Опции расчёта — до отправки на согласование: и переименуемая, и удаляемая.
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    for ид in (ОПЦИЯ, УДАЛЯЕМАЯ):
        if not стр.evaluate("(ид) => !!checkedOptions[ид]", ид):
            сл.нажатьОпцию(стр, ид)
    стр.wait_for_timeout(2500)
    до = стр.evaluate(ВИД, ОПЦИЯ)
    до_удал = стр.evaluate(ВИД, УДАЛЯЕМАЯ)
    if not до["отмечена"] or not до_удал["отмечена"]:
        плохо(f"{н} опции не отметились до подписи: {до}, {до_удал}"); стр.close(); return
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-send"); стр.wait_for_timeout(600)
    стр.evaluate("() => { window.__ТАБЛИЦЫ.preset_approvals.forEach(с => { с.price_by = 'u-ред'; с.price_name = 'Ольга Проверкина'; с.price_at = new Date().toISOString(); с.price_print = с.sent_print; }); _согласование.когда = 0; }")
    па.роль(стр, "specialist")
    стр.evaluate("() => решитьСогласование('approved', 'check')"); стр.wait_for_timeout(1500)
    па.роль(стр, "manager")
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-sign"); стр.wait_for_timeout(3000)
    if not стр.evaluate(сл.ПОДПИСАН):
        плохо(f"{н} после «Подписан» договор не подписан"); стр.close(); return

    # ── снимок ушёл в базу один раз ──
    пут = стр.evaluate("(код) => ({ вызовов: window.__ВЫЗОВЫ.filter(х => х[0] === 'frozen_put').length, з: window.__ЗАМОРОЗКИ[код] && window.__ЗАМОРОЗКИ[код].frozen })", код)
    з_ = пут["з"] or {}
    оп = {р["option_id"]: р for р in ((з_.get("data") or {}).get("op") or [])}
    if пут["вызовов"] != 1 or з_.get("tech") != "frame" or оп.get(ОПЦИЯ, {}).get("price") != до_цена(стр):
        плохо(f"{н} снимок при подписи: вызовов {пут['вызовов']}, технология {з_.get('tech')}, цена опции {оп.get(ОПЦИЯ, {}).get('price')}")

    # ── каталог меняется: переименование, цена, удаление ──
    т = стр.evaluate(КАТАЛОГ); стр.wait_for_timeout(1500)
    if т:
        плохо(f"{н} {т}")
    стр.evaluate("() => loadPreset(activePresetId)"); стр.wait_for_timeout(3500)
    после = стр.evaluate(ВИД, ОПЦИЯ)
    после_удал = стр.evaluate(ВИД, УДАЛЯЕМАЯ)
    if (после["имя"], после["цена"], после["итог"]) != (до["имя"], до["цена"], до["итог"]) or not после["заморожен"]:
        плохо(f"{н} подписанный пресет после правки каталога: было {до}, стало {после}")
    if not после_удал["есть"] or not после_удал["отмечена"] or после_удал["имя"] != до_удал["имя"]:
        плохо(f"{н} удалённая из каталога опция пропала из подписанного: было {до_удал}, стало {после_удал}")
    стр.evaluate("() => { if (!document.getElementById('presetChipCard').classList.contains('show')) document.querySelector('#presetChip .pc-body').click(); }")
    стр.wait_for_timeout(300)
    сл.вкладка(стр, "p")
    пл = стр.evaluate("() => { const п = document.querySelector('#presetChipCard .pc-signed-st'); return п ? п.innerText.replace(/\\s+/g, ' ').trim() : ''; }")
    if "на день подписания" not in пл:
        плохо(f"{н} во вкладке «Пресет» не сказано про цены на день подписания: «{пл}»")
    па.вёрстка(стр, н, "вкладка «Пресет» замороженного")
    стр.screenshot(path=f"/tmp/signed-freeze-tab-{ш}.png")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)

    # ── закрыли пресет — живой каталог ──
    стр.evaluate("() => setActivePreset(null)"); стр.wait_for_timeout(3000)
    живой = стр.evaluate(ВИД, ОПЦИЯ)
    if живой["заморожен"] or живой["имя"] != "Стеклопакет — переименовано в каталоге":
        плохо(f"{н} закрытый подписанный пресет: каталог не вернулся к живому: {живой}")
    # ── открыли снова — заморожен ──
    ид_пресета = стр.evaluate("() => Object.keys(loadAllPresets()).find(к => { const п = loadAllPresets()[к]; return п && (п.shortCode || п.sharedId) == '" + str(код) + "'; })")
    стр.evaluate("(ид) => loadPreset(ид)", ид_пресета); стр.wait_for_timeout(3500)
    снова = стр.evaluate(ВИД, ОПЦИЯ)
    if (снова["имя"], снова["цена"], снова["итог"]) != (до["имя"], до["цена"], до["итог"]):
        плохо(f"{н} подписанный пресет, открытый второй раз: было {до}, стало {снова}")

    # ── отмена подписи — живой каталог ──
    стр.evaluate("() => отменитьПодписание()"); стр.wait_for_timeout(3500)
    отм = стр.evaluate(ВИД, ОПЦИЯ)
    if отм["заморожен"] or отм["имя"] != "Стеклопакет — переименовано в каталоге":
        плохо(f"{н} после отмены подписи каталог не живой: {отм}")
    for е in [е for е in ошибки if "supabase.co" not in е][:3]:
        плохо(f"{н} ошибка страницы: {е[:200]}")
    стр.close()


def до_цена(стр):
    return 40000


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900)
                прогон(бр, порт, 390, 844)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: при подписи каталог уходит в базу одним снимком; после переименования, новой цены и удаления в каталоге "
          "подписанный пресет показывает прежние название, цену и итог, удалённая опция на месте, во вкладке «Пресет» — "
          "«на день подписания»; закрытый пресет и отмена подписи возвращают живой каталог; 1440 и 390.")


if __name__ == "__main__":
    главная()
