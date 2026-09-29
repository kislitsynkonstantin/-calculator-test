#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пока журнал или сводка мини-окна грузятся, бежит полоска загрузки.

Константин 30.09.2026, снимком с телефона: «тут пока грузится журнал, пустая
область и кажется фраза сдвинута. Поставь какую-нибудь анимацию на загрузку».
Список стоял пустым с мелкой строкой, а в плашке «Открыть в журнале действий»
не было числа — ссылка жалась к правому краю, слева пустота.

Проба задерживает ответ базы (`window.__ЗАДЕРЖКА`) и, в настоящих шрифтах,
на 1440, 390 и 320, днём и ночью, держит:
  • во вкладке «Журнал» до ответа — бегущая полоска с подписью посередине
    ленты, а в плашке на месте числа — короткая полоска у левого края;
  • во вкладке «Сводка» до ответа — та же полоска;
  • полоска движется (анимация идёт), а при «Уменьшении движения» стоит;
  • после ответа полосок нет, в плашке число действий.

    python3 check_preset_card_loading.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card_fonts as ш
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS", "/tmp"))

ПОСЕВ = """(код) => { const т = window.__ТАБЛИЦЫ, я = _sbUser.id;
  т.events = [];
  for (let и = 0; и < 12; и++) т.events.push({ id: 'з' + и, user_id: я, event_type: 'print', created_at: new Date(Date.now() - и * 3600000).toISOString(),
    total_price: 3200000, details: { presetCode: код, preset: 'Проба', rows: [] } });
  _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 };
  _сводкаПресета = { код: '', данные: null, ошибка: '', грузится: false, когда: 0 };
  window.__ЗАДЕРЖКА = 2500; }"""

МЕРА = """(в) => { const к = document.getElementById('presetChipCard'), п = к.querySelector('#pcPane-' + в);
  const пол = п && п.querySelector('.pc-wait .bm-load'), бег = пол && пол.querySelector('i');
  const пл = п && п.querySelector('.pc-lg-plate'), лд = пл && пл.querySelector('.pc-lg-ld');
  const r = пл && пл.getBoundingClientRect(), рл = лд && лд.getBoundingClientRect();
  return { полоска: !!пол && пол.getBoundingClientRect().width > 0, анимация: бег ? getComputedStyle(бег).animationName : '',
    подпись: п ? п.innerText.replace(/\\s+/g, ' ').trim() : '',
    вПлашке: !!лд && рл.width > 0, место: пл ? Math.round(r.width - 24 - пл.querySelector('.pc-lg-pl').getBoundingClientRect().width - 10) : null, слева: лд ? Math.round(рл.left - r.left) : null, внутри: лд ? (рл.right <= r.right && рл.top >= r.top && рл.bottom <= r.bottom) : null,
    анимПлашки: лд ? getComputedStyle(лд.querySelector('i')).animationName : '',
    число: пл ? ((пл.querySelector('.pc-lg-pn') || {}).textContent || '').trim() : '' }; }"""


def прогон(бр, порт, шир, выс, ночь, тихо=False):
    н = f"[{шир}{' ночь' if ночь else ''}{' без движения' if тихо else ''}]"
    стр, ошибки = ш.начать(бр, порт, шир, выс, ночь)
    if тихо:
        стр.emulate_media(reduced_motion="reduce")
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        НАХОДКИ.append(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ПОСЕВ, код)
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        стр.locator("#presetChip .pc-body").click()
    стр.wait_for_timeout(300)
    for в, имя in (("l", "Журнал"), ("s", "Сводка")):
        if not стр.locator(f"#pcTab-{в}").count():
            НАХОДКИ.append(f"{н} нет вкладки «{имя}»"); continue
        стр.evaluate("() => { _журналПресета = { код: '', события: null, ошибка: '', грузится: false, когда: 0 }; _сводкаПресета = { код: '', данные: null, ошибка: '', грузится: false, когда: 0 }; }")
        стр.locator(f"#pcTab-{в}").click(); стр.wait_for_timeout(250)
        с = стр.evaluate(МЕРА, в)
        if not с["полоска"] or "загружается" not in с["подпись"]:
            НАХОДКИ.append(f"{н} «{имя}» до ответа базы: нет полоски загрузки с подписью («{с['подпись'][:60]}»)")
        ждём = "none" if тихо else "bmLoad"
        if с["полоска"] and с["анимация"] != ждём:
            НАХОДКИ.append(f"{н} «{имя}»: анимация полоски «{с['анимация']}», ждали «{ждём}»")
        if в == "l":
            if not с["вПлашке"] or not с["внутри"] or (с["слева"] or 99) > 16:
                НАХОДКИ.append(f"{н} плашка до ответа: полоски на месте числа нет или она не у левого края ({с})")
            elif с["анимПлашки"] != ждём:
                НАХОДКИ.append(f"{н} плашка: анимация «{с['анимПлашки']}», ждали «{ждём}»")
            if not тихо:
                стр.screenshot(path=str(СНИМКИ / f"loading-{шир}{'-n' if ночь else ''}.png"))
        стр.wait_for_timeout(7000)
        п = стр.evaluate(МЕРА, в)
        if п["полоска"] or п["вПлашке"]:
            НАХОДКИ.append(f"{н} «{имя}» после ответа полоска осталась")
        if в == "l" and "действ" not in п["число"] and шир >= 768:
            НАХОДКИ.append(f"{н} после ответа в плашке нет числа действий («{п['число']}»)")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for шир, выс, ночь, тихо in ((1440, 900, False, False), (390, 844, False, False), (320, 640, False, False), (390, 844, True, False), (390, 844, False, True)):
                прогон(бр, порт, шир, выс, ночь, тихо)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: пока журнал и сводка мини-окна грузятся, бежит полоска загрузки с подписью, в плашке журнала "
          "на месте числа — короткая полоска у левого края; при «Уменьшении движения» полоски стоят; после ответа "
          "их нет — на 1440, 390 и 320, днём и ночью.")


if __name__ == "__main__":
    главная()
