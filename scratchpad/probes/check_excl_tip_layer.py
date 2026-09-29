#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подсказка «Недоступно: …» — под всплывающими окнами, а не над ними.

Константин 29.09.2026, двумя снимками с телефона: подсказка у закрытой опции
легла поверх боковой панели «Спецификация» и поверх окна уголка. «Сообщение по
недоступным опциям перекрывает всплывающие окна. Окна должны быть сверху».

Проба на 390 и 1440, днём и ночью, держит:
  • там, где подсказка и окно уголка стоят в одном месте, сверху окно;
  • так же с боковой панелью «Спецификация»;
  • над страницей подсказка по-прежнему видна;
  • строка сразу под липкой шапкой: подсказка уходит под строку, а не под
    шапку — шапка теперь выше неё.

    python3 check_excl_tip_layer.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ПОДГОТОВКА = """async (ночь) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle('blank', false); document.body.classList.toggle('dark', ночь);
  selectProjectOption(0); await ждать(900);
  const строки = [...document.querySelectorAll('.opt-item[id^="lbl_"]')].filter(э => э.offsetParent && !э.classList.contains('active'));
  const а = строки[2].id.slice(4), б2 = строки[10].id.slice(4);
  MUTUAL_EXCLUSIONS.length = 0; MUTUAL_EXCLUSIONS.push({ triggers: [а], excludes: [б2] });
  checkedOptions[а] = true; applyExclusions(); await ждать(200);
  window.__строка = document.getElementById('lbl_' + б2);
  return !!window.__строка && window.__строка.dataset.blocked === '1';
}"""

# Сверху ли окно там, где под ним лежит подсказка: подсказку ставим прямо в
# середину окна (она в координатах страницы) и спрашиваем, чей это пиксель.
СВЕРХУ = """(окно) => {
  const tip = document.getElementById('exclTooltip'), о = document.querySelector(окно);
  const с = window.__строка;
  показатьЗапрет(с, с.dataset.blockedText, false);
  const r = о.getBoundingClientRect();
  tip.style.left = Math.round(r.left + 10 + scrollX) + 'px'; tip.style.top = Math.round(r.top + r.height / 2 + scrollY) + 'px';
  const t = tip.getBoundingClientRect();
  const x = t.left + Math.min(20, t.width / 2), y = t.top + t.height / 2;
  const э = document.elementFromPoint(x, y);
  return { виднаПодсказка: tip.style.display === 'block', окно: !!э && !!э.closest(окно), подсказка: !!э && э.id === 'exclTooltip', размер: [Math.round(r.width), Math.round(r.height)] };
}"""


def прогон(бр, порт, ш, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр = бр.new_page(viewport={"width": ш, "height": 844 if ш < 900 else 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    if not стр.evaluate(ПОДГОТОВКА, ночь):
        НАХОДКИ.append(f"{н} не удалось закрыть опцию для подсказки"); стр.close(); return
    # над страницей подсказка видна
    стр.evaluate("() => { window.__строка.scrollIntoView({ block: 'center' }); }"); стр.wait_for_timeout(200)
    в = стр.evaluate("""() => { const с = window.__строка; показатьЗапрет(с, с.dataset.blockedText, false);
      const t = document.getElementById('exclTooltip').getBoundingClientRect();
      const э = document.elementFromPoint(t.left + 10, t.top + t.height / 2); return !!э && э.id === 'exclTooltip'; }""")
    if not в:
        НАХОДКИ.append(f"{н} над страницей подсказку что-то закрывает")
    # окно уголка
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(400)
    р = стр.evaluate(СВЕРХУ, "#presetChipCard")
    if not р["виднаПодсказка"] or not р["окно"]:
        НАХОДКИ.append(f"{н} подсказка легла поверх окна уголка: {р}")
    стр.screenshot(path=str(м.СНИМКИ / f"tip-layer-card-{ш}{'-n' if ночь else ''}.png"))
    стр.evaluate("() => { закрытьКарточкуЗначка(); спрятатьЗапрет(); }")
    # боковая панель «Спецификация»
    стр.evaluate("() => { try { openSideNav(); } catch (e) {} }"); стр.wait_for_timeout(700)
    р = стр.evaluate(СВЕРХУ, "#sideNav")
    if not р["окно"]:
        НАХОДКИ.append(f"{н} подсказка легла поверх боковой панели: {р}")
    стр.screenshot(path=str(м.СНИМКИ / f"tip-layer-nav-{ш}{'-n' if ночь else ''}.png"))
    стр.evaluate("() => { спрятатьЗапрет(); try { closeSideNav(); } catch (e) {} }"); стр.wait_for_timeout(500)
    # строка сразу под липкой шапкой: подсказка уходит под строку
    ш_ = стр.evaluate("""async () => { const с = window.__строка;
      const y = с.getBoundingClientRect().top + scrollY; scrollTo(0, y - 300); await new Promise(r => setTimeout(r, 300));
      const шапка = getStickyOffset(); scrollTo(0, y - шапка - 4); await new Promise(r => setTimeout(r, 300));
      показатьЗапрет(с, с.dataset.blockedText, false);
      const t = document.getElementById('exclTooltip').getBoundingClientRect(), r = с.getBoundingClientRect();
      return { шапка: getStickyOffset(), верх: Math.round(t.top), подСтрокой: t.top >= r.bottom - 1, строка: Math.round(r.top) }; }""")
    if ш_["верх"] < ш_["шапка"] - 1 or not ш_["подСтрокой"]:
        НАХОДКИ.append(f"{н} у строки под липкой шапкой подсказка ушла под шапку: {ш_}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for ночь in (False, True):
                    прогон(бр, порт, ш, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: подсказка «Недоступно» лежит под окном уголка и под боковой панелью, над страницей видна, "
          "а у строки под липкой шапкой уходит под строку — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
