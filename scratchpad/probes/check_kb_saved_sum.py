#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет бруса открывается тем же, чем был сохранён.

Константин 13.10.2026, пресетом 613738 (менеджер вписал цены водостока и
снегозадержателей, а у Константина на их месте стояло «укажите площадь»):
«Проверь, чтобы в пресет все сохранялось».

Площади в пресете сохранялись. Терялось другое: суммы, вписанные руками в поле
«введите сумму» у водостока и снегозадержателей бруса, когда у них ещё не было
расчёта от площади кровли. Сейчас на месте поля — метка площади; открытый
расчёт клал сумму в поле, которого больше нет, и терял её, а следующее
сохранение стирало сумму из пресета.

Проба держит:
  • старый пресет (площадей нет, суммы вписаны) открывается с этими суммами в
    полях «введите сумму», они идут в итог, снова пишутся в сохранение, а
    отмеченную опцию можно снять и отметить снова;
  • вписали площадь — цену даёт формула; стёрли сумму — снова метка площади;
  • полный пресет бруса (площади, толщина, отмеченные, вписанная сумма,
    маржа формулы, свои позиции и примечания, подарки, звёзды, выделения,
    вариант материала, скидка, клиент) после сохранения и открытия в чистой
    странице даёт тот же снимок, ключ в ключ, и тот же итог.

    python3 check_kb_saved_sum.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_glulam_sections as г
import check_glulam_blocks_3_7 as б
from playwright.sync_api import sync_playwright

НАХОДКИ = []
П1, П2 = б.П1, б.П2
# Позиция без цены и без формулы — у неё поле «введите сумму»: им проверяется,
# что вписанная руками сумма обычной опции переживает сохранение.
ТАБЛИЦЫ = б.таблицы()
ТАБЛИЦЫ["pricing_options"].append({"product": "glulam", "option_id": "kb_x9", "name": "Позиция без цены (проба)",
                                   "section": "extra", "included": False, "price": None, "formula": None,
                                   "status": None, "sort": 1600, "shared_option": None})


