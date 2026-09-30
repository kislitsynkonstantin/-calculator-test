#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок мини-окна: только вопросы проверки — точка вместо числа.

Константин 30.09.2026, двумя снимками (значок «Мой пресет» с числом 2 и
вкладка «Проверка»): «если тут остались только эти пункты [вопросы], то тут
оставляй только точку, как на кнопках сверху, только оранжевую. Таким же
цветом, как плашка с номером».

Проба на 390 и 1440, днём и ночью, подменяет итог проверки и держит:
  • есть замечания — число, как прежде;
  • замечаний нет, вопросы есть — точка 8×8 без текста, цвета числа, внутри
    значка сразу за надписью (зазор 3–8 px), на уровне верха букв (центр выше
    середины надписи), от кромки значка не ближе 4 px — Константин, тем же
    днём, снимком значка: «точку на свёрнутом мини-окне вот так размести»,
    как точку у «Пресетов» в шапке; на кромке она резала обводку;
  • нет ни замечаний, ни вопросов — ничего;
  • у раскрытого мини-окна точка тоже не выглядывает.

    python3 check_badge_dot.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИД = """(итог) => { window.проверкаПоЧекЛисту = () => ({ замечания: итог[0], вопросы: итог[1], адреса: {} });
  обновитьСчётчикПроверки(); const с = document.querySelector('#presetChip .pc-ckn'); if (!с) return null;
  const q = с.getBoundingClientRect(), ст = getComputedStyle(с);
  const з = document.getElementById('presetChip').getBoundingClientRect(), н = document.querySelector('#presetChip .pc-lbl').getBoundingClientRect();
  return { зазор: q.left - н.right, выше: н.top + н.height / 2 - (q.top + q.height / 2), кромка: Math.min(з.right - q.right, q.top - з.top, з.bottom - q.bottom), верхБукв: q.top - н.top,
           точка: с.classList.contains('pc-ckn--dot'), текст: с.textContent, ш: Math.round(q.width), в: Math.round(q.height),
           цх: q.left + q.width / 2, цу: q.top + q.height / 2, фон: ст.backgroundColor, видно: ст.visibility !== 'hidden', внутри: q.right <= innerWidth && q.top >= 0 }; }"""
ЗАМ = [{"раздел": "roof", "т": "x", "стоп": False, "эл": ""}]


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(СоШрифтами(бр), порт, ш, в, ночь)
    стр.evaluate("() => { закрытьКарточкуЗначка && закрытьКарточкуЗначка(); appSettings.showCheckBadge = true; }")
    стр.wait_for_timeout(300)
    число = стр.evaluate(ВИД, [ЗАМ * 2, ["вопрос"]])
    точка = стр.evaluate(ВИД, [[], ["вопрос", "ещё"]])
    if точка:
        стр.evaluate("() => { const з = document.getElementById('presetChip'); з.scrollIntoView(); }")
        q = стр.evaluate("() => { const р = document.getElementById('presetChip').getBoundingClientRect(); return { x: р.x - 14, y: р.y - 14, w: р.width + 28, h: р.height + 28 }; }")
        стр.screenshot(path=str(м.СНИМКИ / f"badge-dot-{ш}{'-ночь' if ночь else ''}.png"), clip={"x": max(0, q["x"]), "y": max(0, q["y"]), "width": q["w"], "height": q["h"]})
    нет = стр.evaluate(ВИД, [[], []])
    if not число or число["точка"] or число["текст"] != "2":
        НАХОДКИ.append(f"{н} при замечаниях не число: {число}")
    if not точка or not точка["точка"] or точка["текст"] or (точка["ш"], точка["в"]) != (8, 8) or not точка["внутри"]:
        НАХОДКИ.append(f"{н} только вопросы — не точка 8×8: {точка}")
    elif число and точка["фон"] != число["фон"]:
        НАХОДКИ.append(f"{н} точка другого цвета, чем число: точка {точка}, число {число}")
    elif not (3 <= точка["зазор"] <= 8) or точка["выше"] < 1 or точка["кромка"] < 4 or точка["верхБукв"] < -4:
        НАХОДКИ.append(f"{н} точка не за надписью на уровне верха букв или у кромки: зазор {точка['зазор']:.1f}, выше середины {точка['выше']:.1f}, "
                       f"до кромки {точка['кромка']:.1f}, от верха надписи {точка['верхБукв']:.1f}")
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
    print("Чисто: при замечаниях на значке число; только вопросы — оранжевая точка 8×8 внутри значка за надписью, "
          "на уровне верха букв, того же цвета; ничего нет — пусто; у раскрытого окна не выглядывает — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
