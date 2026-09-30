#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок мини-окна: только вопросы проверки — точка вместо числа.

Константин 30.09.2026, двумя снимками (значок «Мой пресет» с числом 2 и
вкладка «Проверка»): «если тут остались только эти пункты [вопросы], то тут
оставляй только точку, как на кнопках сверху, только оранжевую. Таким же
цветом, как плашка с номером».

Проба на 390 и 1440, днём и ночью, подменяет итог проверки и держит:
  • есть замечания — число, как прежде;
  • замечаний нет, вопросы есть — точка 8×8 без текста, цвета числа, центр на
    том же месте, что у числа (±2 px), в пределах экрана;
  • нет ни замечаний, ни вопросов — ничего;
  • у раскрытого мини-окна точка тоже не выглядывает.

    python3 check_badge_dot.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИД = """(итог) => { window.проверкаПоЧекЛисту = () => ({ замечания: итог[0], вопросы: итог[1], адреса: {} });
  обновитьСчётчикПроверки(); const с = document.querySelector('#presetChip .pc-ckn'); if (!с) return null;
  const q = с.getBoundingClientRect(), ст = getComputedStyle(с);
  return { точка: с.classList.contains('pc-ckn--dot'), текст: с.textContent, ш: Math.round(q.width), в: Math.round(q.height),
           цх: q.left + q.width / 2, цу: q.top + q.height / 2, фон: ст.backgroundColor, видно: ст.visibility !== 'hidden', внутри: q.right <= innerWidth && q.top >= 0 }; }"""
ЗАМ = [{"раздел": "roof", "т": "x", "стоп": False, "эл": ""}]


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(бр, порт, ш, в, ночь)
    стр.evaluate("() => { закрытьКарточкуЗначка && закрытьКарточкуЗначка(); appSettings.showCheckBadge = true; }")
    стр.wait_for_timeout(300)
    число = стр.evaluate(ВИД, [ЗАМ * 2, ["вопрос"]])
    точка = стр.evaluate(ВИД, [[], ["вопрос", "ещё"]])
    нет = стр.evaluate(ВИД, [[], []])
    if not число or число["точка"] or число["текст"] != "2":
        НАХОДКИ.append(f"{н} при замечаниях не число: {число}")
    if not точка or not точка["точка"] or точка["текст"] or (точка["ш"], точка["в"]) != (8, 8) or not точка["внутри"]:
        НАХОДКИ.append(f"{н} только вопросы — не точка 8×8: {точка}")
    elif число and (точка["фон"] != число["фон"] or abs(точка["цх"] - число["цх"]) > 2.5 or abs(точка["цу"] - число["цу"]) > 2.5):
        НАХОДКИ.append(f"{н} точка другого цвета или не на месте числа: точка {точка}, число {число}")
    if нет is not None:
        НАХОДКИ.append(f"{н} без замечаний и вопросов значок не пуст: {нет}")
    стр.evaluate(ВИД, [[], ["вопрос"]])
    к.открыть(стр); стр.wait_for_timeout(300)
    видно = стр.evaluate("() => { const с = document.querySelector('#presetChip .pc-ckn'); return !!с && getComputedStyle(с).visibility !== 'hidden'; }")
    if видно:
        НАХОДКИ.append(f"{н} у раскрытого мини-окна точка выглядывает")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                for ночь in (False, True):
                    прогон(бр, порт, ш, в, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: при замечаниях на значке число; только вопросы — оранжевая точка 8×8 на месте числа, того же "
          "цвета; ничего нет — пусто; у раскрытого окна не выглядывает — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
