#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок мини-окна: число — замечания вместе с подсказками, точки нет.

Константин 30.09.2026, снимком значка с точкой и вкладки «Проверка» с
подсказкой «Добавить два вида визуализации и планировку»: «убери точку, эти
рекомендации прибавляй к цифре замечаний». До этого при одних подсказках на
значке стояла оранжевая точка, а число считало только замечания.

Проба на 390 и 1440, днём и ночью, с настоящими шрифтами подменяет итог
проверки и держит:
  • два замечания и одна подсказка — на значке «3», на вкладке «Проверка» «3»;
  • только подсказки — число подсказок, точки нет ни в каком виде;
  • ни замечаний, ни подсказок — на значке пусто;
  • число сказано словами у значка («… пункта по чек-листу»);
  • у раскрытого мини-окна число со значка не выглядывает.

    python3 check_badge_sum.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИД = """(итог) => { window.проверкаПоЧекЛисту = () => ({ замечания: итог[0], вопросы: итог[1], адреса: {} });
  обновитьСчётчикПроверки(); const с = document.querySelector('#presetChip .pc-ckn');
  const т = document.querySelector('#presetChip .pc-body');
  return { есть: !!с, текст: с ? с.textContent : '', точек: document.querySelectorAll('#presetChip .pc-ckn--dot').length
    + [...document.querySelectorAll('#presetChip *')].filter(э => { const r = э.getBoundingClientRect(), ст = getComputedStyle(э);
        return r.width > 0 && r.width <= 10 && Math.abs(r.width - r.height) < .5 && ст.borderRadius === '50%' && !э.textContent.trim(); }).length,
    метка: т ? т.getAttribute('aria-label') : '' }; }"""
ЗАМ = [{"раздел": "roof", "т": "x", "стоп": False, "эл": ""}]


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(СоШрифтами(бр), порт, ш, в, ночь)
    стр.evaluate("() => { закрытьКарточкуЗначка && закрытьКарточкуЗначка(); appSettings.showCheckBadge = true; }")
    стр.wait_for_timeout(300)
    сумма = стр.evaluate(ВИД, [ЗАМ * 2, ["вопрос"]])
    if not сумма["есть"] or сумма["текст"] != "3":
        НАХОДКИ.append(f"{н} два замечания и подсказка — ждали «3» на значке: {сумма}")
    if "3 пункта по чек-листу" not in (сумма["метка"] or ""):
        НАХОДКИ.append(f"{н} число не сказано словами у значка: «{сумма['метка']}»")
    к.открыть(стр); к.вкладка(стр, "c"); стр.wait_for_timeout(300)
    вкл = стр.evaluate("() => { const в = document.querySelector('#pcTab-c .pc-cnt'); return в ? в.textContent.trim() : ''; }")
    if вкл != "3":
        НАХОДКИ.append(f"{н} на вкладке «Проверка» не то же число, что на значке: «{вкл}»")
    видно = стр.evaluate("() => { const с = document.querySelector('#presetChip .pc-ckn'); return !!с && getComputedStyle(с).visibility !== 'hidden'; }")
    if видно:
        НАХОДКИ.append(f"{н} у раскрытого мини-окна число со значка выглядывает")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    только = стр.evaluate(ВИД, [[], ["вопрос", "ещё"]])
    if not только["есть"] or только["текст"] != "2" or только["точек"]:
        НАХОДКИ.append(f"{н} только подсказки — ждали «2» и ни одной точки: {только}")
    if только["есть"]:
        q = стр.evaluate("() => { const р = document.getElementById('presetChip').getBoundingClientRect(); return { x: р.x - 14, y: р.y - 16, w: р.width + 28, h: р.height + 30 }; }")
        стр.screenshot(path=str(м.СНИМКИ / f"badge-sum-{ш}{'-ночь' if ночь else ''}.png"), clip={"x": max(0, q["x"]), "y": max(0, q["y"]), "width": q["w"], "height": q["h"]})
    нет = стр.evaluate(ВИД, [[], []])
    if нет["есть"] or нет["точек"]:
        НАХОДКИ.append(f"{н} без замечаний и подсказок значок не пуст: {нет}")
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
    print("Чисто: на значке одно число — замечания вместе с подсказками, то же на вкладке «Проверка»; при одних "
          "подсказках — их число, точки нет; пусто — пусто; число сказано словами — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
