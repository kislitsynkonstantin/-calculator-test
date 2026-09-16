#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба строки «Ссылка клиенту» в панели печати и окна уведомлений.

Держит то, что задано 16.09.2026:
  • «Скопировать ссылку» стоит в строке заголовка полосы, а не на панели;
  • строка заголовка разворачивается только птичкой — промах по кнопке
    копирования блок не открывает;
  • «Печать / PDF» стоит в левой группе верхней строки и ни при какой
    ширине не остаётся одна во втором ряду;
  • подпись о заходах написана без слова «клиент»;
  • в окне уведомлений нет подписи «позже здесь появятся…», и каждое
    открытие ссылки — своя строка.

И то, что задано раньше и легко теряется при перестановке:
  • поле нажатия 44 px при маленькой коробке;
  • зазор до линейки и до соседей — ни склейки, ни повисания в пустоте;
  • никакого горизонтального переполнения.
"""
import json
import pathlib
import subprocess
import sys
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent.parent
ХРОМ = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")

ОКНА = [("телефон", 390, 844), ("телефон лёжа", 844, 390),
        ("планшет", 768, 1024), ("стол", 1440, 900)]

НАХОДКИ = []


def плохо(окно, текст):
    НАХОДКИ.append(f"[{окно}] {текст}")


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ПОДГОТОВКА = """() => {
  _sbUser = { id: 'u-проба' };
  _ссылкаКлиента = {
    code: 'adkv8q5j', revoked: false,
    created_at: '2026-09-10T09:00:00Z', snapshot_at: '2026-09-16T10:00:00Z',
    snapshot: {},
  };
  _заходыКлиента = [
    { seen_at: '2026-09-16T14:22:00Z', version_at: '2026-09-16T10:00:00Z' },
    { seen_at: '2026-09-15T18:03:00Z', version_at: '2026-09-16T10:00:00Z' },
    { seen_at: '2026-09-15T11:40:00Z', version_at: '2026-09-12T08:00:00Z' },
  ];
  // Каталог цен живёт в базе, до неё пробе не дойти — экран ошибки поверх
  // страницы перехватывал бы нажатия.
  const беда = document.getElementById('pricingErrorScreen');
  if (беда) беда.style.display = 'none';
  document.getElementById('printOverlay').style.display = 'block';
  переключитьПолосуСсылки(false);
  нарисоватьПолосуСсылки();
}"""

КОЛОКОЛЬЧИК = """() => {
  _уведомления = [
    { вид: 'открыл', когда: '2026-09-16T14:22:00Z', текст: 'Спецификацию «Баня 6×4» открыли по ссылке' },
    { вид: 'открыл', когда: '2026-09-15T18:03:00Z', текст: 'Спецификацию «Баня 6×4» открыли по ссылке' },
    { вид: 'открыл', когда: '2026-09-15T11:40:00Z', текст: 'Спецификацию «Баня 6×4» открыли по ссылке — <b>прежнюю версию</b>' },
  ];
  поставитьОкноУведомлений();
  document.getElementById('bellMenu').style.display = 'block';
  нарисоватьУведомления();
}"""

МЕРА = """() => {
  const кор = э => { const r = э.getBoundingClientRect();
    return { л: r.left, п: r.right, в: r.top, н: r.bottom, ш: r.width, вы: r.height }; };
  const полоса = document.getElementById('clientLinkBar');
  const голова = полоса.querySelector('.cl-head');
  const копия  = полоса.querySelector('.cl-copy');
  const птичка = полоса.querySelector('.cl-arrow');
  const поле = э => {
    const с = getComputedStyle(э, '::before');
    const чис = з => parseFloat(з) || 0;
    const r = э.getBoundingClientRect();
    if (с.content === 'none') return { ш: r.width, вы: r.height };
    return { ш: r.width - чис(с.left) - чис(с.right), вы: r.height - чис(с.top) - чис(с.bottom) };
  };
  const панель = document.getElementById('printToolbar');
  const верх = панель.firstElementChild;
  const печать = document.getElementById('printDocBtn');
  const строки = {};
  [...верх.children].filter(э => э.getClientRects().length).forEach(э => {
    const r = э.getBoundingClientRect();
    const к = Math.round(r.top / 4) * 4;
    (строки[к] = строки[к] || []).push(э.id || э.className || э.tagName);
  });
  const пр = печать.getBoundingClientRect();
  const мойРяд = Object.entries(строки)
    .find(([к]) => Math.abs(+к - Math.round(пр.top / 4) * 4) < 1);
  return {
    естьСтараяКнопка: !!document.getElementById('clientLinkBtn'),
    естьПодписьНизаУведомлений: !!document.querySelector('#bellMenu .nt-f'),
    подпись: полоса.querySelector('.cl-sub').textContent,
    текстКопии: копия ? копия.textContent.trim() : null,
    голова: кор(голова), копия: кор(копия), птичка: кор(птичка),
    полеКопии: поле(копия), полеПтички: поле(птичка),
    рульГоловы: голова.getBoundingClientRect().bottom,
    панельШ: панель.getBoundingClientRect().width,
    печатьРяд: мойРяд ? мойРяд[1] : [],
    печатьКор: кор(печать),
    строкиВерха: Object.keys(строки).length,
    переполнение: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    ошибкиРазметки: [...полоса.querySelectorAll('.cl-head > *')].map(э => ({
      кто: э.className || э.tagName, авто: getComputedStyle(э).marginLeft === 'auto',
    })),
    соседи: (() => {
      const дети = [...голова.children].filter(э => э.getClientRects().length);
      const к = голова.getBoundingClientRect();
      return дети.map(э => {
        const r = э.getBoundingClientRect();
        const свои = дети.filter(д => д !== э && Math.abs(д.getBoundingClientRect().top - r.top) < 6);
        const слева = свои.filter(д => д.getBoundingClientRect().right <= r.left + 1)
          .map(д => r.left - д.getBoundingClientRect().right);
        const справа = свои.filter(д => д.getBoundingClientRect().left >= r.right - 1)
          .map(д => д.getBoundingClientRect().left - r.right);
        const все = [...слева, ...справа, r.left - к.left, к.right - r.right];
        return { кто: э.className || э.tagName, ближайший: Math.min(...все) };
      });
    })(),
  };
}"""


def проверить(страница, окно, ш, в):
    страница.set_viewport_size({"width": ш, "height": в})
    страница.evaluate(ПОДГОТОВКА)
    страница.wait_for_timeout(500)
    д = страница.evaluate(МЕРА)

    if д["естьСтараяКнопка"]:
        плохо(окно, "прежняя кнопка «Ссылка клиенту» осталась на панели")
    if д["текстКопии"] != "Скопировать ссылку":
        плохо(окно, f"кнопка в строке заголовка названа {д['текстКопии']!r}, а не «Скопировать ссылку»")
    if "клиент" in д["подпись"].lower():
        плохо(окно, f"в подписи о заходах осталось слово «клиент»: {д['подпись']!r}")
    if "открыли" not in д["подпись"]:
        плохо(окно, f"подпись о заходах не говорит, что ссылку открывали: {д['подпись']!r}")
    if "3 раза" not in д["подпись"]:
        плохо(окно, f"подпись не показывает общее число заходов: {д['подпись']!r}")

    # Поле нажатия — 44 px, коробка при этом лёгкая.
    if д["полеКопии"]["вы"] < 43.5:
        плохо(окно, f"поле нажатия «Скопировать ссылку» {д['полеКопии']['вы']:.0f} px по высоте, нужно 44")
    if д["копия"]["вы"] > 34:
        плохо(окно, f"кнопка копирования нарисована {д['копия']['вы']:.0f} px — вес оплачен размером")
    if д["полеПтички"]["вы"] < 43.5 or д["полеПтички"]["ш"] < 43.5:
        плохо(окно, f"поле нажатия птички {д['полеПтички']['ш']:.0f}×{д['полеПтички']['вы']:.0f}, нужно 44×44")

    # Зазор до линейки под строкой заголовка.
    зазор = д["рульГоловы"] - д["копия"]["н"]
    if зазор < 6:
        плохо(окно, f"кнопка копирования в {зазор:.0f} px от линейки под заголовком — склеилась с ней")

    # «Элемент стоит рядом с чем-то»: ни один в строке не повисает в пустоте.
    for э in д["соседи"]:
        if э["ближайший"] > 26:
            плохо(окно, f"{э['кто']} в строке заголовка стоит в {э['ближайший']:.0f} px от всего — повис в пустоте")

    # Два margin-left:auto в одной строке — тот самый код-признак.
    авто = [э["кто"] for э in д["ошибкиРазметки"] if э["авто"]]
    if len(авто) > 1:
        плохо(окно, f"в строке заголовка два margin-left:auto: {авто}")

    # «Печать / PDF» — не одна во втором ряду.
    if len(д["печатьРяд"]) < 2:
        плохо(окно, f"«Печать / PDF» стоит в ряду одна: {д['печатьРяд']}")

    if д["переполнение"] > 1:
        плохо(окно, f"горизонтальное переполнение страницы {д['переполнение']} px")

    # Разворот — только птичкой.
    страница.evaluate("() => переключитьПолосуСсылки(false)")
    страница.evaluate("""() => {
      const г = document.querySelector('#clientLinkBar .cl-head');
      const r = г.getBoundingClientRect();
      г.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + 4, clientY: r.top + 4 }));
    }""")
    страница.wait_for_timeout(120)
    if страница.evaluate("() => document.getElementById('clientLinkBar').classList.contains('open')"):
        плохо(окно, "нажатие по строке заголовка развернуло блок — должна только птичка")
    страница.click("#clientLinkBar .cl-arrow")
    страница.wait_for_timeout(400)
    if not страница.evaluate("() => document.getElementById('clientLinkBar').classList.contains('open')"):
        плохо(окно, "птичка не развернула блок")

    # Окно уведомлений: подписи под списком нет, каждое открытие своей строкой.
    страница.evaluate("() => { document.getElementById('printOverlay').style.display='none'; }")
    страница.evaluate(КОЛОКОЛЬЧИК)
    страница.wait_for_timeout(200)
    у = страница.evaluate("""() => ({
      подпись: !!document.querySelector('#bellMenu .nt-f'),
      строк: document.querySelectorAll('#bellMenu .nt-i').length,
      текст: document.getElementById('bellMenu').textContent,
      низ: (() => { const с=[...document.querySelectorAll('#bellMenu .nt-i')].pop();
        if(!с) return null; const м=document.getElementById('bellMenu').getBoundingClientRect();
        return { рамка: getComputedStyle(с).borderBottomWidth,
                 доНиза: м.bottom - с.getBoundingClientRect().bottom }; })(),
    })""")
    if у["подпись"]:
        плохо(окно, "в окне уведомлений осталась подпись «позже здесь появятся…»")
    if у["строк"] != 3:
        плохо(окно, f"в окне уведомлений {у['строк']} строк на три открытия — открытия склеены")
    if у["низ"] and у["низ"]["рамка"] not in ("0px", ""):
        плохо(окно, "последняя строка уведомлений отчёркнута линейкой в край окна")
    страница.evaluate("() => { document.getElementById('bellMenu').style.display='none'; }")

    снимок = pathlib.Path(__file__).parent / f"снимок-{окно.replace(' ', '-')}.png"
    страница.evaluate("() => { document.getElementById('printOverlay').style.display='block'; }")
    страница.wait_for_timeout(150)
    страница.locator("#printToolbar").screenshot(path=str(снимок))


def главная():
    с, порт = сервер()
    ошибки = []
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
        стр = бр.new_page()
        стр.add_init_script(ЗАГЛУШКА)
        стр.on("console", lambda с: ошибки.append(с.text) if с.type == "error" else None)
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
        стр.wait_for_timeout(1500)
        for имя, ш, в in ОКНА:
            проверить(стр, имя, ш, в)
        бр.close()
    с.shutdown()

    важные = [о for о in ошибки if "favicon" not in о and "jsdelivr" not in о]
    if важные:
        print("Ошибки в консоли (первые пять):")
        for о in важные[:5]:
            print("   ", о[:200])
    if НАХОДКИ:
        print("\nНАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("\nЧисто: строка заголовка, «Печать / PDF», подпись и уведомления — все четыре окна.")


if __name__ == "__main__":
    главная()
