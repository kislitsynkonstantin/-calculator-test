#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Раздел 14 договора «Адреса и реквизиты» не рвётся: заголовок едет вместе с реквизитами.

Константин 02.10.2026, снимком PDF с телефона: на 16-й странице внизу один
заголовок «14. Адреса и реквизиты» и пустое место, реквизиты и подписи — на
17-й. «Если разрывается, то вот так переноси — чтобы 14 раздел был вместе».

Печатал он с iPhone, то есть WebKit, а WebKit `break-after: avoid` у заголовка
не знает. В контейнере только Chromium, поэтому проба выключает у заголовков
`break-after` — так Chromium ведёт себя как WebKit — и двигает раздел 14 вниз
по листу распоркой от 0 до высоты страницы с шагом 12 px: разрыв страницы
проходит через раздел во всех местах. Держит:
  • заголовок раздела 14 и реквизиты (ОГРН подрядчика) — на одной странице;
  • подписи сторон — на той же странице;
  • то же у договора на отделку;
  • и без подмены (как печатает Chromium сам).

    python3 check_contract_keep14.py
"""
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
import fitz
from playwright.sync_api import sync_playwright

НАХОДКИ = []
КАК_WEBKIT = "h2.section{break-after:auto!important;page-break-after:auto!important}"

РАСПОРКА = """(в) => { const з = [...document.querySelectorAll('h2.section')].find(х => /Адреса и реквизиты/.test(х.textContent));
  const цель = з.parentElement.classList.contains('keep') ? з.parentElement : з;
  let р = document.getElementById('__распорка'); if (!р) { р = document.createElement('div'); р.id = '__распорка'; цель.before(р); }
  р.style.height = в + 'px'; }"""


def страницы(д):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as ф:
        д.pdf(path=ф.name, format="A4", prefer_css_page_size=True, print_background=True)
        док = fitz.open(ф.name)
        return [п.get_text() for п in док]


def где(тексты, образец):
    return [i for i, т in enumerate(тексты) if образец in т.replace("\n", " ")]


def прогнать(кт, html, имя, подмена):
    д = кт.new_page(viewport={"width": 900, "height": 1200})
    д.set_content(html, wait_until="load"); д.wait_for_timeout(800)
    if подмена:
        д.add_style_tag(content=КАК_WEBKIT)
    ошибок = 0
    for в in range(0, 1130, 12):
        д.evaluate(РАСПОРКА, в)
        т = страницы(д)
        з, р, п = где(т, "Адреса и реквизиты"), где(т, "1237700535049"), где(т, "подпись, М.П.")
        if len(з) != 1 or len(р) != 1 or len(п) != 1:
            НАХОДКИ.append(f"[{имя}] распорка {в}: не нашлись метки в PDF — заголовок {з}, ОГРН {р}, подпись {п}"); break
        if not (з[0] == р[0] == п[0]):
            ошибок += 1
            if ошибок <= 2:
                НАХОДКИ.append(f"[{имя}{' как WebKit' if подмена else ''}] распорка {в} px: заголовок на стр. {з[0] + 1}, "
                               f"реквизиты на {р[0] + 1}, подписи на {п[0] + 1}")
    if ошибок > 2:
        НАХОДКИ.append(f"[{имя}{' как WebKit' if подмена else ''}] и ещё {ошибок - 2} положений с разрывом")
    д.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            к, стр, ош = о.начать(бр, порт, 1440, "admin")
            кт = СоШрифтами(бр)
            for ид, имя in ((1, "основной"), (2, "на отделку")):
                html = стр.evaluate("(ид) => сПалитрой(buildContractHtmlKar(getContractVarsKar(ид)))", ид)
                for подмена in (True, False):
                    прогнать(кт, html, имя, подмена)
            к.close(); бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: раздел 14 договора — заголовок, реквизиты и подписи — на одной странице при любом положении "
          "разрыва, у обоих договоров, и с break-after, и без него (как печатает WebKit).")


if __name__ == "__main__":
    главная()
