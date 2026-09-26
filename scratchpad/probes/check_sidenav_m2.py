#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цена за м² в боковой панели — в ряду со «птичкой».

Константин 26.09.2026, снимком панели «Спецификация» на телефоне: «цена за м2
сюда вынеси — на одной строке с птичкой, чтобы не увеличивать количество
строк».

Проба держит в «Бланке» на 390 и 1440:
  • в ряду со «птичкой» стоит «Цена за м²» и то же число, что в строке
    параметров проекта, — не пересчитанное отдельно;
  • подпись и «птичка» на одной высоте, ряд не вырос: его высота та же, что
    без цены (строк не прибавилось);
  • цена у левого края ряда, «птичка» у правого, между ними не меньше 8 px;
  • настройка «Показывать цену за м²» выключена — в ряду остаётся одна
    «птичка», без пустого места;
  • нажатие по ряду по-прежнему сворачивает переходы по странице.

    python3 check_sidenav_m2.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

ТАБЛИЦЫ_JS = (
    "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};"
    "window.__ТАБЛИЦЫ.pricing_projects = [1,2].map(и => ({"
    "  product: 'frame', sort: и, slug: 'Проба ' + и, name: 'Проба ' + и,"
    "  price_100: 1000000, price_150: 1200000, price_200: 1400000,"
    "  floors: 1, roof_type: 'двускатная', warm: true,"
    "  open_area: 10, closed_area: 20, facade_area: 60,"
    "  paint_area: 60, roof_area: 40 }));")


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)



ВИД = """async (показывать) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  appSettings.showPricePerM2 = показывать;
  calc(); await ждать(250);
  const ряд = document.querySelector('.sn-grp-page');
  const верх = ряд && ряд.querySelector('.sn-grp-top');
  const м2 = document.getElementById('snHeadM2');
  const птичка = ряд && ряд.querySelector('.sn-chev');
  const чип = document.getElementById('pricePerM2Chip');
  const числоЧипа = чип && чип.style.display !== 'none' ? (чип.querySelector('strong')?.textContent || '').trim() : '';
  const р = ряд ? ряд.getBoundingClientRect() : null, в = верх ? верх.getBoundingClientRect() : null;
  const м = м2 ? м2.getBoundingClientRect() : null, п = птичка ? птичка.getBoundingClientRect() : null;
  return {
    есть: !!м2, текст: м2 ? (м2.textContent || '').trim() : null, числоЧипа,
    виден: !!(м && м.width > 0),
    высотаВерха: в ? Math.round(в.height * 10) / 10 : null,
    середины: (м && п && м.width) ? Math.abs((м.top + м.bottom) / 2 - (п.top + п.bottom) / 2) : null,
    слева: (м && р && м.width) ? Math.round(м.left - р.left) : null,
    зазор: (м && п && м.width) ? Math.round(п.left - м.right) : null,
    вРяду: (м && р && м.width) ? (м.top >= р.top - 1 && м.bottom <= р.bottom + 1) : null,
  };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                стр = бр.new_page(viewport={"width": ш, "height": 950})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("""async () => {
                  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                  applyUiStyle('blank', false);
                  const и = PROJECTS.findIndex(x => x && x[0] && x[6] > 0);
                  selectProjectOption(и >= 0 ? и : 0);
                  await new Promise(r => setTimeout(r, 1000));
                  if (typeof appSettings !== 'undefined') appSettings.sideNavPageCollapsed = false;
                  if (typeof openSideNav === 'function') openSideNav();
                  await new Promise(r => setTimeout(r, 500));
                }""")
                н = f"[{ш}px]"
                вкл = стр.evaluate(ВИД, True)
                выкл = стр.evaluate(ВИД, False)
                print("  " + н, json.dumps({"вкл": вкл, "выкл": выкл}, ensure_ascii=False))
                if not вкл["есть"]:
                    плохо(н + " в ряду со «птичкой» нет места для цены за м²")
                else:
                    if not вкл["числоЧипа"]:
                        плохо(н + " в строке параметров проекта нет цены за м² — сравнивать не с чем")
                    elif вкл["числоЧипа"] not in (вкл["текст"] or "") or "Цена за м²" not in (вкл["текст"] or ""):
                        плохо(н + f" в панели «{вкл['текст']}», а в параметрах проекта {вкл['числоЧипа']}")
                    if not вкл["виден"] or not вкл["вРяду"]:
                        плохо(н + " цена за м² не видна в ряду со «птичкой»")
                    if вкл["середины"] is not None and вкл["середины"] > 2:
                        плохо(н + f" цена и «птичка» на разной высоте ({round(вкл['середины'], 1)} px)")
                    if вкл["слева"] is not None and вкл["слева"] > 26:
                        плохо(н + f" цена висит в {вкл['слева']} px от левого края ряда")
                    if вкл["зазор"] is not None and вкл["зазор"] < 8:
                        плохо(н + f" цена подходит к «птичке» на {вкл['зазор']} px")
                    if вкл["высотаВерха"] and выкл["высотаВерха"] and вкл["высотаВерха"] > выкл["высотаВерха"] + 1:
                        плохо(н + f" ряд вырос с ценой: {выкл['высотаВерха']} → {вкл['высотаВерха']} px")
                    if выкл["виден"] or (выкл["текст"] or ""):
                        плохо(н + f" настройка выключена, а в ряду «{выкл['текст']}»")
                свёрнут = стр.evaluate("""() => { const р = document.querySelector('.sn-grp-page'); р.click();
                  const да = р.classList.contains('collapsed'); р.click(); return да; }""")
                if not свёрнут:
                    плохо(н + " нажатие по ряду больше не сворачивает переходы по странице")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    печать()


def печать():
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: цена за м² стоит в ряду со «птичкой», то же число, что в параметрах проекта, ряд не вырос, "
          "без настройки её нет, а ряд по-прежнему сворачивает переходы — на 390 и 1440.")


if __name__ == "__main__":
    главная()
