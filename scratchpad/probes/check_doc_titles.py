#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шапки трёх документов окна печати — одним шрифтом.

Константин 01.10.2026, снимками шапки спецификации: «в шапке спецификации и
файла визуализации/планировки вот тут шрифт должен быть как в договоре».

Проба на 390 и 1440, в бирюзе и «Зелёном-графите», с настоящими шрифтами,
держит:
  • название спецификации, Приложения № 2 и договора — Unbounded одного
    начертания (700); шрифт действительно лёг — ширина строки в Unbounded
    не совпадает ни с serif, ни с sans-serif;
  • выделенная часть названия у всех трёх — одного цвета (проект с
    выделением, как «Фахверковая баня «Гранада» 7x9»);
  • надзаголовок спецификации и Приложения № 2 — одного цвета;
  • название спецификации не вылезает за лист;
  • лист договора и «Вида и плана» стоит в окне печати по тем же краям, что
    спецификация (01.10.2026: «спецификация на всю ширину, а договор и
    вид/план уже»).

    python3 check_doc_titles.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
# Края листа в окне печати, в координатах окна: спецификация — сам #printDoc,
# договор и приложение — лист внутри своего кадра.
КРАЯ = """(вид) => { const рр = r => [Math.round(r.left), Math.round(r.right)];
  if (вид === 'spec') return рр(document.getElementById('printDoc').getBoundingClientRect());
  const к = document.querySelector(вид === 'contract' ? '#contractPreviewDoc iframe' : '#appxPreviewDoc iframe'); if (!к) return null;
  const л = к.contentDocument.querySelector(вид === 'contract' ? '.page' : '.sheet'); if (!л) return null;
  const r = л.getBoundingClientRect(), f = к.getBoundingClientRect(); return [Math.round(f.left + r.left), Math.round(f.left + r.right)]; }"""
ШАПКА = """(корень) => { const т = корень.querySelector('.bl-title, .title'), е = т && т.querySelector('em, .bl-em'), н = корень.querySelector('.bl-eyebrow, .eyebrow');
  const ок = корень.defaultView || window, кс = т ? ок.getComputedStyle(т) : null;
  // Шрифт лёг: ширина самого названия против той же строки подменным шрифтом.
  const ш = s => { const e = корень.createElement('span'); e.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font-weight:700;font-size:' + кс.fontSize + ';letter-spacing:' + кс.letterSpacing + ';font-family:' + s;
    e.textContent = т.textContent; корень.body.appendChild(e); const w = e.getBoundingClientRect().width; e.remove(); return w; };
  const лист = т && (т.closest('.bl-doc, .sheet, .page') || корень.body).getBoundingClientRect(), r = т && т.getBoundingClientRect();
  return т ? { семья: кс.fontFamily.split(',')[0].replace(/["']/g, '').trim(), вес: кс.fontWeight, выдел: е ? ок.getComputedStyle(е).color : '',
    надзаг: н ? ок.getComputedStyle(н).color : '', лёг: Math.abs(ш(кс.fontFamily) - ш('serif')) > 2 && Math.abs(ш(кс.fontFamily) - ш('sans-serif')) > 2, вылез: r.right > лист.right + 1 } : null; }"""


def прогон(бр, порт, ш, тон):
    н = f"[{ш} {тон}]"
    стр, ош = к.начать(бр, порт, ш, 900, False)
    # Проект с выделенной частью названия, как у бани «Гранада».
    стр.evaluate("(т) => { applyTone(т, false); if (selectedProject) selectedProject[0] = 'Фахверковая баня «Гранада» 7x9'; openPrintPreview(); }", тон); стр.wait_for_timeout(700)
    спец = стр.evaluate(f"() => ({ШАПКА})(document.querySelector('#printDoc').ownerDocument)")
    края = {"spec": стр.evaluate(КРАЯ, "spec")}
    # Договор менеджеру закрыт до согласования спецификации — смотрим ролью администратора.
    стр.evaluate("async () => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'admin' }); setPreviewEntity('contract'); await new Promise(r => setTimeout(r, 900)); }")
    дог = стр.evaluate(f"() => ({ШАПКА})(document.querySelector('#contractPreviewDoc iframe').contentDocument)")
    края["contract"] = стр.evaluate(КРАЯ, "contract")
    стр.evaluate("async () => { setPreviewEntity('appx'); await new Promise(r => setTimeout(r, 400)); await показатьПриложение2(); await new Promise(r => setTimeout(r, 1200)); }")
    прил = стр.evaluate(f"() => {{ const к = document.querySelector('#appxPreviewDoc iframe'); return к ? ({ШАПКА})(к.contentDocument) : null; }}")
    края["appx"] = стр.evaluate(КРАЯ, "appx")
    # Лист договора и «Вида и плана» — во всю ширину окна, как спецификация
    # (01.10.2026: «спецификация на всю ширину, а договор и вид/план уже»).
    for вид in ("contract", "appx"):
        if not края[вид] or any(abs(a - b) > 1 for a, b in zip(края[вид], края["spec"])):
            НАХОДКИ.append(f"{н} лист «{вид}» не во всю ширину окна, как спецификация: {края[вид]} против {края['spec']}")
    for имя, х in (("спецификация", спец), ("договор", дог), ("приложение", прил)):
        if not х:
            НАХОДКИ.append(f"{н} {имя}: шапки нет"); continue
        if х["семья"] != "Unbounded" or х["вес"] != "700" or not х["лёг"]:
            НАХОДКИ.append(f"{н} {имя}: название не Unbounded 700 или шрифт не лёг: {х}")
        if х["вылез"]:
            НАХОДКИ.append(f"{н} {имя}: название вылезает за лист")
    if спец and дог and прил and not (дог["выдел"] == прил["выдел"] and спец["выдел"] in ("", дог["выдел"])):
        НАХОДКИ.append(f"{н} выделенная часть названия разного цвета: спецификация {спец['выдел']}, договор {дог['выдел']}, приложение {прил['выдел']}")
    if спец and прил and спец["надзаг"] != прил["надзаг"]:
        НАХОДКИ.append(f"{н} надзаголовок разного цвета: спецификация {спец['надзаг']}, приложение {прил['надзаг']}")
    if ш == 1440 and тон == "bmsk":
        стр.evaluate("() => setPreviewEntity('spec')"); стр.wait_for_timeout(500)
        стр.screenshot(path=str(м.СНИМКИ / "doc-titles-spec-1440.png"))
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тон in ("teal", "bmsk"):
                    прогон(СоШрифтами(бр), порт, ш, тон)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: названия спецификации, Приложения № 2 и договора — Unbounded 700, шрифт лёг, выделение и надзаголовок "
          "одного цвета, название в пределах листа — на 390 и 1440, в бирюзе и «Зелёном-графите».")


if __name__ == "__main__":
    главная()
