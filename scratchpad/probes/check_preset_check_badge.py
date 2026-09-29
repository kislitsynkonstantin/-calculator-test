#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Счётчик замечаний проверки на значке мини-окна.

Константин 29.09.2026, по макету mockups/mini-window-check-badge-v2.html:
«внедряй только оранжевый без стопа» — вариант 01, кружок на правом верхнем
углу значка, один тёплый цвет и при стопе, и без него; в «Настройках» —
переключатель «Замечания проверки на значке пресета».

Проба на 390 и 1440, днём и ночью, держит:
  • у своего пресета на значке кружок с числом замечаний — тем же, что во
    вкладке «Проверка»; стоит на правом верхнем углу значка и не выходит за
    край экрана;
  • цвет кружка тёплый и один: при стопе не меняется, у серого чужого
    значка тоже;
  • число живёт вместе с расчётом: сняли пробное бурение — число выросло,
    вернули — вернулось, без перерисовки остального значка;
  • у общего пресета кружок стоит над замком и сам замок не закрывает;
  • у несохранённого расчёта кружка нет; у раскрытого мини-окна кружок не
    выглядывает из-под окна краем;
  • при первой загрузке счётчик выключен; переключатель в «Настройках»
    включает и выключает его и пишет настройку в профиль аккаунта, а
    включённая в профиле настройка приходит на новое устройство.

    python3 check_preset_check_badge.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
# Медовый, вариант 01 макета check-counter-colors-v1 без ободка (30.09.2026).
ТЁПЛЫЙ = {False: "rgb(234, 168, 72)", True: "rgb(227, 162, 74)"}

КРУЖОК = """() => { const з = document.getElementById('presetChip'), с = з && з.querySelector('.pc-ckn');
  const пр = проверкаПоЧекЛисту();
  const r = з.getBoundingClientRect();
  const о = { есть: !!с, класс: з.className, число: пр.замечания.length, стоп: пр.замечания.filter(x => x.стоп).length,
              метка: (з.querySelector('.pc-body') || {}).getAttribute ? з.querySelector('.pc-body').getAttribute('aria-label') : '',
              шир: innerWidth, зн: { l: r.left, t: r.top, r: r.right, b: r.bottom } };
  if (с) { const k = с.getBoundingClientRect(), cs = getComputedStyle(с);
    о.текст = с.textContent; о.фон = cs.backgroundColor; о.тень = cs.boxShadow; о.ночь = document.body.classList.contains('dark'); о.видим = cs.display !== 'none' && cs.visibility !== 'hidden' && k.width > 0;
    о.к = { l: k.left, t: k.top, r: k.right, b: k.bottom }; }
  const лк = з.querySelector('.pc-lk svg');
  if (лк) { const л = лк.getBoundingClientRect(); о.замок = { l: л.left, t: л.top, r: л.right, b: л.bottom }; }
  return о; }"""


def кружок(стр):
    стр.wait_for_timeout(120)
    return стр.evaluate(КРУЖОК)


