#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мини-окно не прокручивается вбок.

Константин 29.09.2026, двумя снимками вкладки «Журнал» на телефоне: «внутри
окна журнал гуляет, когда двигаю пальцем влево/вправо». Поле нажатия птички
раскрытия (невидимое `::before`) выходило за правый край ленты на 4 px, лента
получала прокрутку вбок, а на iPhone упругая прокрутка раскачивала её гораздо
шире этих четырёх пикселей.

Проба на 320, 390 и 1440 px для каждой вкладки мини-окна — «Пресет»,
«Журнал» (свёрнутые строки и раскрытая), «Проверка» — держит:
  • ни одна прокручиваемая область окна не шире самой себя: ни видимый
    элемент, ни поле нажатия не выходят за её правый и левый край;
  • у прокручиваемых областей прокрутка вбок запрещена: следующий такой
    выступ не превратится в качание ленты;
  • поле нажатия птички, ужатое справа, по-прежнему не меньше 44 px.

    python3 check_preset_card_sideways.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ЛЕНТА = """() => { const о = пресетКарточки(); const д = rows => ({ obj: 'Каркас', rows, sum: '', presetCode: о.код });
  const s = [], я = _sbUser && _sbUser.id;
  for (let i = 0; i < 6; i++) s.push({ id: 'e' + i, created_at: new Date(Date.now() - 86400000 - i * 600000).toISOString(),
    event_type: i % 3 === 2 ? 'print' : 'tech_changed', user_id: я, project_name: 'Проба',
    details: д([{ k: 'Технология', a: 'Каркас', b: 'Клеёный брус' }, { k: 'Итог', a: '3 086 292 ₽', b: '0 ₽' }]) });
  s.push({ id: 'd1', created_at: new Date(Date.now() - 90000000).toISOString(), event_type: 'discount_until_changed', user_id: я,
    project_name: 'Проба', details: д([{ k: 'Действительна до', a: 'без срока', b: '07.10.2026' }]) });
  _журналПресета = { код: о.код, события: s, ошибка: '', грузится: false, когда: Date.now() }; }"""

ВБОК = """() => { const н = [];
  document.querySelectorAll('#presetChipCard .pc-pane.on, #presetChipCard .pc-pane.on .pc-lg-sc').forEach(sc => {
    const cs = getComputedStyle(sc); if (!/auto|scroll/.test(cs.overflowY)) return;
    const имя = sc.className.split(' ')[0];
    if (cs.overflowX !== 'hidden') н.push(имя + ': прокрутка вбок не запрещена (' + cs.overflowX + ')');
    if (sc.scrollWidth > sc.clientWidth + .5) н.push(имя + ': содержимое шире области на ' + (sc.scrollWidth - sc.clientWidth) + ' px');
    const r = sc.getBoundingClientRect(), L = r.left, R = r.left + sc.clientWidth;
    sc.querySelectorAll('*').forEach(e => { const b = e.getBoundingClientRect(); if (!b.width) return;
      if (b.right > R + .5 || b.left < L - .5) н.push(имя + ': «' + (e.className || e.tagName) + '» за краем ' + Math.round(Math.max(b.right - R, L - b.left)) + ' px');
      const п = getComputedStyle(e, '::before');
      if (п.content !== 'none' && п.position === 'absolute') {
        const пр = b.right - (parseFloat(п.right) || 0), пл = b.left + (parseFloat(п.left) || 0);
        if (пр > R + .5 || пл < L - .5) н.push(имя + ': поле нажатия «' + e.className + '» за краем ' + Math.round(Math.max(пр - R, L - пл)) + ' px');
      } });
  });
  document.querySelectorAll('#presetChipCard .pc-lg-chev').forEach(e => { const b = e.getBoundingClientRect(), п = getComputedStyle(e, '::before');
    const w = b.width - (parseFloat(п.left) || 0) - (parseFloat(п.right) || 0), h = b.height - (parseFloat(п.top) || 0) - (parseFloat(п.bottom) || 0);
    if (Math.min(w, h) < 43.5) н.push('поле нажатия птички ' + Math.round(w) + '×' + Math.round(h) + ' — меньше 44'); });
  return [...new Set(н)]; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    if not стр.evaluate("() => activePresetId"):
        НАХОДКИ.append(f"{н} пресет не сохранился"); стр.close(); return
    к.открыть(стр); стр.wait_for_timeout(300)
    стр.evaluate(ЛЕНТА)
    for вкладка, имя in (("p", "Пресет"), ("l", "Журнал"), ("c", "Проверка")):
        стр.evaluate("(в) => { _пкВкладка = в; заполнитьКарточкуЗначка(); }", вкладка); стр.wait_for_timeout(300)
        for х in стр.evaluate(ВБОК):
            НАХОДКИ.append(f"{н} «{имя}»: {х}")
        if вкладка == "l":
            стрелки = стр.locator("#presetChipCard .pc-lg-chev")
            if not стрелки.count():
                НАХОДКИ.append(f"{н} в журнале нет строк с птичкой — раскрытую строку не проверить")
            else:
                стрелки.nth(min(2, стрелки.count() - 1)).click(); стр.wait_for_timeout(300)
                for х in стр.evaluate(ВБОК):
                    НАХОДКИ.append(f"{н} «Журнал», строка раскрыта: {х}")
                стр.screenshot(path=str(м.СНИМКИ / f"card-sideways-{ш}.png"))
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((320, 700), (390, 844), (1440, 900)):
                прогон(бр, порт, ш, в)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in sorted(set(НАХОДКИ)):
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: во вкладках «Пресет», «Журнал» (и с раскрытой строкой) и «Проверка» ничто, включая поля нажатия, "
          "не выходит за край прокручиваемой области, прокрутка вбок запрещена — на 320, 390 и 1440.")


if __name__ == "__main__":
    главная()
