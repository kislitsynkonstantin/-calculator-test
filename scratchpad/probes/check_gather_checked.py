#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Настройка «Собирать выбранные опции».

Константин 12.10.2026, снимком «Окон и дверей»: «Добавь тоггл в настройках
„Собирать выбранные опции“. Чтобы аккуратно с приятной анимацией
перемещались».

Проба держит, каркас, раздел «Кровля» (в нём больше всего свободных опций у
заглушки), 1440 px:
  • по умолчанию включено; выключенное — строки стоят в порядке разметки;
  • включили — на экране сверху базовые строки, за ними выбранные опции,
    ниже остальные; внутри группы порядок разметки;
  • поставили галочку руками — строка переезжает плавно (transform с
    переходом), после переезда стоит в группе выбранных;
  • порядок в разметке не меняется: сохранённый порядок перетаскивания
    (`optOrder`) тот же, что до включения;
  • выключили — экран снова в порядке разметки;
  • при prefers-reduced-motion переезд без анимации;
  • переключатель есть в «Настройках».

    python3 check_gather_checked.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ВИД = """(раздел) => { const список = document.getElementById('list_' + раздел);
  const строки = [...список.children].filter(э => э.classList.contains('opt-item') && э.getClientRects().length);
  const поЭкрану = строки.slice().sort((а, б) => а.getBoundingClientRect().top - б.getBoundingClientRect().top);
  const группа = э => { const o = э.dataset.optId ? getOpt(э.dataset.optId) : null; return o && o.included ? 0 : (э.classList.contains('active') ? 1 : 2); };
  return { разметка: строки.map(э => э.id), экран: поЭкрану.map(э => э.id), группы: поЭкрану.map(группа) }; }"""
ПОРЯДОК = "() => JSON.stringify(collectState().optOrder)"


def прогон(бр, порт, тихо=False):
    к = бр.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce" if тихо else "no-preference")
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    раздел = "roof"
    if тихо:
        стр.evaluate("() => { appSettings.gatherChecked = true; собратьВыбранные(false); }")
        цель = стр.evaluate("() => (OPTIONS.find(o => o.section === 'roof' && !o.included && !checkedOptions[o.id] && isOptionVisible(o) && !document.getElementById('por_' + o.id) && document.getElementById('lbl_' + o.id).dataset.blocked !== '1') || {}).id")
        стр.evaluate(f"() => toggleOpt('{цель}')")
        п = стр.evaluate(f"() => document.getElementById('lbl_{цель}').style.transition")
        if "transform" in (п or ""):
            НАХОДКИ.append(f"reduced-motion: строка всё равно едет с анимацией ({п})")
        к.close()
        return
    if (appdef := стр.evaluate("() => appSettings.gatherChecked")) is not True:
        НАХОДКИ.append(f"по умолчанию настройка выключена: {appdef}")
    # Дальше проба идёт от выключенного состояния: так видно и «выключили —
    # порядок разметки», и переезд при включении.
    стр.evaluate("() => { appSettings.gatherChecked = false; собратьВыбранные(false); }")
    с = стр.evaluate(ВИД, раздел)
    if с["экран"] != с["разметка"]:
        НАХОДКИ.append("выключено, а экранный порядок не совпадает с разметкой")
    порядок_до = стр.evaluate(ПОРЯДОК)
    # Выберем две опции, чтобы выбранные стояли вперемешку с невыбранными.
    цели = стр.evaluate("""() => OPTIONS.filter(o => o.section === 'roof' && !o.included && isOptionVisible(o)
        && !document.getElementById('por_' + o.id) && document.getElementById('lbl_' + o.id).dataset.blocked !== '1').map(o => o.id)""")
    if len(цели) < 3:
        НАХОДКИ.append(f"в разделе кровли мало опций для пробы: {цели}")
        к.close(); return
    последняя = цели[-1]
    стр.evaluate(f"() => {{ toggleOpt('{последняя}'); }}")
    стр.wait_for_timeout(200)
    стр.evaluate("() => { appSettings.gatherChecked = true; собратьВыбранные(true); }")
    стр.wait_for_timeout(600)
    с = стр.evaluate(ВИД, раздел)
    if с["группы"] != sorted(с["группы"]):
        НАХОДКИ.append(f"включено: на экране группы не по порядку база → выбранные → остальные: {с['группы']}")
    if с["экран"].index("lbl_" + последняя) > с["группы"].count(0) + с["группы"].count(1) - 1:
        НАХОДКИ.append("включено: выбранная опция не стоит в группе выбранных")
    # Галочка руками — плавный переезд
    свободные = [ц for ц in цели[:-1] if стр.evaluate(f"() => !checkedOptions['{ц}'] && document.getElementById('lbl_{ц}').dataset.blocked !== '1'")]
    первая = свободные[0]
    з = стр.evaluate(f"""async () => {{ const э = document.getElementById('lbl_{первая}');
      toggleOpt('{первая}'); await new Promise(r => setTimeout(r, 90));
      return {{ переход: э.style.transition, вПути: getComputedStyle(э).transform }}; }}""")
    if "transform" not in (з["переход"] or "") or з["вПути"] in ("none", "", "matrix(1, 0, 0, 1, 0, 0)"):
        НАХОДКИ.append(f"галочка руками: строка встала на место без анимации ({з})")
    стр.wait_for_timeout(600)
    с = стр.evaluate(ВИД, раздел)
    if с["группы"] != sorted(с["группы"]):
        НАХОДКИ.append(f"после галочки руками группы не по порядку: {с['группы']}")
    if стр.evaluate(f"() => document.getElementById('lbl_{первая}').style.transform"):
        НАХОДКИ.append("после переезда у строки остался сдвиг")
    # Порядок разметки не тронут
    if стр.evaluate(ПОРЯДОК) != порядок_до:
        НАХОДКИ.append("включённая настройка изменила сохранённый порядок перетаскивания")
    # Снимок
    стр.evaluate("() => document.getElementById('list_roof').scrollIntoView({ block: 'start' })")
    стр.wait_for_timeout(300)
    стр.screenshot(path=str(м.СНИМКИ / "gather_1440.png"))
    # Выключили
    стр.evaluate("() => { appSettings.gatherChecked = false; собратьВыбранные(true); }")
    стр.wait_for_timeout(600)
    с = стр.evaluate(ВИД, раздел)
    if с["экран"] != с["разметка"]:
        НАХОДКИ.append("выключили, а экранный порядок не вернулся к разметке")
    # Переключатель в «Настройках»
    есть = стр.evaluate("() => { try { openSettings(); } catch (e) {} const и = document.querySelector('input[aria-label=\"Собирать выбранные опции\"]'); return !!и; }")
    if not есть:
        НАХОДКИ.append("в «Настройках» нет переключателя «Собирать выбранные опции»")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"ошибка страницы: {о[:160]}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт)
            прогон(бр, порт, тихо=True)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: «Собирать выбранные опции» включено по умолчанию; включённое ставит на экране базу, выбранные "
          "и остальные по группам, галочка руками переезжает плавно, порядок разметки и перетаскивания не тронут, "
          "выключение возвращает прежний вид; при reduced-motion без анимации; переключатель в «Настройках».")


if __name__ == "__main__":
    главная()
