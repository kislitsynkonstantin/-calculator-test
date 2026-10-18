#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимки и PDF из чата пресета — кнопкой в «Визуализацию и планировку».

Константин 18.10.2026, снимком пустого блока «Визуализация и планировка»:
«Добавь также, чтобы в чат пресета можно было сразу грузить визуализации и
планировку — предлагать всплывающей кнопкой в чате, добавить их сюда».

Проба держит, на заглушке базы и с pdf.js из папки проб:
  • после отправки снимка и PDF над полем чата всплывает «Добавить в
    «Визуализацию и планировку»»; после текста без файлов — нет;
  • нажатие кладёт снимок и разобранный PDF на полотно, кнопка уходит,
    а копией обратно в чат они не идут — они там уже лежат;
  • крестик убирает предложение, полотно не трогая;
  • в пресете, закрытом для правок, предложения нет;
  • вёрстка на 390 и 1440, днём и ночью: кнопка внутри мини-окна, не лежит
    поверх ленты (накрывала кнопки последнего сообщения), не липнет к полю, нарисована не выше 34 px, а нажатие — не меньше 44 px, надпись
    читается (контраст не меньше 4.5).

    python3 check_chat_to_canvas.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from check_chat_files import отдать_pdfjs
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
ОБРАЗЦЫ = ЗДЕСЬ / "образцы_приложения2"
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


ВСПЛЫВАЮЩАЯ = """() => { const в = document.querySelector('#presetChipCard .pc-chvz'); if (!в) return null;
  const к = document.getElementById('presetChipCard').getBoundingClientRect(), r = в.getBoundingClientRect();
  const поле = document.querySelector('#presetChipCard .pc-chin').getBoundingClientRect();
  const над = [...document.querySelectorAll('#pcChatExtra > :not(.pc-chvz)')].map(э => э.getBoundingClientRect()).filter(р => р.height);
  const низ = над.length ? Math.min(...над.map(р => р.top)) : поле.top;
  const кн = в.querySelector('.pc-chvz-go'), кр = кн.getBoundingClientRect(), до = getComputedStyle(кн, '::before');
  const x = в.querySelector('.pc-chvz-x').getBoundingClientRect();
  const свет = с => { const м_ = с.match(/[\\d.]+/g).map(Number).slice(0, 3).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
    return .2126 * м_[0] + .7152 * м_[1] + .0722 * м_[2]; };
  const ст = getComputedStyle(в), а = свет(ст.color), б = свет(ст.backgroundColor);
  const сп = кн.querySelector('span');
  const лента = document.getElementById('pcChatList').getBoundingClientRect();
  return { наЛенте: лента.bottom - r.top, лев: r.left - к.left, прав: к.right - r.right, доПоля: низ - r.bottom, выс: кр.height,
    нажатие: кр.height - 2 * parseFloat(до.top || 0), крестНажатие: x.height + 16,
    контраст: (Math.max(а, б) + .05) / (Math.min(а, б) + .05), обрезано: сп.scrollWidth > сп.clientWidth + 1, текст: в.textContent.trim() }; }"""


