#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка: вопросы по нажатию ведут к месту, которого касаются.

Константин 30.09.2026, снимком вкладки «Проверка» с вопросами «Тип отопления
не указан» и «Окна Blitz 60…»: «вот эти примечания по нажатию чтобы тоже
перекидывало на раздел, к которому они относятся».

Проба на 390 и 1440 ставит расчёт, в котором стоят все пять вопросов, и держит:
  • каждый вопрос — кнопка со стрелкой, а не простая плашка; текст и стрелка
    не вылезают за карточку, высота нажатия не меньше 32 px;
  • нажатие закрывает карточку и ведёт:
      визуализация — к блоку «Визуализация и планировка», заливкой его заголовка;
      скидка за наличные — к отметке «за наличные», плашкой вокруг;
      тип отопления — к шапке раздела «Инженерные коммуникации»;
      Blitz 60 — к строке окон Blitz 60 (первой отмеченной);
      котёл — к строке котла;
    место стоит на экране и подсвечено.

    python3 check_check_questions.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
# (начало вопроса, как проверить место: ('эл', id, класс) или ('раздел', ключ))
ВОПРОСЫ = [
    ("Добавить два вида визуализации", ("сел", "#imageCanvasCard .card-title", "pc-flash-row")),
    ("Скидка за наличные", ("эл", "cashDiscountLabel", "pc-flash-box")),
    ("Тип отопления", ("раздел", "engineering")),
    ("Окна Blitz 60", ("текст", "blitz\\s*60", "pc-flash-row")),
    ("Котёл в расчёте", ("эл", "lbl_custom_вп2", "pc-flash-row")),
]
ВИД = """() => { const п = document.getElementById('pcPane-c'); if (!п) return null; const r = document.getElementById('presetChipCard').getBoundingClientRect();
  return [...п.querySelectorAll('.pc-q')].map(э => { const q = э.getBoundingClientRect(), с = э.querySelector('.pc-ck-go');
    const вылез = [э, ...э.querySelectorAll('*')].some(х => { const w = х.getBoundingClientRect(); return w.width && (w.right > r.right + .5 || w.left < r.left - .5); });
    return { т: э.textContent.trim(), кнопка: э.tagName === 'BUTTON', стрелка: !!с, выс: Math.round(q.height), вылез }; }); }"""
МЕСТО = """([вид, ид, класс]) => {
  let э = null;
  if (вид === 'эл') э = document.getElementById(ид);
  else if (вид === 'сел') э = document.querySelector(ид);
  else if (вид === 'текст') э = [...document.querySelectorAll('.opt-item.pc-flash-row')].find(х => new RegExp(ид, 'i').test(х.textContent)) || null;
  else { const о = document.getElementById('sec_opts_' + ид); э = о && о.closest('.card') && о.closest('.card').querySelector('.section-header'); }
  if (!э) return null;
  const q = э.getBoundingClientRect(), стр = document.getElementById('totalStrip');
  const низ = document.body.classList.contains('total-strip-on') && стр ? стр.getBoundingClientRect().top : innerHeight;
  return { видно: q.top >= 0 && q.top < низ && q.height > 0, вспышка: вид !== 'раздел' ? э.classList.contains(класс) : э.classList.contains('pc-flash'),
           карточка: document.getElementById('presetChipCard').classList.contains('show') }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.evaluate("""() => { const д = (р, ид, имя) => { customOptions[р] = customOptions[р] || []; customOptions[р].push({ id: ид, name: имя, price: 1000, checked: true }); highlightedOpts.add('custom_' + ид); };
      д('windows', 'вп1', 'Окна ПВХ Blitz 60, белые'); д('engineering', 'вп2', 'Газовый котёл с монтажом');
      if (typeof canvasItems !== 'undefined') canvasItems.length = 0;
      const н = document.getElementById('cashDiscountCheck'); if (н) н.checked = false;
      renderOptionSections(); calc(); }""")
    стр.wait_for_timeout(500)
    к.открыть(стр); к.вкладка(стр, "c"); стр.wait_for_timeout(400)
    вид = стр.evaluate(ВИД) or []
    стр.screenshot(path=str(м.СНИМКИ / f"check-questions-{ш}.png"))
    for начало, место in ВОПРОСЫ:
        в_ = next((х for х in вид if х["т"].startswith(начало)), None)
        if not в_:
            НАХОДКИ.append(f"{н} нет вопроса «{начало}»: {[х['т'][:30] for х in вид]}"); continue
        if not в_["кнопка"] or not в_["стрелка"] or в_["выс"] < 32 or в_["вылез"]:
            НАХОДКИ.append(f"{н} «{начало}»: {в_}")
    for i, (начало, место) in enumerate(ВОПРОСЫ):
        к.открыть(стр); к.вкладка(стр, "c"); стр.wait_for_timeout(400)
        кн = стр.locator("#pcPane-c .pc-q", has_text=начало).first
        if not кн.count():
            continue
        кн.click(); стр.wait_for_timeout(1300)
        р = стр.evaluate(МЕСТО, [место[0], место[1], место[2] if len(место) > 2 else ""])
        if not р or not р["видно"] or not р["вспышка"] or р["карточка"]:
            НАХОДКИ.append(f"{н} «{начало}» не привёл к месту {место}: {р}")
        if i == 1:
            стр.screenshot(path=str(м.СНИМКИ / f"check-questions-cash-{ш}.png"))
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 390, 844)
            прогон(бр, порт, 1440, 900)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: все пять вопросов проверки — кнопки со стрелкой в пределах карточки; нажатие закрывает карточку и "
          "ведёт к блоку визуализации, отметке «за наличные», разделу инженерки, строке окон Blitz 60 и строке котла, "
          "подсвечивая место, — на 390 и 1440.")


if __name__ == "__main__":
    главная()
