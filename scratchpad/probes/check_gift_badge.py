#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Метка «В ПОДАРОК» держится у каждой позиции, отмеченной подарком.

Константин 25.09.2026, снимком каркаса: у «Контробрешётки», «Обрешётки» и
«Стропильной системы» кнопка подарка нажата, в печати подарок стоит, а метки
в строке нет. Имена этих позиций зависят от толщины утепления, и calc()
переписывал их через textContent — вместе с меткой. Так же вели себя имена
вариантов (планкен), тип краски и количество в имени.

Проба на 390 и 1440 px, в «Модерне» и «Бланке»:
  • дарит позицию с именем от толщины, позицию с именем от выбора (если есть)
    и простую; метка есть у всех;
  • после calc() и после смены толщины туда и обратно метка на месте, стоит
    ровно одна и имя в строке — текущее имя позиции, без задвоения;
  • снятие подарка убирает метку.

    python3 check_gift_badge.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(где, т):
    НАХОДКИ.append(f"{где}: {т}")


ЗАМЕР = r"""(ид) => {
  const стр = document.getElementById('lbl_' + ид);
  if (!стр) return null;
  const имя = стр.querySelector('.opt-name');
  const оп = OPTIONS.find(о => о.id === ид);
  const текст = имя ? [...имя.childNodes].filter(н => н.nodeType === 3).map(н => н.data).join('').trim() : '';
  const метки = стр.querySelectorAll('.opt-gift-badge');
  const м = метки[0];
  return { меток: метки.length, видна: !!(м && м.getClientRects().length && getComputedStyle(м).display !== 'none'),
           текст, имя: оп ? оп.name : '', кнопка: !!document.querySelector('#gift_' + ид + '.on') };
}"""


def проверить(бр, порт, ш, в, бланк):
    где = f"{'Бланк' if бланк else 'Модерн'} · {ш}px"
    к = бр.new_context(viewport={"width": ш, "height": в})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""(бланк) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      selectProjectOption(0);
    }""", бланк)
    стр.wait_for_timeout(700)
    # Позиции: одна с именем от толщины, одна с именем от варианта, одна простая.
    иды = стр.evaluate("""() => {
      const есть = ид => !!document.querySelector('#gift_' + ид);
      const толщ = Object.keys(BASE_ITEMS_BY_THICKNESS).filter(есть);
      const вар = (typeof ВАРИАНТЫ_ОПЦИЙ !== 'undefined' ? Object.keys(ВАРИАНТЫ_ОПЦИЙ) : []).filter(есть);
      const прост = OPTIONS.map(о => о.id).filter(ид => есть(ид) && !толщ.includes(ид) && !вар.includes(ид));
      return { толщ: толщ.slice(0, 2), вар: вар.slice(0, 1), прост: прост.slice(0, 1) };
    }""")
    все = иды["толщ"] + иды["вар"] + иды["прост"]
    if not иды["толщ"]:
        плохо(где, "на странице нет позиции с именем от толщины — проба ничего не проверила")
    for ид in все:
        стр.evaluate("(ид) => toggleGift(ид, { stopPropagation(){} })", ид)
    стр.wait_for_timeout(300)

    def сверить(шаг):
        for ид in все:
            з = стр.evaluate(ЗАМЕР, ид)
            if not з:
                плохо(где, f"{шаг}: строки {ид} нет"); continue
            if not з["кнопка"] or з["меток"] != 1 or not з["видна"]:
                плохо(где, f"{шаг}: «{з['имя'][:40]}» — кнопка {з['кнопка']}, меток {з['меток']}, видна {з['видна']}")
            if з["текст"] != з["имя"]:
                плохо(где, f"{шаг}: имя в строке «{з['текст'][:50]}» ≠ имени позиции «{з['имя'][:50]}»")

    сверить("сразу после подарка")
    стр.evaluate("() => calc()"); стр.wait_for_timeout(300)
    сверить("после пересчёта")
    for т in (2, 0, 1):
        стр.evaluate(f"() => setThickness({т})"); стр.wait_for_timeout(400)
        сверить(f"после толщины {т}")
    if иды["вар"]:
        стр.evaluate(f"() => setOptVariant('{иды['вар'][0]}', 1)"); стр.wait_for_timeout(300)
        сверить("после смены варианта")
    for ид in все:
        стр.evaluate("(ид) => toggleGift(ид, { stopPropagation(){} })", ид)
    стр.wait_for_timeout(300)
    for ид in все:
        з = стр.evaluate(ЗАМЕР, ид)
        if з and (з["меток"] or з["кнопка"]):
            плохо(где, f"после снятия подарка у {ид} осталась метка или нажатая кнопка")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()
    print(f"  {где}: позиции {все}")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ш, в in ((390, 844), (1440, 900)):
                    try:
                        проверить(бр, порт, ш, в, бланк)
                    except Exception as e:
                        плохо(f"{бланк}/{ш}", f"проба оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: метка «В ПОДАРОК» стоит у каждой подаренной позиции и переживает пересчёт, "
          "смену толщины и варианта; имя в строке не задваивается; снятие подарка убирает метку.")


if __name__ == "__main__":
    главная()
