#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Дровяная печь закрывает электрические.

Константин 24.09.2026: «добавь автоматизацию: если выбрана дровяная печь, то
блокируются для выбора эти 2 электрические» — угловая Harvia Glow Corner
TRC 90 и подвесная Sawo Cumulus CML-60NB-P. Третья электрическая, Sawo с
выносным пультом, закрыта тем же правилом.

Проба нажимает, а не читает правила:

  • отмеченная электрическая печь снимается, как только выбрана дровяная;
  • пока дровяная стоит, все три электрические закрыты и нажатие по ним
    галочку не ставит;
  • снятая дровяная открывает их снова;
  • правило одностороннее: электрическая дровяные не закрывает.

    python3 check_stove_electric.py
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
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
НАХОДКИ = []

ПЕЧИ = [("st3", "Угловая печь для сауны Harvia Glow Corner TRC 90, 9 кВт"),
        ("st4", "Подвесная электрическая печь Sawo Cumulus CML-60NB-P 6 кВт"),
        ("st5", "Подвесная электрическая печь Sawo Cumulus CML-60Ni2-P с выносным пультом (талькохлорит)"),
        ("st16", "Печь-каменка Ферингер Малютка до 18 м³"),
        ("st18", "Печь Ферингер Оптима до 28 м³")]
ЭЛЕКТРО = ["st3", "st4", "st5"]
ОПЦИИ = ДАННЫЕ["pricing_options"] + [
    {"product": "frame", "option_id": к, "name": и, "section": "stove", "included": False,
     "price": 60000 + н * 1000, "formula": None, "status": None, "sort": 100 + н}
    for н, (к, и) in enumerate(ПЕЧИ)]
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(ДАННЫЕ, pricing_options=ОПЦИИ), ensure_ascii=False) + ");")


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


СОСТОЯНИЕ = """(ид) => Object.fromEntries(ид.map(и => {
  const л = document.getElementById('lbl_' + и);
  return [и, { есть: !!л, отмечена: !!checkedOptions[и], закрыта: !!(л && л.dataset.blocked === '1') }];
}))"""


def главная():
    с, порт = сервер()
    все = [к for к, _ in ПЕЧИ]
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("""async () => {
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              selectProjectOption(0); await new Promise(r => setTimeout(r, 800));
            }""")
            нажать = lambda и: стр.evaluate("(и) => toggleOpt(и)", и)

            с0 = стр.evaluate(СОСТОЯНИЕ, все)
            нет = [и for и in все if not с0[и]["есть"]]
            if нет:
                плохо(f"печей нет в разделе: {нет} — проба идёт вхолостую")
            else:
                # 1. электрическая, потом дровяная — электрическая снимается
                нажать("st3")
                if not стр.evaluate(СОСТОЯНИЕ, все)["st3"]["отмечена"]:
                    плохо("электрическую печь не удалось отметить до дровяной")
                нажать("st16")
                с1 = стр.evaluate(СОСТОЯНИЕ, все)
                if с1["st3"]["отмечена"]:
                    плохо("выбрана дровяная, а электрическая Harvia осталась отмеченной")
                for и in ЭЛЕКТРО:
                    if not с1[и]["закрыта"]:
                        плохо(f"при дровяной печи электрическая {и} не закрыта")
                # 2. нажатие по закрытой — галочки нет
                нажать("st4")
                if стр.evaluate(СОСТОЯНИЕ, все)["st4"]["отмечена"]:
                    плохо("закрытую электрическую Sawo удалось отметить нажатием")
                # 3. сняли дровяную — электрические открыты
                стр.evaluate("() => спрятатьЗапрет && спрятатьЗапрет()")
                нажать("st16")
                с3 = стр.evaluate(СОСТОЯНИЕ, все)
                for и in ЭЛЕКТРО:
                    if с3[и]["закрыта"]:
                        плохо(f"дровяная снята, а электрическая {и} осталась закрытой")
                # 4. другая дровяная закрывает так же
                нажать("st18")
                if not all(стр.evaluate(СОСТОЯНИЕ, все)[и]["закрыта"] for и in ЭЛЕКТРО):
                    плохо("печь Оптима не закрывает электрические")
                нажать("st18")
                # 5. в обратную сторону правила нет
                нажать("st4")
                с5 = стр.evaluate(СОСТОЯНИЕ, все)
                if с5["st16"]["закрыта"] or с5["st18"]["закрыта"]:
                    плохо("электрическая печь закрыла дровяные — правило должно быть в одну сторону")
                print(f"  дровяная → электрические: {[с1[и]['закрыта'] for и in ЭЛЕКТРО]}; "
                      f"после снятия: {[с3[и]['закрыта'] for и in ЭЛЕКТРО]}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: дровяная печь снимает и закрывает все три электрические, снятая — "
          "открывает их, а электрическая дровяные не закрывает.")


if __name__ == "__main__":
    главная()
