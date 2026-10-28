#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Боковая панель на телефоне — высотой по содержимому; у парной — свои строки.

Константин 28.10.2026, снимком панели «Спецификация» у парной на телефоне:
«Боковая панель зачем такая большая». Панель тянулась от шапки до полоски
итога при любом числе разделов, и у парной с её тремя разделами две трети
панели были пустыми. На том же снимке — «Цена за м²» последнего каркаса и
группа «Договор на парную» при договоре, который везде называется «Договор
подряда».

Проба держит на 390 px с сенсорным экраном:
  • у парной панель кончается на последнем разделе — заметно выше полоски
    итога, без прокрутки, а нажатие под ней попадает в страницу, а не в
    прозрачный просвет панели;
  • у каркаса длинный список по-прежнему доходит до полоски и прокручивается;
  • у парной в панели «Цена за м³» — то же число, что в карточке «Параметры
    парной», а не цена за м² каркаса; у каркаса — «Цена за м²»;
  • группа договора у парной — «Договор подряда», и состав, сохранённый со
    старым именем «Договор на парную», берёт новое сам.

    python3 check_sidenav_fit.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_steam_tab as п
from playwright.sync_api import sync_playwright

НАХОДКИ = []
def плохо(т): НАХОДКИ.append(т)

ИЗМЕР = """() => { const п = document.querySelector('#sideNav .side-nav-panel'), и = document.getElementById('sideNavInner');
  const р = п.getBoundingClientRect(), н = document.getElementById('sideNav').getBoundingClientRect();
  const под = document.elementFromPoint(р.left + 20, Math.min(р.bottom + 30, н.bottom - 10));
  const м = document.getElementById('snHeadM2');
  return { низ: Math.round(р.bottom), просветНиз: Math.round(н.bottom),
    прокрутка: и.scrollHeight > и.clientHeight + 1,
    подПанелью: под ? (под.closest('#sideNav') ? 'панель' : 'страница') : null,
    цена: м ? м.textContent.replace(/\\u00a0/g, ' ').trim() : '',
    группы: [...document.querySelectorAll('#sideNav .sn-cgrp, #sideNav .sn-contract, #sideNav .side-nav-group')].map(е => е.textContent.trim()),
    текст: document.getElementById('sideNavInner').innerText }; }"""


def открыть(бр, порт, тех):
    к = бр.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    стр = к.new_page(); ош = []
    стр.on('pageerror', lambda e: ош.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=п.ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(п.м.ЗАГЛУШКА); стр.add_init_script(п.м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    # Сначала каркас с проектом: у его карточки есть цена за м², и парная не должна её унаследовать.
    стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }")
    if тех == 'steam':
        п.в_парную(стр, образец=False)
        стр.evaluate("() => { парнаяПечь('feringer-klassika'); calc(); }")
    стр.evaluate("() => window.scrollTo(0, 400)"); стр.wait_for_timeout(300)
    стр.evaluate("() => openSideNav()"); стр.wait_for_timeout(700)
    return к, стр, ош


def main():
    с, порт = п.м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=п.м.хром())
            к, стр, ош = открыть(бр, порт, 'steam')
            в = стр.evaluate(ИЗМЕР)
            чип = стр.evaluate("() => document.querySelector('#steamM3Chip strong').textContent.replace(/\\u00a0/g, ' ').replace(/\\s?₽$/, '').trim()")
            if в['низ'] > в['просветНиз'] - 150 or в['прокрутка'] or в['подПанелью'] != 'страница':
                плохо(f"парная: панель кончается на {в['низ']} px при просвете до {в['просветНиз']}, прокрутка {в['прокрутка']}, "
                      f"нажатие под ней — {в['подПанелью']}: ждали короткую панель и страницу под ней")
            if в['цена'] != f"Цена за м³ {чип} ₽":
                плохо(f"парная: в панели «{в['цена']}», в карточке цена за м³ {чип} ₽")
            if 'ДОГОВОР ПОДРЯДА' not in в['текст'].upper() or 'НА ПАРНУЮ' in в['текст'].upper():
                плохо(f"парная: группа договора в панели не «Договор подряда»: {в['текст'][:300]!r}")
            стар = стр.evaluate("""() => { contractsConfig[0].name = 'Договор на парную'; проставитьКодыСоставов();
              return contractsConfig[0].name; }""")
            if стар != 'Договор подряда':
                плохо(f"состав со старым именем «Договор на парную» после разбора называется «{стар}»")
            стр.screenshot(path='/tmp/sidenav-fit-steam-390.png')
            if ош:
                плохо(f"парная: ошибки страницы {ош[:2]}")
            к.close()

            к, стр, ош = открыть(бр, порт, 'frame')
            в = стр.evaluate(ИЗМЕР)
            if в['низ'] < в['просветНиз'] - 2 or not в['прокрутка']:
                плохо(f"каркас: панель кончается на {в['низ']} px при просвете до {в['просветНиз']}, прокрутка {в['прокрутка']} — "
                      "длинный список должен доходить до полоски и прокручиваться")
            if not в['цена'].startswith('Цена за м² '):
                плохо(f"каркас: строка цены в панели «{в['цена']}», ждали «Цена за м² …»")
            if ош:
                плохо(f"каркас: ошибки страницы {ош[:2]}")
            к.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: на телефоне панель у парной кончается на своих трёх разделах, нажатие под ней попадает в страницу, "
          "у каркаса список доходит до полоски и прокручивается; у парной «Цена за м³» из карточки и «Договор подряда», "
          "старое имя состава переименовывается само.")


if __name__ == '__main__':
    main()
