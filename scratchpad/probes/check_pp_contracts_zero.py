#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вкладка «Договоры» платёжного плана говорит тем же языком, что боковая панель.

Константин 02.10.2026, снимками боковой панели и вкладки «Договоры»: «если в
спецификации убираю базу, то в платёжном плане наверно эти разделы нужно
сделать бледными. Или дописать, база снята. Или предложи как лучше сделать.
Чтобы было единое поле информации».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • у каждого раздела справа его сумма — та же, что в боковой панели; раздел
    без позиций бледный (чернила ink3, тонкое начертание) и с «—»;
  • под разделами — строка «Итого» с суммой разделов в той же колонке; у
    договора, где пусто всё, — «—»; при скидке второй строкой «со скидкой» —
    цена договора та же, что во вкладке «Платежи»;
  • ничего не обрезано: название договора в поле целиком, сумма раздела не
    касается ручки и названия, строка не выходит за блок.

    python3 check_pp_contracts_zero.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []

СНЯТЬ = """() => { OPTIONS.filter(o => ['interior', 'steam', 'stove'].includes(o.section)).forEach(o => { checkedOptions[o.id] = false; });
  ['interior', 'steam', 'stove'].forEach(к => { try { (getCustomOpts(к) || []).forEach(co => { co.checked = false; }); } catch (e) {} }); calc(); }"""

ВКЛАДКА = """() => { const кэш = _secTotalsCache, цвет = э => getComputedStyle(э).color;
  const чернила3 = (() => { const с = document.createElement('span'); с.style.color = 'var(--bl-ink3)'; document.body.appendChild(с); const ц = getComputedStyle(с).color; с.remove(); return ц; })();
  const строки = [...document.querySelectorAll('#paymentPlanBody .pp-cm-block .pp-cm-chip')].map(ч => {
    const имя = ч.querySelector('.pp-cm-name'), зн = ч.querySelector('.pp-cm-val'), ручка = ч.querySelector(':scope > div:first-child');
    const ри = имя.getBoundingClientRect(), рз = зн ? зн.getBoundingClientRect() : null, рр = ручка.getBoundingClientRect(), рч = ч.getBoundingClientRect();
    const текст = document.createRange(); текст.selectNodeContents(имя); const рт = текст.getBoundingClientRect();
    return { ключ: ч.dataset.key, сумма: кэш[ч.dataset.key] || 0, знач: зн ? зн.textContent.trim() : null, бледный: ч.classList.contains('pp-cm-zero'),
      цветИмени: цвет(имя), вес: getComputedStyle(имя).fontWeight, чернила3,
      доРучки: рз ? рр.left - рз.right : null, отИмени: рз ? рз.left - рт.right : null, внутри: рр.right <= рч.right + 1 && рч.left >= 0 }; });
  const шапки = [...document.querySelectorAll('#paymentPlanBody .pp-cm-block')].map(б => {
    const и = б.querySelector('.pp-cm-head input'), с = б.querySelector('.pp-cm-total');
    const сумм = с ? [...с.querySelectorAll('b')] : [], строки = [...б.querySelectorAll('.pp-cm-chip .pp-cm-val')];
    // Итог стоит в колонке сумм разделов: правые края совпадают.
    const край = сумм[0] && строки[0] ? Math.abs(сумм[0].getBoundingClientRect().right - строки[0].getBoundingClientRect().right) : 0;
    const низ = с ? б.getBoundingClientRect().bottom - Math.max(...сумм.map(в => в.getBoundingClientRect().bottom)) : 99;
    return { низ, имя: и.value, обрезано: и.scrollWidth > и.clientWidth + 1, сумма: сумм[0] ? сумм[0].textContent.trim() : null,
      спец: сумм[1] ? сумм[1].textContent.trim() : '', край,
      ключи: [...б.querySelectorAll('.pp-cm-chip')].map(ч => ч.dataset.key) }; });
  return { строки, шапки, итоги: getPPContracts().map(c => ({ ключи: c.sections, итог: ppGetTotal(c) })) }; }"""


def число(т):
    return int("".join(ц for ц in (т or "") if ц.isdigit()) or 0)


