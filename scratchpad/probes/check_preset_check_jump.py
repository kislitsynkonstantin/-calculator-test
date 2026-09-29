#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замечание проверки ведёт прямо к строке, которую надо отметить.

Константин 29.09.2026, двумя снимками: замечание «Добавить сборку премиальной
парной» во вкладке «Проверка» мини-окна вело к шапке раздела «Парное
отделение», а опцию приходилось искать в списке глазами — «тут должно
перекидывать прямо на опцию, чтобы просто нажать».

Проба на 390 и 1440 держит:
  • у замечаний, за которыми стоит конкретная строка, в кнопке есть её адрес:
    пробное бурение → «Пробное бурение», водосток → опция водосточной
    системы, Rockwool в своём примечании → это примечание;
  • нажатие закрывает мини-окно, строка встаёт целиком между липкой шапкой и
    полоской итога и подсвечивается;
  • строки нет (адрес пустой или неверный) — переход, как прежде, к шапке
    раздела.

    python3 check_preset_check_jump.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ГДЕ = """(ид) => { const э = document.getElementById(ид); if (!э) return null; const r = э.getBoundingClientRect();
  const верх = getStickyOffset(); let низ = innerHeight;
  if (document.body.classList.contains('total-strip-on')) низ -= parseFloat(getComputedStyle(document.body).getPropertyValue('--strip-h')) || 68;
  return { верх: Math.round(r.top), низ: Math.round(r.bottom), окноВерх: Math.round(верх), окноНиз: Math.round(низ),
    подсветка: э.classList.contains('pc-flash-row'), карточка: document.getElementById('presetChipCard').classList.contains('show') }; }"""


def нажать(стр, текст):
    к.открыть(стр); стр.wait_for_timeout(250)
    стр.evaluate("() => { _пкВкладка = 'c'; заполнитьКарточкуЗначка(); }"); стр.wait_for_timeout(250)
    кн = стр.locator("#presetChipCard [data-act='ck']", has_text=текст)
    if not кн.count():
        return "нет:" + стр.evaluate("() => { const к = document.getElementById('presetChipCard'); return (к.classList.contains('show') ? 'открыто ' : 'закрыто ') + к.innerText.replace(/\\s+/g, ' ').slice(0, 160); }")
    ид = кн.first.get_attribute("data-el")
    кн.first.click(); стр.wait_for_timeout(1100)
    return ид


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    # Замечания: без пробного бурения, с обшивкой фасада без водостока, Rockwool в своём примечании.
    стр.evaluate("""() => { if (checkedOptions.f3) toggleOpt('f3');
      const о = (OPTIONS || []).find(o => o.section === 'exterior' && /^Обшивка стен/i.test(o.name || '') && !checkedOptions[o.id]); if (о) toggleOpt(о.id);
      toggleAddNoteForm('insulation'); const ф = document.getElementById('addNoteForm_insulation'); if (ф) { ф.querySelector('textarea').value = 'Утеплитель Rockwool Light Batts'; confirmAddNote('insulation'); }
      calc(); }""")
    стр.wait_for_timeout(600)
    for текст, ждём in (("пробное бурение", "lbl_f3"), ("водосточную", "lbl_"), ("Rockwool", "note_")):
        ид = нажать(стр, текст)
        if ид is not None and ид.startswith("нет:"):
            НАХОДКИ.append(f"{н} нет замечания «{текст}» — переход к строке не проверен: {ид[4:]}"); continue
        if not ид or not ид.startswith(ждём):
            НАХОДКИ.append(f"{н} замечание «{текст}» ведёт не к строке: адрес «{ид}»"); continue
        г = стр.evaluate(ГДЕ, ид)
        if г is None:
            НАХОДКИ.append(f"{н} «{текст}»: строки «{ид}» на листе нет"); continue
        if г["карточка"]:
            НАХОДКИ.append(f"{н} «{текст}»: мини-окно после перехода осталось открытым")
        if г["верх"] < г["окноВерх"] - 1 or г["низ"] > г["окноНиз"] + 1:
            НАХОДКИ.append(f"{н} «{текст}»: строка не встала в видимую часть — {г}")
        if not г["подсветка"]:
            НАХОДКИ.append(f"{н} «{текст}»: строка не подсвечена")
        if текст == "пробное бурение":
            стр.screenshot(path=str(м.СНИМКИ / f"check-jump-{ш}.png"))
    # Строки нет — к шапке раздела.
    стр.evaluate("() => { window.scrollTo(0, 0); кРазделуИзПроверки('roof', 'lbl_нет_такой'); }"); стр.wait_for_timeout(1100)
    шапка = стр.evaluate("""() => { const э = document.getElementById('sec_opts_roof'); const ш = э && э.closest('.card') && э.closest('.card').querySelector('.section-header');
      return ш ? { вспышка: ш.classList.contains('pc-flash'), верх: Math.round(ш.getBoundingClientRect().top), шапка: Math.round(getStickyOffset()) } : null; }""")
    if not шапка or not шапка["вспышка"] or abs(шапка["верх"] - шапка["шапка"]) > 40:
        НАХОДКИ.append(f"{н} без строки переход не пришёл к шапке раздела: {шапка}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                прогон(бр, порт, ш, в)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: замечание ведёт прямо к строке — опции или своему примечанию, — мини-окно закрывается, строка встаёт "
          "между шапкой и полоской итога и подсвечивается; без строки — к шапке раздела, как прежде — на 390 и 1440.")


if __name__ == "__main__":
    главная()
