#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Открытая терраса — цена по площади, площадь вписывается руками.

Константин 01.10.2026, снимком раздела «Доп. опции и логистика»: «вот эту
опцию сделай формульную. Норму стоимости за м2 возьми из этого поля. Поле
ручное: можно вбить площадь открытой террасы и посчитает цену». В каталоге
«Устройство открытой террасы 12 м²» — 144 000 ₽, то есть 12 000 ₽ за метр.

Проба на 390 и 1440, в «Бланке» и «Модерне», днём и ночью, держит:
  • на карточке поле площади со значением 12 и подписью «м²», цена 144 000 ₽;
  • вписали 20 и Enter — цена 240 000 ₽, в имени «… 20 м²», строка при этом
    не отметилась и не снялась;
  • «+» — 21 м², 252 000 ₽; отмеченная опция входит в итог этой суммой;
  • не число — поле возвращается к прежней площади;
  • площадь живёт в расчёте: collectState() и обратно через restoreState();
  • поле и кнопки не вылезают за строку, поле не уже 28 px;
  • в покое поле выглядит числом — без линии и подложки; нажали — линия и
    подложка появляются («зачем тут подчёркивание. Если нажимаю вручную
    ввести, тогда активируй поле», 01.10.2026).

    python3 check_terrace_area.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СОСТ = """() => { const э = document.getElementById('lbl_e10'); if (!э) return null;
  const п = document.getElementById('qtyval_e10'), ц = document.getElementById('optprice_e10'), r = э.getBoundingClientRect();
  const вылез = [...э.querySelectorAll('.opt-qty-stepper, .opt-qty-stepper *')].some(х => { const q = х.getBoundingClientRect(); return q.width && (q.right > r.right + 1 || q.left < r.left - 1); });
  return { поле: п ? п.tagName : '', знач: п ? (п.value ?? п.textContent) : '', ед: (э.querySelector('.opt-qty-unit') || {}).textContent || '',
    цена: ц ? ц.textContent.replace(/\\s/g, ' ').trim() : '', имя: (э.querySelector('.opt-name') || {}).textContent || '', отмечена: !!checkedOptions.e10,
    ширина: п ? Math.round(п.getBoundingClientRect().width) : 0, вылез,
    линия: п ? getComputedStyle(п).borderBottomColor : '', подложка: п ? getComputedStyle(п).backgroundColor : '',
    зазор: (() => { const е = э.querySelector('.opt-qty-unit'); if (!п || !е || п.tagName !== 'INPUT') return null;
      const кс = getComputedStyle(п), х = document.createElement('canvas').getContext('2d'); х.font = кс.font;
      const пр = п.getBoundingClientRect(), ер = е.getBoundingClientRect();
      const конец = (кс.textAlign === 'right' || кс.textAlign === 'end') ? пр.right - parseFloat(кс.paddingRight) - parseFloat(кс.borderRightWidth)
        : кс.textAlign === 'center' ? пр.left + пр.width / 2 + х.measureText(п.value).width / 2
        : пр.left + parseFloat(кс.paddingLeft) + parseFloat(кс.borderLeftWidth) + х.measureText(п.value).width;
      return { до_ед: Math.round((ер.left - конец) * 10) / 10, вместе: Math.round(ер.right - пр.left) }; })() }; }"""


