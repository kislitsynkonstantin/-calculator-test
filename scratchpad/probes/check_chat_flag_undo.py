#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Отразить в правках» в чате — «Отменить» у самой кнопки, 3 секунды.

Константин 18.10.2026, снимком варианта А макета
mockups/chat-tap-guard-v2.html: «Этот делай». Отметка подсвечивает значок
сразу, а в базу, строкой в чат и в журнал уходит, когда время на отмену вышло.

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • нажатие — значок нажат, рядом «Отменить», у имени подписи «в правках» нет,
    пузырь сообщения не перекрашен; правка сразу видна в числе «Проверки»;
    за 2,5 секунды база не спрошена, журнал пуст;
  • «Отменить» — значок отжат, и ни через 3,5 секунды, ни позже ни базы, ни
    журнала; второе нажатие на значок — та же отмена;
  • без отмены: через 3 секунды один запрос с «open», «Отменить» пропадает,
    в журнале «добавлена в проверку»;
  • перезагрузка ленты из базы, пока идёт отсчёт, отметку не стирает;
  • вкладка ушла в фон — отметка уходит сразу, не дожидаясь трёх секунд;
  • касание, остановившее едущую ленту, отметку не ставит;
  • «Выполнено» в секунды отмены: сначала уходит «open», потом «done»;
  • значок не сдвигается, когда встаёт «Отменить», — у чужого сообщения
    «Отменить» справа, у своего слева; «Отменить» внутри карточки, поле
    нажатия не меньше 44 px, текст не обрезан; вёрстка на 390 и 1440.

    python3 check_chat_flag_undo.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
ЧУЖОЕ = "11111111-1111-4111-8111-111111111111"
СВОЁ = "22222222-2222-4222-8222-222222222222"
ТРЕТЬЕ = "33333333-3333-4333-8333-333333333333"


def плохо(т):
    НАХОДКИ.append(т)


СОСТ = """(ид) => { const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid="' + ид + '"]');
  if (!м_) return null;
  const ф = м_.querySelector('[data-act="ch-flag"]'), о = м_.querySelector('[data-act="ch-flag-undo"]');
  return { нажат: ф.getAttribute('aria-pressed'), флаг: ф.getBoundingClientRect().left, отмена: !!о,
    отменаСлева: о ? о.getBoundingClientRect().right <= ф.getBoundingClientRect().left : null,
    метка: (м_.querySelector('.pc-cht') || {}).textContent || '', фон: getComputedStyle(м_.querySelector('.pc-chb')).backgroundColor,
    отметки: window.__ОТМЕТКИ.filter(х => х.p_id === ид).map(х => х.p_state),
    журнал: (window.__ТАБЛИЦЫ.events || []).filter(е => /^review_/.test(е.event_type)).length,
    провСчёт: +(((document.querySelector('#pcTab-c .pc-cnt') || {}).textContent) || 0) }; }"""

# «Отменить»: внутри карточки, поле нажатия, текст целиком, зазор до значка.
ВИД = """(ид) => { const к = document.getElementById('presetChipCard'), м_ = к.querySelector('.pc-chm[data-mid="' + ид + '"]');
  const о = м_ && м_.querySelector('[data-act="ch-flag-undo"]'); if (!о) return ['«Отменить» нет'];
  const н = [], б = о.getBoundingClientRect(), р = к.getBoundingClientRect(), с = getComputedStyle(о, '::before');
  if (б.left < р.left + 4 || б.right > р.right - 4) н.push('«Отменить» у края карточки или за ним');
  // Текст — по прямоугольникам самих букв: scrollWidth у кнопки считает и
  // невидимое поле нажатия, вынесенное за её края.
  const д = document.createRange(); д.selectNodeContents(о);
  if ([...д.getClientRects()].some(х => х.width > 0 && (х.left < б.left - .5 || х.right > б.right + .5))) н.push('«Отменить» обрезано');
  if (о.textContent.trim() !== 'Отменить') н.push('на кнопке не «Отменить»: ' + о.textContent);
  const h = б.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
  if (h < 43.5) н.push('поле нажатия «Отменить» ' + Math.round(h) + ' px');
  const ф = м_.querySelector('[data-act="ch-flag"]').getBoundingClientRect();
  const зазор = Math.max(ф.left - б.right, б.left - ф.right);
  if (зазор < 4) н.push('«Отменить» вплотную к значку: ' + Math.round(зазор) + ' px');
  if (зазор > 26) н.push('«Отменить» далеко от значка: ' + Math.round(зазор) + ' px');
  return н; }"""


def нажать(стр, ид, act="ch-flag"):
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{ид}'] [data-act='{act}']").click()