def отправить(стр, файлы, текст=""):
    if файлы:
        стр.locator("#pcChatFile").set_input_files(files=файлы); стр.wait_for_timeout(500)
    if текст:
        стр.locator("#pcChatText").fill(текст)
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(600)


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    стр.route("**/cdnjs.cloudflare.com/ajax/libs/pdf.js/**", отдать_pdfjs)
    if not стр.evaluate("() => typeof вВизуализациюИзЧата === 'function'"):
        плохо(f"{н} в калькуляторе нет переноса из чата в «Визуализацию и планировку»"); стр.close(); return
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ; т.preset_messages = т.preset_messages || [];
      window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date().toISOString() : null;
      window.__RPC.preset_chat_read = () => null; }""", код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(800)
    снимок = {"name": "визуализация.jpg", "mimeType": "image/jpeg", "buffer": (ОБРАЗЦЫ / "визуализация.jpg").read_bytes()}
    pdf = {"name": "план_учебный.pdf", "mimeType": "application/pdf", "buffer": (ОБРАЗЦЫ / "план_учебный.pdf").read_bytes()}

    # Текст без файлов — предложения нет.
    отправить(стр, None, "Просто вопрос")
    if стр.locator("#presetChipCard .pc-chvz").count():
        плохо(f"{н} кнопка всплыла после сообщения без файлов")

    # Снимок и PDF — предложение всплывает.
    отправить(стр, [снимок, pdf], "Визуализация и планировка от архитектора")
    вс = стр.evaluate(ВСПЛЫВАЮЩАЯ)
    if not вс:
        плохо(f"{н} после снимка и PDF кнопка «В визуализацию» не всплыла"); стр.close(); return
    if "Визуализацию и планировку" not in вс["текст"]:
        плохо(f"{н} надпись кнопки: {вс['текст']!r}")
    if вс["лев"] < 0 or вс["прав"] < 0:
        плохо(f"{н} кнопка выходит за мини-окно: {вс}")
    if вс["наЛенте"] > 0.5:
        плохо(f"{н} кнопка лежит поверх ленты и накрывает последнее сообщение на {вс['наЛенте']:.0f} px")
    if вс["доПоля"] < 6:
        плохо(f"{н} кнопка липнет к полю сообщения: {вс}")
    if вс["выс"] > 34:
        плохо(f"{н} кнопка раздута: {вс['выс']} px")
    if вс["нажатие"] < 44 or вс["крестНажатие"] < 44:
        плохо(f"{н} нажатие меньше 44 px: {вс}")
    if вс["контраст"] < 4.5:
        плохо(f"{н} надпись кнопки плохо читается: контраст {вс['контраст']:.2f}")
    if вс["обрезано"]:
        плохо(f"{н} надпись кнопки обрезана")
    стр.screenshot(path=str(СНИМКИ / f"chat-canvas-{ш}{'-n' if ночь else ''}.png"))

    было = стр.evaluate("() => ({ полотно: canvasItems.length, копий: window.__ТАБЛИЦЫ.preset_messages.filter(с => /добавлен[ыо]? в «Визуализацию/.test(с.body || '')).length })")
    стр.locator("#presetChipCard [data-act='ch-to-canvas']").click()
    стр.wait_for_timeout(5000)
    стало = стр.evaluate("() => ({ полотно: canvasItems.length, копий: window.__ТАБЛИЦЫ.preset_messages.filter(с => /добавлен[ыо]? в «Визуализацию/.test(с.body || '')).length, виды: [...document.querySelectorAll('#imageCanvas .canvas-img-item')].map(э => э.dataset.kind || '') })")
    if стало["полотно"] < было["полотно"] + 2:
        плохо(f"{н} на полотно легло {стало['полотно'] - было['полотно']} снимков, ждали снимок и планировку из PDF: {стало}")
    if "план" not in стало["виды"]:
        плохо(f"{н} PDF из чата не разобран в планировку: {стало['виды']}")
    if стало["копий"] != было["копий"]:
        плохо(f"{н} добавленное из чата ушло копией обратно в чат")
    if стр.locator("#presetChipCard .pc-chvz").count():
        плохо(f"{н} кнопка осталась после нажатия")

    # Крестик — предложение уходит, полотно не меняется.
    отправить(стр, [снимок])
    до = стр.evaluate("() => canvasItems.length")
    if not стр.locator("#presetChipCard .pc-chvz").count():
        плохо(f"{н} после второго снимка кнопка не всплыла")
    else:
        стр.locator("#presetChipCard [data-act='ch-to-canvas-x']").click(); стр.wait_for_timeout(500)
        if стр.locator("#presetChipCard .pc-chvz").count() or стр.evaluate("() => canvasItems.length") != до:
            плохо(f"{н} крестик не убрал предложение или тронул полотно")

    # Пресет закрыт для правок — предложения нет.
    стр.evaluate("() => { window.__замок = замокПресетаЗакрыт; window.замокПресетаЗакрыт = () => true; }")
    отправить(стр, [снимок])
    if стр.locator("#presetChipCard .pc-chvz").count():
        плохо(f"{н} в закрытом пресете кнопка всплыла")
    стр.evaluate("() => { window.замокПресетаЗакрыт = window.__замок; }")
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
    print("Чисто: после снимков и PDF в чате всплывает «Добавить в «Визуализацию и планировку»», нажатие кладёт их на полотно "
          "без копии обратно в чат, крестик убирает предложение, в закрытом пресете его нет; вёрстка на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