def страница(бр):
    к = бр.new_context(viewport={"width": 1440, "height": 900})
    стр = к.new_page()
    стр.ошибки = []
    стр.on("pageerror", lambda e: стр.ошибки.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{ПОРТ}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { for (const ид of ['pricingErrorScreen', 'loginScreen']) { const э = document.getElementById(ид); if (э) э.style.display = 'none'; }
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400)); }""")
    return к, стр


def открыть(стр, снимок):
    стр.evaluate("(с) => restoreState(с)", снимок)
    стр.wait_for_timeout(1600)


ВИД = """() => { const п = ид => { const э = document.getElementById('por_' + ид); return э ? э.value : null; };
  const метка = ид => !!document.querySelector('#optprice_' + ид + ' .kb-need-area');
  const с = collectState();
  return { водосток: п('kb_r2'), снег: п('kb_r4'), меткаВодостока: метка('kb_r2'), меткаСнега: метка('kb_r4'),
    итог: Math.round(al2ИтогДо()), вСохранении: с.porValues, площади: с.kbAreas,
    отмечены: [!!checkedOptions.kb_r2, !!checkedOptions.kb_r4] }; }"""


def старый_пресет(бр):
    к, стр = страница(бр)
    снимок = стр.evaluate("""(п) => { selectProjectOption(PROJECTS.findIndex(p => p[0] === п)); kbSetArea('roof', ''); kbSetArea('fasad', ''); calc();
      const без = Math.round(al2ИтогДо());
      const с = collectState(); с.checkedOptions = Object.assign({}, с.checkedOptions, { kb_r2: true, kb_r4: true });
      с.porValues = Object.assign({}, с.porValues, { kb_r2: '34 650', kb_r4: '18 360' }); с.kbAreas = { fasad: null, roof: null };
      return { с, без }; }""", П2)
    к.close()
    к, стр = страница(бр)
    открыть(стр, json.loads(json.dumps(снимок["с"])))
    в = стр.evaluate(ВИД)
    print("  старый пресет:", в)
    if в["водосток"] != "34 650" or в["снег"] != "18 360":
        НАХОДКИ.append(f"старый пресет: вписанные суммы не встали в поля — водосток {в['водосток']!r}, снегозадержатели {в['снег']!r}")
    if в["меткаВодостока"] or в["меткаСнега"]:
        НАХОДКИ.append("старый пресет: на месте вписанной суммы стоит метка площади")
    if в["итог"] - снимок["без"] != 34650 + 18360:
        НАХОДКИ.append(f"старый пресет: суммы не в итоге — итог {в['итог']}, без них {снимок['без']}")
    if (в["вСохранении"] or {}).get("kb_r2") != "34 650" or (в["вСохранении"] or {}).get("kb_r4") != "18 360":
        НАХОДКИ.append(f"старый пресет: в новое сохранение суммы не пишутся: {в['вСохранении']}")
    # снять и отметить снова
    стр.evaluate("() => { toggleOpt('kb_r2'); toggleOpt('kb_r2'); calc(); }")
    if not стр.evaluate("() => !!checkedOptions.kb_r2"):
        НАХОДКИ.append("старый пресет: водосток с вписанной суммой не отмечается снова — требует площадь")
    # площадь даёт формулу, поле уходит
    стр.evaluate("() => { kbSetArea('roof', '100'); calc(); }")
    п = стр.evaluate("() => ({ поле: !!document.getElementById('por_kb_r2'), цена: getOptPrice(getOpt('kb_r2')) })")
    if п["поле"] or not п["цена"]:
        НАХОДКИ.append(f"площадь вписана, а водосток не считается формулой: {п}")
    # без площади и со стёртой суммой — метка
    стр.evaluate("() => { kbSetArea('roof', ''); calc(); }")
    открыть(стр, json.loads(json.dumps(снимок["с"])))
    стр.evaluate("() => { const э = document.getElementById('por_kb_r4'); if (!э) return; э.value = ''; э.dispatchEvent(new Event('input', { bubbles: true })); refreshOptPricesInDOM(); }")
    if not стр.evaluate("() => !!document.querySelector('#optprice_kb_r4 .kb-need-area')"):
        НАХОДКИ.append("стёрли вписанную сумму снегозадержателей — метка площади не вернулась")
    for о in стр.ошибки[:3]:
        НАХОДКИ.append(f"старый пресет: ошибка страницы {о[:160]}")
    к.close()


ИСКЛЮЧИТЬ = {"savedAt"}


def полный_пресет(бр):
    к, стр = страница(бр)
    с1 = стр.evaluate("""async (п) => {
      selectProjectOption(PROJECTS.findIndex(p => p[0] === п)); await new Promise(r => setTimeout(r, 300));
      kbSetArea('fasad', '120'); kbSetArea('roof', '95'); setThickness(2);
      ['kb_p4', 'kb_e2', 'kb_s15', 'kb_r2', 'kb_r4'].forEach(ид => { if (!checkedOptions[ид]) toggleOpt(ид); });
      const por = [...document.querySelectorAll('.price-on-request-input')].find(э => э.id.startsWith('por_'));
      let porИд = null;
      if (por) { porИд = por.id.slice(4); por.value = '12 345'; por.dispatchEvent(new Event('input', { bubbles: true })); if (!checkedOptions[porИд]) toggleOpt(porИд); }
      (customOptions.extra = customOptions.extra || []).push({ id: ++customIdCounter, name: 'Своя позиция пробы', price: 7777, checked: true });
      (customNotes.extra = customNotes.extra || []).push({ id: 'cn_' + (++customNoteIdCounter), text: 'Своё примечание пробы' });
      giftedOpts.add('kb_s15'); starredOpts.add('kb_p4'); highlightedOpts.add('kb_e2');
      try { formulaOverrides.kb_r2 = Object.assign({}, formulaOverrides.kb_r2, { margin: 0.35 }); } catch (e) {}
      const д = document.getElementById('discountPctInput'); if (д) { д.value = '5'; д.dispatchEvent(new Event('input', { bubbles: true })); }
      const кл = document.getElementById('clientName'); if (кл) { кл.value = 'Клиент Пробный'; кл.dispatchEvent(new Event('input', { bubbles: true })); }
      // Свои позиция и примечание положены в данные — строки им рисует перерисовка;
      // вписанная сумма через неё переживает (тот же путь, что при смене режима цен).
      renderOptionSections({ сохранитьСуммы: true });
      calc(); await new Promise(r => setTimeout(r, 300));
      return collectState(); }""", П1)
    к.close()
    к, стр = страница(бр)
    открыть(стр, json.loads(json.dumps(с1)))
    с2 = стр.evaluate("() => collectState()")
    # Варианты и режимы хранятся по id опции; id, которых нет в каталоге
    # технологии, открытие расчёта вычищает нарочно (sanitizeOrphanOptIds).
    есть = set(стр.evaluate("() => OPTIONS.map(o => o.id)"))
    for ключ in ("optVariants", "conditionalModes"):
        for с in (с1, с2):
            с[ключ] = {к: в for к, в in (с.get(ключ) or {}).items() if к in есть}
    разные = [ключ for ключ in sorted(set(с1) | set(с2)) if ключ not in ИСКЛЮЧИТЬ
              and json.dumps(с1.get(ключ), sort_keys=True, ensure_ascii=False) != json.dumps(с2.get(ключ), sort_keys=True, ensure_ascii=False)]
    print("  полный пресет: ключей", len(с1), "разошлись:", разные)
    for ключ in разные:
        НАХОДКИ.append(f"полный пресет: «{ключ}» после открытия другое: было {json.dumps(с1.get(ключ), ensure_ascii=False)[:160]}, "
                       f"стало {json.dumps(с2.get(ключ), ensure_ascii=False)[:160]}")
    for ключ, ждём in (("kbAreas", {"fasad": 120, "roof": 95}), ("thickness", 2)):
        if с1.get(ключ) != ждём:
            НАХОДКИ.append(f"полный пресет: проба не выставила {ключ}: {с1.get(ключ)}")
    if not с1.get("porValues"):
        НАХОДКИ.append("полный пресет: в пробе нет вписанной суммы — проверять нечего")
    # Открыли другой расчёт — суммы прежнего туда не переезжают.
    чистый = json.loads(json.dumps(с1)); чистый["porValues"] = {}
    открыть(стр, чистый)
    чужие = стр.evaluate("() => [...document.querySelectorAll('input.price-on-request-input[id^=\"por_\"]')].filter(э => э.value).map(э => э.id)")
    if чужие:
        НАХОДКИ.append(f"открыт расчёт без вписанных сумм, а в полях суммы прежнего: {чужие}")
    # Смена режима цен перерисовывает разделы — вписанная сумма остаётся.
    открыть(стр, json.loads(json.dumps(с1)))
    ид = next(iter(с1.get("porValues") or {}), None)
    if ид:
        стр.evaluate("() => { try { setOptionPricingMode('legacy'); setOptionPricingMode('new'); } catch (e) { renderOptionSections({ сохранитьСуммы: true }); } }")
        осталось = стр.evaluate("(ид) => (document.getElementById('por_' + ид) || {}).value || ''", ид)
        if осталось != с1["porValues"][ид]:
            НАХОДКИ.append(f"после смены режима цен вписанная сумма {ид}: {осталось!r}, ждали {с1['porValues'][ид]!r}")
    for о in стр.ошибки[:3]:
        НАХОДКИ.append(f"полный пресет: ошибка страницы {о[:160]}")
    к.close()


def главная():
    global ПОРТ
    с, ПОРТ = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            старый_пресет(бр)
            полный_пресет(бр)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: старый пресет бруса открывается с вписанными суммами — в полях, в итоге и в новом сохранении; "
          "площадь даёт формулу, стёртая сумма — метку; полный пресет бруса после сохранения и открытия — тот же снимок ключ в ключ.")


if __name__ == "__main__":
    главная()