def проверить(н, д, скидка):
    for с in д["строки"]:
        и = f"{н} раздел {с['ключ']}:"
        if с["сумма"] > 0:
            if с["бледный"] or число(с["знач"]) != round(с["сумма"]):
                НАХОДКИ.append(f"{и} сумма {с['сумма']}, а в строке «{с['знач']}», бледный {с['бледный']}")
        else:
            if not с["бледный"] or с["знач"] != "—":
                НАХОДКИ.append(f"{и} пустой раздел не бледный или без «—»: {с}")
            elif с["цветИмени"] != с["чернила3"] or int(с["вес"]) > 300:
                НАХОДКИ.append(f"{и} бледный раздел нарисован {с['цветИмени']} / {с['вес']}, ждали {с['чернила3']} / 300")
        if с["доРучки"] is not None and с["доРучки"] < 4:
            НАХОДКИ.append(f"{и} сумма касается ручки: {с['доРучки']:.1f} px")
        if с["отИмени"] is not None and с["отИмени"] < 8:
            НАХОДКИ.append(f"{и} сумма вплотную к названию: {с['отИмени']:.1f} px")
        if not с["внутри"]:
            НАХОДКИ.append(f"{и} строка выходит за блок")
    for ш in д["шапки"]:
        и = f"{н} договор «{ш['имя']}»:"
        if ш["низ"] < 8:
            НАХОДКИ.append(f"{и} строка «Итого» прижата к нижней линейке: {ш['низ']:.1f} px")
        if ш["край"] > 1:
            НАХОДКИ.append(f"{и} итог не в колонке сумм разделов: расхождение {ш['край']:.1f} px")
        if ш["обрезано"]:
            НАХОДКИ.append(f"{и} название в поле обрезано")
        сумма = sum(round(с["сумма"]) for с in д["строки"] if с["ключ"] in ш["ключи"])
        if сумма > 0 and число(ш["сумма"]) != сумма:
            НАХОДКИ.append(f"{и} в шапке «{ш['сумма']}», сумма разделов {сумма}")
        if сумма == 0 and ш["сумма"] != "—":
            НАХОДКИ.append(f"{и} пустой договор, а в шапке «{ш['сумма']}»")
        итог = next((т["итог"] for т in д["итоги"] if sorted(т["ключи"]) == sorted(ш["ключи"])), None)
        if скидка and сумма > 0 and (not ш["спец"] or число(ш["спец"]) != итог):
            НАХОДКИ.append(f"{и} при скидке спец. цена «{ш['спец']}», во вкладке «Платежи» {итог}")
        if not скидка and ш["спец"]:
            НАХОДКИ.append(f"{и} без скидки под суммой «{ш['спец']}»")


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                стр, ош = к.начать(СоШрифтами(бр), порт, ш, 900, False)
                стр.evaluate("() => { openPaymentPlan(); switchPPTab('contracts'); }"); стр.wait_for_timeout(400)
                проверить(f"{н} как есть:", стр.evaluate(ВКЛАДКА), False)
                стр.evaluate("() => { const о = document.getElementById('paymentPlanOverlay'); о.style.display = 'none'; }")
                стр.evaluate(СНЯТЬ)
                стр.evaluate("() => { document.getElementById('discountPctInput').value = '3'; calc(); openPaymentPlan(); switchPPTab('contracts'); }")
                стр.wait_for_timeout(400)
                д = стр.evaluate(ВКЛАДКА)
                if not any(с_["бледный"] for с_ in д["строки"]):
                    НАХОДКИ.append(f"{н} база отделки снята, а бледных разделов нет")
                проверить(f"{н} база отделки снята, скидка 3 %:", д, True)
                блок = стр.locator("#paymentPlanBody .pp-cm-block").nth(1)
                блок.scroll_into_view_if_needed(); стр.wait_for_timeout(200)
                стр.screenshot(path=str(м.СНИМКИ / f"pp-contracts-zero-{ш}.png"))
                for о in [о for о in ош if "supabase.co" not in о][:3]:
                    НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: во вкладке «Договоры» у разделов суммы боковой панели, пустые — бледные с «—»; итог договора "
          "под разделами, при скидке — спец. цена из «Платежей»; ничего не обрезано и не слиплось — на 390 и 1440.")


if __name__ == "__main__":
    главная()
