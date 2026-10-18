#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подсказка под открытой правкой из чата: что поменялось в расчёте после неё.

Константин 18.10.2026 на вопрос, может ли код без ИИ проверять ручные правки
из чата: «5. Да» — подсказка по журналу пресета, галочку ставит проверяющий.

Проба держит, на заглушке базы:
  • под открытой правкой — «После правки: добавлено «…»; убрано «…»; …»
    по событиям журнала после времени сообщения; события до него не идут;
  • названий опций — не больше двух, дальше «и ещё N»; частей — не больше
    трёх, дальше «и ещё N»;
  • своё, что журнал ещё не записал (опции копятся 30 секунд), — тоже;
  • правка, после которой ничего не меняли, — «После правки расчёт не
    менялся»; у выполненной правки подсказки нет;
  • вёрстка на 390 и 1440: подсказка в поле карточки, не налезает на
    соседний пункт.

    python3 check_chat_hint.py
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


ДАННЫЕ = """(код) => {
  const т = window.__ТАБЛИЦЫ, д = Date.now(), мин = 60e3;
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  const сообщ = (ид, тело, назад, сост) => ({ id: ид, code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина', body: тело, reply_to: null,
    review_state: сост, kind: 'msg', attachments: [], created_at: new Date(д - назад * мин).toISOString() });
  т.preset_messages = [
    сообщ('a0000000-0000-4000-8000-000000000001', 'Добавь водосток и убери вальмовую кровлю', 60, 'open'),
    сообщ('a0000000-0000-4000-8000-000000000002', 'Проверь скидку', 5, 'open'),
    сообщ('a0000000-0000-4000-8000-000000000003', 'Фанеру поменять', 50, 'done'),
  ];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  const соб = (вид, назад, rows, obj) => ({ id: 'e' + вид + назад, created_at: new Date(д - назад * мин).toISOString(), event_type: вид, user_id: 'u-проба',
    details: { presetCode: код, obj: obj || null, rows: rows || [] } });
  window.__СОБЫТИЯ = [
    соб('options_batch', 90, [{ k: 'Добавлены', a: '', b: 'До правки — не идёт' }]),
    соб('options_batch', 40, [{ k: 'Добавлены', a: '', b: 'Водосточная система ПВХ\\nСнегозадержатели трубчатые\\nКолпак на трубу' }, { k: 'Убраны', a: '', b: 'Вальмовая кровля' }]),
    соб('gift_marked', 30, [], 'Фанера 21 мм'),
    соб('option_price_changed', 25, [], 'Цена каталога — не о расчёте'),
    соб('discount_changed', 20, []),
    соб('approval_sent', 10, []),
  ];
}"""

ПОДСКАЗКИ = """() => [...document.querySelectorAll('#presetChipCard .pc-pr li')].map(л => ({
  текст: (л.querySelector('.pc-pr-tx') || {}).textContent || '', после: (л.querySelector('.pc-pr-af') || {}).textContent || '',
  пусто: !!л.querySelector('.pc-pr-af0'), готово: л.classList.contains('done') }))"""

ВЁРСТКА = """() => { const к = document.getElementById('presetChipCard'), r = к.getBoundingClientRect(), cs = getComputedStyle(к), н = [];
  const л = r.left + parseFloat(cs.paddingLeft), п = r.right - parseFloat(cs.paddingRight);
  const пп = [...к.querySelectorAll('.pc-pr li')];
  к.querySelectorAll('.pc-pr-af').forEach(э => { const б = э.getBoundingClientRect(); if (!б.width) return;
    if (б.left < л - .5 || б.right > п + .5) н.push('подсказка за полем карточки');
    const ли = э.closest('li'), след = ли.nextElementSibling;
    if (б.bottom > ли.getBoundingClientRect().bottom + .5) н.push('подсказка вылезла из пункта');
    if (след && след.getBoundingClientRect().top < б.bottom - .5) н.push('подсказка налезла на следующий пункт'); });
  return н; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(700)
    стр.evaluate("(код) => { _al2Набор = null; _журналПресета = { код: String(код), события: window.__СОБЫТИЯ, ошибка: '', грузится: false, когда: Date.now(), заранее: false }; }", код)
    ч.вкладка(стр, "c"); стр.wait_for_timeout(500)
    п = {х["текст"]: х for х in стр.evaluate(ПОДСКАЗКИ)}
    первая = п.get("Добавь водосток и убери вальмовую кровлю", {})
    ждали = "После правки: добавлено «Водосточная система ПВХ», «Снегозадержатели трубчатые» и ещё 1; убрано «Вальмовая кровля»; опция отмечена подарком — «Фанера 21 мм»; и ещё 1."
    if первая.get("после") != ждали:
        плохо(f"{н} подсказка под первой правкой: «{первая.get('после')}», ждали «{ждали}»")
    if "До правки" in первая.get("после", "") or "каталога" in первая.get("после", ""):
        плохо(f"{н} в подсказку попало событие до правки или не о расчёте")
    вторая = п.get("Проверь скидку", {})
    if вторая.get("после") != "После правки расчёт не менялся" or not вторая.get("пусто"):
        плохо(f"{н} правка без изменений после неё: {вторая}")
    if п.get("Фанеру поменять", {}).get("после"):
        плохо(f"{н} у выполненной правки есть подсказка")
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-hint-{ш}.png"))
    # Своё, ещё не записанное.
    стр.evaluate("""() => { const о = OPTIONS.find(x => !x.included && !checkedOptions[x.id]); window.__ОПЦ = о.name;
      _al2Набор = { плюс: new Set([о.id]), минус: new Set(), итогДо: 0, проект: null }; заполнитьКарточкуЗначка(); }""")
    стр.wait_for_timeout(300)
    п = {х["текст"]: х for х in стр.evaluate(ПОДСКАЗКИ)}
    имя = стр.evaluate("() => window.__ОПЦ")
    if f"«{имя}»" not in п.get("Проверь скидку", {}).get("после", ""):
        плохо(f"{н} своё незаписанное не попало в подсказку: {п.get('Проверь скидку')}")
    стр.evaluate("() => { _al2Набор = null; }")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


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
    print("Чисто: подсказка «После правки: …» по журналу после времени сообщения, пределы имён и частей, своё незаписанное, "
          "«расчёт не менялся», у выполненной нет, вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
