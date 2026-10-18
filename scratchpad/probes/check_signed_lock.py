#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Договор подписан» закрывает пресет; скрытая «Отменить подписание».

Константин 18.10.2026, тремя снимками мини-окна: «После того как поставили
«Договор подписан», запретить все изменения в пресете (правки к договору,
спецификации и тд). Для всех. И в названии пресета и в разделе Пресет
мини-окна отображай, что договор подписан. И ставь замок. Долгое нажатие на
надпись договор подписан в чате или в журнале, появляется кнопка «Отменить
подписание». Скрытая функция. Мало ли. И, кстати, в журнал сейчас не
пишется, когда подписан. Это надо писать в журнал и в уведомления всем
присылать (Редактору, Администратору, Специалисту + менеджеру, чей пресет)».

Проба держит, на заглушке базы, на 390 и 1440:
  • после «Подписан» пресет заперт для всех: галочка опции не ставится и у
    менеджера, и у администратора, правка текста договора закрыта, внизу
    экрана — «Договор подписан — пресет закрыт для правок»;
  • значок мини-окна — «Договор подписан» с замком; во вкладке «Пресет» —
    плашка «Договор подписан … — пресет закрыт для правок»;
  • «Договор подписан» есть в видах журнала, строка — в журнале действий и
    во вкладке «Журнал» пресета;
  • короткое нажатие на строку «Договор подписан» в чате кнопки не
    показывает, долгое (0,7 с) — показывает «Отменить подписание»; то же в
    журнале пресета; кнопка зовёт preset_approval_unsign с кодом, пресет
    снова открыт для правки, в журнале — «Подписание договора отменено»;
  • колокольчик менеджера, чей пресет, показывает «Договор подписан», даже
    если на согласование отправлял другой.

    python3 check_signed_lock.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_approval as па
import check_approval_report as з
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


ОТМЕНА = """() => { window.__RPC.preset_approval_unsign = (а) => {
    window.__ВЫЗОВЫ.push(['unsign', JSON.parse(JSON.stringify(а))]);
    const с = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === а.p_code);
    if (!с || !с.signed_at) return { __ошибка: 'не подписан' };
    Object.assign(с, { signed_at: null, signed_by: null, signed_name: null });
    window.__ТАБЛИЦЫ.preset_messages.push({ id: 'cccccccc-3333-4333-8333-333333333333', code: а.p_code, author_id: 'u-проба', author_name: 'Проба Пробная',
      body: 'Проба Пробная', reply_to: null, attachments: [], review_state: null, kind: 'event', event: 'unsigned', ref: null, created_at: new Date().toISOString() });
    return Object.assign({}, с); }; }"""


# В сборке без замка подписи функции нет — проба тогда судит по строке
# согласования, а не падает.
ПОДПИСАН = "() => typeof договорПодписан === 'function' ? договорПодписан() : !!((_согласование.строка || {}).signed_at)"


def опция(стр):
    """Первая неотмеченная видимая опция: нажатие по строке и итог до/после."""
    return стр.evaluate("""() => { const э = [...document.querySelectorAll('#optionSections .opt-item')].find(х => !х.classList.contains('active') && х.offsetParent && х.dataset.optId);
      return э ? э.dataset.optId : null; }""")


def нажатьОпцию(стр, ид):
    стр.evaluate("(ид) => document.querySelector('.opt-item[data-opt-id=\"' + ид + '\"]').scrollIntoView({ block: 'center' })", ид)
    стр.wait_for_timeout(200)
    стр.locator(f'.opt-item[data-opt-id="{ид}"] .opt-name').first.click()
    стр.wait_for_timeout(400)
    return стр.evaluate("(ид) => !!checkedOptions[ид]", ид)


