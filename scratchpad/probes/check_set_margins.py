#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Комплект договора — спецификация, договор, Приложение № 2 — с одними полями.

Константин 01.10.2026, снимками «Вида и плана» и договора с телефона: «слева
сделай одинаковый отступ для переплёта сразу… а справа можно меньше сделать.
И чтобы 3 документа были с одинаковыми отступами, так как это комплект
договора». Поля по ГОСТ Р 7.0.97-2016: левое 20 мм, правое 10 мм, верхнее и
нижнее 20 мм.

Проба на 390, 768 и 1440, с настоящими шрифтами, держит:
  • на экране текст трёх документов начинается и кончается на одних и тех же
    вертикалях окна печати (±1 px), и левое поле больше правого;
  • в печати у всех трёх правило @page — 20 мм 10 мм 20 мм 20 мм, а сам лист
    своих полей не добавляет (иначе на бумаге поля разойдутся, хотя @page один);
  • в Word поля страницы те же: 20 / 10 / 20 / 20 мм.

    python3 check_set_margins.py
"""
import pathlib, re, sys, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЗДЕСЬ = pathlib.Path(__file__).parent

# Края текста в координатах окна: спецификация — блок .bl-doc, договор и
# приложение — содержимое листа (край листа плюс его внутреннее поле).
КРАЯ = """(вид) => {
  if (вид === 'spec') { const r = document.querySelector('#printDoc .bl-doc').getBoundingClientRect(),
      о = document.getElementById('printDoc').getBoundingClientRect(); return { л: r.left, п: r.right, лл: о.left, пп: о.right }; }
  const к = document.querySelector(вид === 'contract' ? '#contractPreviewDoc iframe' : '#appxPreviewDoc iframe'); if (!к) return null;
  const д = к.contentDocument, л = д.querySelector(вид === 'contract' ? '.page' : '.sheet'); if (!л) return null;
  const r = л.getBoundingClientRect(), f = к.getBoundingClientRect(), с = д.defaultView.getComputedStyle(л);
  return { л: f.left + r.left + parseFloat(с.paddingLeft), п: f.left + r.right - parseFloat(с.paddingRight), лл: f.left + r.left, пп: f.left + r.right }; }"""

# Правила @page документа и поля самого листа в печати.
ПЕЧАТЬ = """(сел) => { const поля = [];
  // @page бывает и внутри @media print — обходим вложенные правила.
  const обход = пр => { for (const п of пр) { if (п.type === CSSRule.PAGE_RULE && п.style.marginLeft) поля.push([п.style.marginTop, п.style.marginRight, п.style.marginBottom, п.style.marginLeft].join(' '));
    else if (п.cssRules) обход(п.cssRules); } };
  for (const лист of document.styleSheets) { let пр; try { пр = лист.cssRules; } catch (e) { continue; } обход(пр); }
  const л = document.querySelector(сел), с = л ? getComputedStyle(л) : null;
  return { поля, лист: с ? [с.paddingTop, с.paddingRight, с.paddingLeft, с.marginLeft, с.marginRight].join(' ') : null }; }"""

ЖДЁМ = "20mm 10mm 20mm 20mm"


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            кт = СоШрифтами(бр)
            for ш in (390, 768, 1440):
                стр, ош = к.начать(кт, порт, ш, 900, False)
                # Договор менеджеру закрыт до согласования спецификации — ролью администратора.
                стр.evaluate("() => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'admin' }); applyTone('bmsk', false); openPrintPreview(); }"); стр.wait_for_timeout(800)
                края = {"spec": стр.evaluate(КРАЯ, "spec")}
                for вид in ("contract", "appx"):
                    стр.evaluate(f"async () => {{ setPreviewEntity('{вид}'); await new Promise(r => setTimeout(r, 1500)); }}")
                    края[вид] = стр.evaluate(КРАЯ, вид)
                н = f"[{ш}]"
                if not all(края.values()):
                    НАХОДКИ.append(f"{н} не найден лист: {края}"); стр.close(); continue
                с0 = края["spec"]
                for вид in ("contract", "appx"):
                    к_ = края[вид]
                    if abs(к_["л"] - с0["л"]) > 1 or abs(к_["п"] - с0["п"]) > 1:
                        НАХОДКИ.append(f"{н} текст «{вид}» не по краям спецификации: слева {к_['л']:.0f} / {с0['л']:.0f}, справа {к_['п']:.0f} / {с0['п']:.0f}")
                for вид, к_ in края.items():
                    лев, пр = к_["л"] - к_["лл"], к_["пп"] - к_["п"]
                    if not лев > пр:
                        НАХОДКИ.append(f"{н} «{вид}»: левое поле {лев:.0f} px не больше правого {пр:.0f} px")
                # Печать: те же правила @page, лист без своих полей.
                if ш == 1440:
                    стр.emulate_media(media="print"); стр.wait_for_timeout(300)
                    for вид, сел, кадр in (("contract", ".page", "#contractPreviewDoc iframe"), ("appx", ".sheet", "#appxPreviewDoc iframe")):
                        стр.evaluate(f"async () => {{ setPreviewEntity('{вид}'); await new Promise(r => setTimeout(r, 1500)); }}")
                        р = стр.frame_locator(кадр).locator("body").evaluate(f"(б) => ({ПЕЧАТЬ})('{сел}')")
                        if ЖДЁМ not in р["поля"]:
                            НАХОДКИ.append(f"[печать {вид}] @page не {ЖДЁМ}: {р['поля']}")
                        if not р["лист"] or any(х not in ("0px",) for х in р["лист"].split()):
                            НАХОДКИ.append(f"[печать {вид}] лист добавляет свои поля: {р['лист']}")
                    стр.evaluate("async () => { setPreviewEntity('spec'); await new Promise(r => setTimeout(r, 500)); }")
                    р = стр.evaluate(f"() => ({ПЕЧАТЬ})('#printDoc .bl-doc')")
                    if ЖДЁМ not in р["поля"]:
                        НАХОДКИ.append(f"[печать спецификация] @page не {ЖДЁМ}: {р['поля']}")
                    if not р["лист"] or any(х != "0px" for х in р["лист"].split()):
                        НАХОДКИ.append(f"[печать спецификация] лист добавляет свои поля: {р['лист']}")
                    стр.emulate_media(media="screen")
                for о in [о for о in ош if "supabase.co" not in о][:2]:
                    НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    # Word: поля страницы в разметке документа — из кода выгрузки.
    код = (pathlib.Path(м.КОРЕНЬ) / "index.html").read_text(encoding="utf-8") if hasattr(м, "КОРЕНЬ") else None
    if код is not None and "margin: { top: мм(20), right: мм(10), bottom: мм(20), left: мм(20) }" not in код:
        НАХОДКИ.append("Word: поля страницы не 20 / 10 / 20 / 20 мм")
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: спецификация, договор и Приложение № 2 — одни поля: на экране текст по одним краям, левое поле "
          "больше правого; в печати @page 20 / 10 / 20 / 20 мм и лист без своих полей — на 390, 768 и 1440.")


if __name__ == "__main__":
    главная()