def прогон(бр, порт, ш, в, полный):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    ч.открыть(стр); стр.wait_for_timeout(500)
    ч.вкладка(стр, "m"); стр.wait_for_timeout(600)

    # ── нажатие: сразу видно, в базу не спешит ──
    до = стр.evaluate(СОСТ, ЧУЖОЕ)
    нажать(стр, ЧУЖОЕ); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ, ЧУЖОЕ)
    if с["нажат"] != "true" or not с["отмена"] or с["метка"] or с["фон"] != до["фон"] or с["провСчёт"] != до["провСчёт"] + 1:
        плохо(f"{н} нажатие на значок: {с} (до {до})")
    if not с["отмена"]:
        плохо(f"{н} у значка нет «Отменить» — дальше проверять нечего"); стр.close(); return
    if с["отменаСлева"]:
        плохо(f"{н} у чужого сообщения «Отменить» слева от значка")
    if abs(с["флаг"] - до["флаг"]) > .5:
        плохо(f"{н} значок чужого сообщения сдвинулся, когда встало «Отменить»: {до['флаг']} → {с['флаг']}")
    for т in стр.evaluate(ВИД, ЧУЖОЕ):
        плохо(f"{н} {т}")
    ч.вёрстка(стр, н, "«Отменить» у чужого сообщения")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-undo-{ш}.png"))
    стр.wait_for_timeout(2200)
    с = стр.evaluate(СОСТ, ЧУЖОЕ)
    if с["отметки"] or с["журнал"]:
        плохо(f"{н} за 2,5 секунды отметка ушла в базу или журнал: {с}")
    # ── «Отменить» ──
    нажать(стр, ЧУЖОЕ, "ch-flag-undo"); стр.wait_for_timeout(3700)
    с = стр.evaluate(СОСТ, ЧУЖОЕ)
    if с["нажат"] != "false" or с["отмена"] or с["отметки"] or с["журнал"] or с["провСчёт"] != до["провСчёт"]:
        плохо(f"{н} после «Отменить»: {с}")
    # ── второе нажатие на значок — та же отмена ──
    нажать(стр, ЧУЖОЕ); стр.wait_for_timeout(400); нажать(стр, ЧУЖОЕ); стр.wait_for_timeout(3500)
    с = стр.evaluate(СОСТ, ЧУЖОЕ)
    if с["нажат"] != "false" or с["отметки"] or с["журнал"]:
        плохо(f"{н} второе нажатие на значок не отменило: {с}")
    # ── без отмены: через 3 секунды — база и журнал; перезагрузка ленты в отсчёте не стирает ──
    нажать(стр, ЧУЖОЕ); стр.wait_for_timeout(500)
    стр.evaluate("() => загрузитьЧат(true, true)"); стр.wait_for_timeout(700)
    с = стр.evaluate(СОСТ, ЧУЖОЕ)
    if с["нажат"] != "true" or not с["отмена"]:
        плохо(f"{н} перезагрузка ленты в отсчёте стёрла отметку: {с}")
    стр.wait_for_timeout(2400)
    с = стр.evaluate(СОСТ, ЧУЖОЕ)
    события = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).filter(е => /^review_/.test(е.event_type)).map(е => е.event_type)")
    if с["отметки"] != ["open"] or с["отмена"] or с["нажат"] != "true" or события != ["review_added"]:
        плохо(f"{н} отметка без отмены: {с}, журнал {события}")
    if not полный:
        if ошибки: плохо(f"{н} ошибки страницы: {ошибки[:3]}")
        стр.close(); return

    # ── своё сообщение: «Отменить» слева, значок на месте ──
    до = стр.evaluate(СОСТ, СВОЁ)
    нажать(стр, СВОЁ); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ, СВОЁ)
    if not с["отмена"] or not с["отменаСлева"] or abs(с["флаг"] - до["флаг"]) > .5:
        плохо(f"{н} своё сообщение: «Отменить» не слева или значок сдвинулся: {до['флаг']} → {с['флаг']}, {с}")
    for т in стр.evaluate(ВИД, СВОЁ):
        плохо(f"{н} своё сообщение: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"chat-undo-mine-{ш}.png"))
    # ── вкладка в фоне — отметка уходит сразу ──
    стр.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      document.dispatchEvent(new Event('visibilitychange')); delete document.hidden; }""")
    стр.wait_for_timeout(400)
    с = стр.evaluate(СОСТ, СВОЁ)
    if с["отметки"] != ["open"]:
        плохо(f"{н} вкладка ушла в фон, а отметка ждёт: {с}")
    # ── «Выполнено» в секунды отмены: сначала open, потом done ──
    нажать(стр, ТРЕТЬЕ); стр.wait_for_timeout(300)
    нажать(стр, ТРЕТЬЕ, "ch-done"); стр.wait_for_timeout(900)
    с = стр.evaluate(СОСТ, ТРЕТЬЕ)
    if с["отметки"] != ["open", "done"]:
        плохо(f"{н} «Выполнено» в секунды отмены: {с['отметки']}")
    стр.wait_for_timeout(3200)
    if стр.evaluate(СОСТ, ТРЕТЬЕ)["отметки"] != ["open", "done"]:
        плохо(f"{н} после «Выполнено» отложенная отметка ушла ещё раз")
    # ── касание, остановившее ленту ──
    стр.evaluate("() => { const л = document.getElementById('pcChatList'); л.style.maxHeight = '160px'; заполнитьКарточкуЗначка(); }")
    стр.wait_for_timeout(300)
    ид = "44444444-4444-4444-8444-444444444444"
    до = стр.evaluate(СОСТ, ид)
    стр.evaluate("() => { const л = document.getElementById('pcChatList'); л.scrollTop = Math.max(0, л.scrollTop - 1); л.dispatchEvent(new Event('scroll')); }")
    нажать(стр, ид); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ, ид)
    if с["нажат"] != до["нажат"] or с["отмена"]:
        плохо(f"{н} касание по едущей ленте поставило отметку: {с}")
    стр.wait_for_timeout(400)
    нажать(стр, ид); стр.wait_for_timeout(300)
    if стр.evaluate(СОСТ, ид)["нажат"] != "true":
        плохо(f"{н} после остановленной ленты обычное нажатие не сработало")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 390, 844, True)
                прогон(бр, порт, 1440, 900, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Отразить в правках» — значок сразу, «Отменить» 3 секунды рядом, без подписи и заливки; отменённое не доходит "
          "ни до базы, ни до журнала, второе нажатие — та же отмена; без отмены один запрос и «добавлена в проверку»; "
          "перезагрузка ленты отметку не стирает, фон вкладки отправляет сразу, «Выполнено» идёт после неё; касание по едущей "
          "ленте не считается; значок не сдвигается, «Отменить» с нужной стороны, поле 44 px; 390 и 1440.")


if __name__ == "__main__":
    главная()