def прогон(бр, порт, ш, в, ночь, тема):
    н = f"[{ш} {тема}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(бр, порт, ш, в, ночь)
    if тема == "modern":
        стр.evaluate("() => applyUiStyle('modern', false)")
    # В учебном каталоге строки террасы нет — цена как в базе: 144 000 ₽ за 12 м².
    стр.evaluate("() => { const о = getOpt('e10'); if (о) о.price = 144000; renderOptionSections(); calc(); }")
    стр.wait_for_timeout(300)
    стр.evaluate("() => { const э = document.getElementById('lbl_e10'); if (э) э.scrollIntoView({ block: 'center' }); }")
    стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ)
    if not с:
        НАХОДКИ.append(f"{н} строки открытой террасы нет"); стр.close(); return
    if с["поле"] != "INPUT" or с["знач"] != "12" or с["ед"] != "м²" or "144 000" not in с["цена"]:
        НАХОДКИ.append(f"{н} до правки: {с}")
    if с["поле"] != "INPUT":
        стр.close(); return
    прозр = ("rgba(0, 0, 0, 0)", "transparent")
    if с["линия"] not in прозр or с["подложка"] not in прозр:
        НАХОДКИ.append(f"{н} в покое поле площади с линией или подложкой: {с['линия']}, {с['подложка']}")
    стр.locator("#qtyval_e10").focus(); стр.wait_for_timeout(350)
    ф = стр.evaluate(СОСТ)
    if ф["линия"] in прозр or ф["подложка"] in прозр:
        НАХОДКИ.append(f"{н} нажали на площадь — поле не проявилось: {ф['линия']}, {ф['подложка']}")
    стр.evaluate("() => document.activeElement && document.activeElement.blur()")
    if с["зазор"] is None or с["зазор"]["до_ед"] > 5 or с["зазор"]["до_ед"] < 0.5:
        НАХОДКИ.append(f"{н} в покое «м²» не вплотную к числу: {с['зазор']}")
    if с["зазор"] and с["зазор"]["вместе"] < 28:
        НАХОДКИ.append(f"{н} число с «м²» вместе уже 28 px: {с['зазор']}")
    if ф["зазор"] is None or ф["зазор"]["до_ед"] < 8 or ф["ширина"] < 28:
        НАХОДКИ.append(f"{н} при вводе «м²» не отошла или поле узкое: ширина {ф['ширина']}, {ф['зазор']}")
    if с["вылез"] or ф["вылез"]:
        НАХОДКИ.append(f"{н} поле площади вылезает за строку")
    стр.locator("#lbl_e10 .opt-qty-unit").click(); стр.wait_for_timeout(200)
    if стр.evaluate("() => document.activeElement && document.activeElement.id") != "qtyval_e10":
        НАХОДКИ.append(f"{н} нажатие на «м²» не открывает ввод")
    стр.evaluate("() => document.activeElement && document.activeElement.blur()"); стр.wait_for_timeout(250)
    if стр.evaluate(СОСТ)["зазор"] != с["зазор"]:
        НАХОДКИ.append(f"{н} после ввода «м²» не вернулась к числу: {стр.evaluate(СОСТ)['зазор']} против {с['зазор']}")
    поле = стр.locator("#qtyval_e10")
    поле.click(); поле.fill("20"); поле.press("Enter"); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ)
    if "240 000" not in с["цена"] or not с["имя"].endswith("20 м²") or с["отмечена"]:
        НАХОДКИ.append(f"{н} вписали 20: {с}")
    стр.locator("#lbl_e10 .opt-qty-btn").nth(1).click(); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ)
    if "252 000" not in с["цена"] or с["знач"] != "21":
        НАХОДКИ.append(f"{н} «+»: {с}")
    итог = стр.evaluate("() => { const б = calc() || 0; toggleOpt('e10'); calc(); const п = parseInt((document.getElementById('totalDisplay').textContent || '').replace(/\\D/g, ''), 10); toggleOpt('e10'); calc(); const до = parseInt((document.getElementById('totalDisplay').textContent || '').replace(/\\D/g, ''), 10); return п - до; }")
    if итог != 252000:
        НАХОДКИ.append(f"{н} отмеченная терраса меняет итог на {итог}, ждали 252 000")
    поле.click(); поле.fill("абв"); поле.press("Enter"); стр.wait_for_timeout(200)
    с = стр.evaluate(СОСТ)
    if с["знач"] != "21" or "252 000" not in с["цена"]:
        НАХОДКИ.append(f"{н} не число: поле {с['знач']!r}, цена {с['цена']}")
    сох = стр.evaluate("() => { const ст = collectState(); return (ст.formulaOverrides || {}).e10 || null; }")
    if not сох or сох.get("area") != 21:
        НАХОДКИ.append(f"{н} площадь не в расчёте: {сох}")
    стр.evaluate("() => { const ст = collectState(); delete formulaOverrides.e10; renderOptionSections(); calc(); restoreState(ст); }")
    стр.wait_for_timeout(600)
    с = стр.evaluate(СОСТ)
    if с["знач"] != "21" or "252 000" not in с["цена"] or not с["имя"].endswith("21 м²"):
        НАХОДКИ.append(f"{н} после restoreState: {с}")
    if ш == 390 and not ночь and тема == "blank":
        стр.evaluate("() => document.getElementById('lbl_e10').scrollIntoView({ block: 'center' })")
        стр.screenshot(path=str(м.СНИМКИ / "terrace-390.png"))
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
                    for тема in ("blank", "modern"):
                        прогон(СоШрифтами(бр), порт, ш, в, ночь, тема)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: открытая терраса считается по площади — 12 000 ₽ за м² от цены каталога; площадь вписывается в поле "
          "и шагает кнопками, имя и итог идут за ней, не число не принимается, площадь живёт в расчёте — на 390 и 1440, "
          "в «Бланке» и «Модерне», днём и ночью.")


if __name__ == "__main__":
    главная()