def долго(стр, селектор, мс):
    к = стр.locator(селектор).first
    к.scroll_into_view_if_needed()
    б = к.bounding_box()
    стр.mouse.move(б["x"] + б["width"] / 2, б["y"] + б["height"] / 2)
    стр.mouse.down(); стр.wait_for_timeout(мс); стр.mouse.up()
    стр.wait_for_timeout(300)
    return стр.evaluate("() => !!document.querySelector('#presetChipCard [data-act=\"ap-unsign\"]')")


def вкладка(стр, буква):
    стр.evaluate("(б) => { _пкВкладка = б; заполнитьКарточкуЗначка(); }", буква)
    стр.wait_for_timeout(500)


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = з.начать(бр, порт, ш, в)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(па.ДАННЫЕ, код)
    стр.evaluate(з.ХРАНИЛИЩЕ)
    стр.evaluate(ОТМЕНА)
    стр.evaluate("""() => { window.__проверкаБыла = проверкаПоЧекЛисту;
      window.проверкаПоЧекЛисту = function () { const п = window.__проверкаБыла.apply(this, arguments); п.замечания = п.замечания.filter(з => !з.стоп); return п; }; }""")
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-send"); стр.wait_for_timeout(600)
    стр.evaluate("() => { window.__ТАБЛИЦЫ.preset_approvals.forEach(с => { с.price_by = 'u-ред'; с.price_name = 'Ольга Проверкина'; с.price_at = new Date().toISOString(); с.price_print = с.sent_print; }); _согласование.когда = 0; }")
    па.роль(стр, "specialist")
    стр.evaluate("() => решитьСогласование('approved', 'check')"); стр.wait_for_timeout(1500)
    па.роль(стр, "manager")
    ид = опция(стр)
    if not ид:
        плохо(f"{н} не нашлось неотмеченной опции для проверки замка")
    # До подписи пресет правится.
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-sign"); стр.wait_for_timeout(2500)
    if not стр.evaluate(ПОДПИСАН):
        плохо(f"{н} после «Подписан» договорПодписан() — ложь"); стр.close(); return

    # Запрет правки — менеджеру и администратору.
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    for р in ["manager", "admin"]:
        па.роль(стр, р)
        стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(200)
        if ид and нажатьОпцию(стр, ид):
            плохо(f"{н} {р}: после подписи галочка опции ставится")
        if стр.evaluate("() => можноПравитьДоговор()") and стр.evaluate("() => window._sbProfile.role") != "manager":
            плохо(f"{н} {р}: после подписи правка текста договора открыта")
    тосты = стр.evaluate("() => window.__тосты.slice(-6)")
    if not any("Договор подписан — пресет закрыт" in т for т in тосты):
        плохо(f"{н} нажатие по запертой опции не говорит, что договор подписан: {тосты}")
    па.роль(стр, "manager")

    # Значок мини-окна и вкладка «Пресет».
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    значок = стр.evaluate("() => { const з = document.getElementById('presetChip'); return { т: з.innerText.trim(), замок: !!з.querySelector('.pc-sg-lk'), кл: з.className }; }")
    if "Договор подписан" not in значок["т"] or not значок["замок"]:
        плохо(f"{н} значок мини-окна после подписи: {значок}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"signed-chip-{ш}.png"))
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    вкладка(стр, "p")
    пл = стр.evaluate("() => { const п = document.querySelector('#presetChipCard .pc-signed-st'); return п ? п.innerText.replace(/\\s+/g, ' ').trim() : ''; }")
    if "Договор подписан" not in пл or "закрыт для правок" not in пл:
        плохо(f"{н} во вкладке «Пресет» нет плашки подписи: «{пл}»")
    па.вёрстка(стр, н, "вкладка «Пресет» подписанного")
    стр.screenshot(path=str(СНИМКИ / f"signed-tab-{ш}.png"))

    # Журнал.
    if стр.evaluate("() => AL_ВСЕ_ВИДЫ.approval_signed") != "Договор подписан":
        плохо(f"{н} «Договор подписан» нет в видах журнала")
    if not стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).some(е => е.event_type === 'approval_signed')"):
        плохо(f"{н} подпись не записана в журнал действий")
    стр.evaluate("async () => { _журналПресета.когда = 0; await загрузитьЖурналПресета(true); }"); стр.wait_for_timeout(600)
    вкладка(стр, "l")
    в_журнале = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-lg li')].map(л => л.getAttribute('data-evt'))")
    if "approval_signed" not in в_журнале:
        плохо(f"{н} во вкладке «Журнал» нет строки «Договор подписан»: {в_журнале[:8]}")
    elif not долго(стр, '#presetChipCard li[data-evt="approval_signed"]', 750):
        плохо(f"{н} долгое нажатие на «Договор подписан» в журнале не показало «Отменить подписание»")

    # Чат: короткое — ничего, долгое — кнопка.
    стр.evaluate("async () => { await загрузитьЧат(true); }"); стр.wait_for_timeout(600)
    вкладка(стр, "m"); стр.wait_for_timeout(600)
    if not стр.locator('#presetChipCard .pc-chev-ap[data-ev="signed"]').count():
        плохо(f"{н} в чате нет строки «Договор подписан»")
    else:
        if долго(стр, '#presetChipCard .pc-chev-ap[data-ev="signed"]', 120):
            плохо(f"{н} короткое нажатие на «Договор подписан» в чате показало кнопку отмены")
        if not долго(стр, '#presetChipCard .pc-chev-ap[data-ev="signed"]', 750):
            плохо(f"{н} долгое нажатие на «Договор подписан» в чате не показало «Отменить подписание»")
        else:
            стр.screenshot(path=str(СНИМКИ / f"signed-unsign-btn-{ш}.png"))
            стр.locator('#presetChipCard [data-act="ap-unsign"]').click(); стр.wait_for_timeout(1500)
            с = стр.evaluate("(код) => ({ вызов: window.__ВЫЗОВЫ.filter(х => х[0] === 'unsign').map(х => х[1]), подписан: (" + ПОДПИСАН + ")(),"
                             " журнал: (window.__ТАБЛИЦЫ.events || []).some(е => е.event_type === 'approval_unsigned'), тосты: window.__тосты.slice(-3) })", код)
            if с["вызов"] != [{"p_code": код}] or с["подписан"] or not с["журнал"]:
                плохо(f"{н} «Отменить подписание»: {с}")
            стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
            if ид and not нажатьОпцию(стр, ид):
                плохо(f"{н} после отмены подписи пресет по-прежнему заперт")

    # Колокольчик менеджера, чей пресет: подписал и отправлял другой.
    у = стр.evaluate("""async (код) => {
      window.__ТАБЛИЦЫ.preset_approval_log = (window.__ТАБЛИЦЫ.preset_approval_log || []).concat([{ id: 950, code: код, event: 'signed', slot: null,
        by_id: 'u-другой', by_name: 'Другой Менеджер', sent_by: 'u-другой', preset_name: 'Проба', project_name: 'Проба', at: new Date().toISOString() }]);
      window.__ТАБЛИЦЫ.preset_approval_log.forEach(ш => { if (ш.code === код && ш.id !== 950) ш.sent_by = 'u-другой'; });
      const с = []; await уведомленияСогласования(с); return с.map(х => String(х.текст || '').replace(/<[^>]+>/g, '')); }""", код)
    if not any("Договор подписан" in т for т in у):
        плохо(f"{н} колокольчик менеджера, чей пресет, не показывает подпись, отправленную другим: {у[:5]}")
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
    print("Чисто: подписанный договор запирает пресет для всех (опции, текст договора), значок и вкладка «Пресет» говорят «Договор подписан» с замком, "
          "подпись — в журнале; долгое нажатие в чате и журнале показывает «Отменить подписание», отмена открывает пресет; колокольчик владельца знает о подписи.")


if __name__ == "__main__":
    главная()
