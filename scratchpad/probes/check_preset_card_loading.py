#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пока журнал или сводка мини-окна грузятся, бежит полоска загрузки.

(21) Константин 30.09.2026 выбрал вариант 03 макета plate-loading-v1 и
попросил начинать с середины: «давай 3 вариант… надпись „В журнал действий“
сначала по центру поставить». Полоски в плашке больше нет — пока грузится,
ссылка посередине и у неё покачивается стрелка; пришёл список — ссылка едет
вправо, число проявляется слева.

Константин 30.09.2026, снимком с телефона: «тут пока грузится журнал, пустая
область и кажется фраза сдвинута. Поставь какую-нибудь анимацию на загрузку».
Список стоял пустым с мелкой строкой, а в плашке «Открыть в журнале действий»
не было числа — ссылка жалась к правому краю, слева пустота.

Проба задерживает ответ базы (`window.__ЗАДЕРЖКА`) и, в настоящих шрифтах,
на 1440, 390 и 320, днём и ночью, держит:
  • во вкладке «Журнал» до ответа — бегущая полоска с подписью посередине
    ленты, а в плашке полоски нет: ссылка стоит посередине, стрелка покачивается;
  • список пришёл — ссылка едет из середины на место справа (в первый миг она
    ещё сдвинута), число проявляется; при «Уменьшении движения» — без сдвига;
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
  // Функция базы preset_events в заглушке отвечает мгновенно, а имена авторов
  // после подгрузки при открытии (48) уже известны — без задержки и на ней
  // момента «до ответа» не было бы вовсе.
  if (!window.__событияБезЗадержки) window.__событияБезЗадержки = window.__RPC.preset_events;
  window.__RPC.preset_events = (а) => new Promise(r => setTimeout(() => r(window.__событияБезЗадержки(а)), window.__ЗАДЕРЖКА || 0));
  window.__ЗАДЕРЖКА = 2500; }"""

МЕРА = """(в) => { const к = document.getElementById('presetChipCard'), п = к.querySelector('#pcPane-' + в);
  const пол = п && п.querySelector('.pc-wait .bm-load'), бег = пол && пол.querySelector('i');
  const пл = п && п.querySelector('.pc-lg-plate'), лд = пл && пл.querySelector('.bm-load');
  const r = пл && пл.getBoundingClientRect(), сс = пл && пл.querySelector('.pc-lg-pl'), рс = сс && сс.getBoundingClientRect(), ст = пл && пл.querySelector('.pc-lg-ar');
  return { полоска: !!пол && пол.getBoundingClientRect().width > 0, анимация: бег ? getComputedStyle(бег).animationName : '',
    подпись: п ? п.innerText.replace(/\\s+/g, ' ').trim() : '',
    вПлашке: !!лд, середина: рс ? Math.round((рс.left + рс.right) / 2 - (r.left + r.right) / 2) : null, справа: рс ? Math.round(r.right - рс.right) : null,
    анимСтрелки: ст ? getComputedStyle(ст).animationName : '',
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
            if с["вПлашке"] or с["середина"] is None or abs(с["середина"]) > 2:
                НАХОДКИ.append(f"{н} плашка до ответа: полоска в плашке или ссылка не посередине ({с})")
            if с["анимСтрелки"] != ("none" if тихо else "pcArBreath"):
                НАХОДКИ.append(f"{н} плашка до ответа: стрелка «{с['анимСтрелки']}»")
            if not тихо:
                стр.screenshot(path=str(СНИМКИ / f"loading-{шир}{'-n' if ночь else ''}.png"))
            # Первый кадр после ответа: ссылка ещё сдвинута к середине и едет.
            стр.evaluate("""() => { window.__сдвиг = null; const к = document.getElementById('presetChipCard');
              const н = new MutationObserver(() => { const с = к.querySelector('.pc-lg-plate:not(.pc-lg-wait) .pc-lg-pl'); if (!с || window.__сдвиг !== null) return;
                const m = getComputedStyle(с).transform; window.__сдвиг = m === 'none' ? 0 : Math.round(new DOMMatrix(m).m41); н.disconnect(); });
              н.observe(к, { childList: true, subtree: true }); }""")
        стр.wait_for_timeout(7000)
        п = стр.evaluate(МЕРА, в)
        if п["полоска"] or п["вПлашке"]:
            НАХОДКИ.append(f"{н} «{имя}» после ответа полоска осталась")
        if в == "l":
            if "действ" not in п["число"] or (п["справа"] or 99) > 14:
                НАХОДКИ.append(f"{н} после ответа: число «{п['число']}», ссылка от правого края {п['справа']} px")
            сдвиг = стр.evaluate("() => window.__сдвиг")
            if тихо and сдвиг not in (0, None):
                НАХОДКИ.append(f"{н} при «Уменьшении движения» ссылка всё же поехала: {сдвиг} px")
            if not тихо and (сдвиг is None or сдвиг > -20):
                НАХОДКИ.append(f"{н} ссылка не поехала из середины: в первый кадр сдвиг {сдвиг} px")
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
    print("Чисто: пока журнал и сводка мини-окна грузятся, бежит полоска загрузки с подписью; в плашке журнала "
          "полоски нет — ссылка посередине, стрелка покачивается, а после ответа ссылка едет вправо и появляется число; "
          "при «Уменьшении движения» всё стоит — на 1440, 390 и 320, днём и ночью.")


if __name__ == "__main__":
    главная()