def проверить_кружок(н, с, что):
    if not с["число"]:
        НАХОДКИ.append(f"{н} {что}: в расчёте нет замечаний — проверять нечего"); return
    if not с["есть"] or not с.get("видим"):
        НАХОДКИ.append(f"{н} {что}: кружка с числом замечаний на значке нет ({с['число']} замечаний)"); return
    # Размер — 19 px, на 5 % меньше прежних 20 (30.09.2026).
    if abs((с["к"]["b"] - с["к"]["t"]) - 19) > 0.6:
        НАХОДКИ.append(f"{н} {что}: высота кружка {с['к']['b'] - с['к']['t']:.1f} px, ждали 19")
    if с["текст"] != str(с["число"]):
        НАХОДКИ.append(f"{н} {что}: на кружке «{с['текст']}», а замечаний {с['число']}")
    if с["фон"] != ТЁПЛЫЙ[с["ночь"]]:
        НАХОДКИ.append(f"{н} {что}: кружок не медовый: {с['фон']} (стопов {с['стоп']})")
    # Ободка нет: у тени кружка нулевое размытие давало бы ровное кольцо.
    if " 0px 0px 0px 2px" in (с.get("тень") or "") or "0px 0px 0px" in (с.get("тень") or ""):
        НАХОДКИ.append(f"{н} {что}: у кружка ободок: {с['тень']}")
    к_, з = с["к"], с["зн"]
    # на правом верхнем углу: заходит за верх и за правый край значка, но не дальше половины себя
    if not (к_["t"] < з["t"] < к_["b"]) or not (к_["l"] < з["r"] < к_["r"]):
        НАХОДКИ.append(f"{н} {что}: кружок не на правом верхнем углу значка: кружок {к_}, значок {з}")
    if к_["r"] > с["шир"] - 2:
        НАХОДКИ.append(f"{н} {что}: кружок у самого края экрана: правый край {к_['r']:.0f} при ширине {с['шир']}")
    if "по чек-листу" not in (с["метка"] or ""):
        НАХОДКИ.append(f"{н} {что}: число замечаний не сказано словами у значка: «{с['метка']}»")


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(бр, порт, ш, в, ночь)
    if not стр.evaluate("() => activePresetId"):
        НАХОДКИ.append(f"{н} пресет не сохранился"); стр.close(); return
    # Замечание со стопом: водосток при обшивке фасада — чтобы проверить, что цвет при стопе тот же.
    стр.evaluate("""() => { const о = (OPTIONS || []).find(o => o.section === 'exterior' && /^Обшивка стен/i.test(o.name || '') && !checkedOptions[o.id]);
      if (о) toggleOpt(о.id); }""")
    стр.wait_for_timeout(500)
    # По умолчанию счётчик выключен; переключатель в «Настройках» включает его
    # и пишет в профиль аккаунта.
    с = кружок(стр)
    if с["есть"] or стр.evaluate("() => appSettings.showCheckBadge") is not False:
        НАХОДКИ.append(f"{н} при первой загрузке счётчик не выключен: кружок {с['есть']}, настройка {стр.evaluate('() => appSettings.showCheckBadge')}")
    стр.evaluate("() => openSettings()"); стр.wait_for_timeout(500)
    пер = стр.locator('input[aria-label="Замечания проверки на значке пресета"]')
    ПРОФИЛЬ = "() => { const п = (window.__ТАБЛИЦЫ.profiles || [])[0]; return п && п.app_settings ? п.app_settings.showCheckBadge : undefined; }"
    if not пер.count():
        НАХОДКИ.append(f"{н} в «Настройках» нет переключателя «Замечания проверки на значке пресета»")
        стр.evaluate("() => { appSettings.showCheckBadge = true; }")
    else:
        if пер.first.is_checked():
            НАХОДКИ.append(f"{н} переключатель при первой загрузке включён")
        for вкл in (True, False, True):
            пер.first.evaluate(f"e => {{ e.checked = {'true' if вкл else 'false'}; e.dispatchEvent(new Event('change')); }}"); стр.wait_for_timeout(300)
            с = кружок(стр)
            if с["есть"] != вкл:
                НАХОДКИ.append(f"{н} переключатель {'включён' if вкл else 'выключен'}, а кружок {'не появился' if вкл else 'остался'}")
            if стр.evaluate(ПРОФИЛЬ) is not вкл:
                НАХОДКИ.append(f"{н} переключатель {'включён' if вкл else 'выключен'}, а в профиль аккаунта ушло {стр.evaluate(ПРОФИЛЬ)}")
    стр.evaluate("() => { try { closeSettings(); } catch (e) {} const о = document.getElementById('settingsOverlay'); if (о) о.classList.remove('show'); }")
    стр.wait_for_timeout(300)
    обновить = "() => { try { обновитьСчётчикПроверки(); } catch (e) {} }"
    стр.evaluate(обновить)
    с = кружок(стр)
    проверить_кружок(н, с, "свой пресет")
    if с["число"] and not с["стоп"]:
        НАХОДКИ.append(f"{н} в расчёте не нашлось стопа — цвет при стопе не проверен")
    стр.screenshot(path=str(м.СНИМКИ / f"check-badge-own-{ш}{'-n' if ночь else ''}.png"))
    # Раскрытое мини-окно закрывает значок — кружок не выглядывает из-под него краем.
    к.открыть(стр); стр.wait_for_timeout(300)
    ви = стр.evaluate("""() => { const c = document.querySelector('#presetChip .pc-ckn'), k = document.getElementById('presetChipCard');
      if (!c || !k.classList.contains('show')) return null; const a = c.getBoundingClientRect(), b = k.getBoundingClientRect();
      const снаружи = a.right > b.right + .5 || a.left < b.left - .5 || a.top < b.top - .5 || a.bottom > b.bottom + .5;
      return getComputedStyle(c).visibility !== 'hidden' && снаружи; }""")
    if ви:
        НАХОДКИ.append(f"{н} мини-окно раскрыто, а кружок выглядывает из-под него краем")
    стр.evaluate("() => закрытьКарточкуЗначка()"); стр.wait_for_timeout(300)
    # Число живёт с расчётом: сняли пробное бурение — прибавилось замечание;
    # вернули — ушло. Без перерисовки значка.
    было = с["число"]
    if стр.evaluate("() => !!checkedOptions.f3 && !!getOpt('f3')"):
        стр.evaluate("() => toggleOpt('f3')"); стр.wait_for_timeout(500)
        с = кружок(стр)
        if с["число"] != было + 1:
            НАХОДКИ.append(f"{н} снятое пробное бурение не прибавило замечания: было {было}, стало {с['число']}")
        elif с.get("текст") != str(с["число"]):
            НАХОДКИ.append(f"{н} кружок не обновился после правки расчёта: «{с.get('текст')}», замечаний {с['число']}")
        стр.evaluate("() => toggleOpt('f3')"); стр.wait_for_timeout(500)
        с = кружок(стр)
        if с["число"] != было or с.get("текст") != str(было):
            НАХОДКИ.append(f"{н} вернули пробное бурение, а кружок не вернулся к {было}: «{с.get('текст')}»")
    else:
        НАХОДКИ.append(f"{н} пробное бурение не отмечено — правка расчёта не проверена")
    # Чужой общий — серый значок с замком.
    стр.evaluate("""() => { закрытьКарточкуЗначка(); _sharedPresets.push({ short_code: '111222', id: '111222', name: 'Баня «Лейпциг» 5×7', author_name: 'Сергей Волков',
      author_id: 'u-другой', is_public: true, visibility: 'public', locked: true, created_at: '2026-09-22T13:05:00Z', updated_at: '2026-09-22T13:05:00Z', state: {} });
      openSharedPreset('111222'); }""")
    стр.wait_for_timeout(1500)
    с = кружок(стр)
    if "pc-other" not in с["класс"]:
        НАХОДКИ.append(f"{н} чужой общий пресет не открылся: {с['класс']}")
    else:
        проверить_кружок(н, с, "чужой общий")
        if с.get("замок") and с.get("к"):
            к_, л = с["к"], с["замок"]
            if not (к_["b"] <= л["t"] or к_["r"] <= л["l"] or к_["l"] >= л["r"]):
                НАХОДКИ.append(f"{н} кружок закрывает замок: кружок {к_}, замок {л}")
        elif not с.get("замок"):
            НАХОДКИ.append(f"{н} у чужого общего нет замка на значке")
        стр.screenshot(path=str(м.СНИМКИ / f"check-badge-other-{ш}{'-n' if ночь else ''}.png"))
    # Несохранённый расчёт — кружка нет.
    стр.evaluate("() => { try { exitSharedMode(); } catch (e) {} _activeSharedCode = null; setActivePreset(null); отрисоватьЗначокПресета(); }")
    стр.wait_for_timeout(500)
    с = кружок(стр)
    if "pc-unsaved" in с["класс"] and с["есть"]:
        НАХОДКИ.append(f"{н} у несохранённого расчёта на значке кружок замечаний")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def из_профиля(бр, порт, ш, в):
    """Настройка аккаунта: включена в профиле — счётчик есть и на новом устройстве."""
    н = f"[{ш} из профиля]"
    было = м.ТАБЛИЦЫ_JS
    м.ТАБЛИЦЫ_JS = было + "\n;window.__ТАБЛИЦЫ.profiles.forEach(п => { п.app_settings = Object.assign({}, п.app_settings, { showCheckBadge: true }); });"
    try:
        стр, ошибки = к.начать(бр, порт, ш, в, False)
    finally:
        м.ТАБЛИЦЫ_JS = было
    if стр.evaluate("() => appSettings.showCheckBadge") is not True:
        НАХОДКИ.append(f"{н} включённая в профиле настройка не пришла на устройство")
    с = кружок(стр)
    if с["число"] and not с["есть"]:
        НАХОДКИ.append(f"{н} в профиле счётчик включён, а на значке его нет")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в, ночь in ((390, 844, False), (390, 844, True), (1440, 900, False), (1440, 900, True)):
                прогон(бр, порт, ш, в, ночь)
            из_профиля(бр, порт, 390, 844)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: на значке своего и чужого общего пресета кружок с числом замечаний — тёплый и при стопе, на правом "
          "верхнем углу, над замком, не у края экрана; число меняется с расчётом; у несохранённого кружка нет; "
          "по умолчанию он выключен, переключатель в «Настройках» включает его и пишет в профиль, профиль включает его на новом устройстве — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
