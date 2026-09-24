#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Межкомнатные двери: количество счётчиком и примечание, которое уходит само.

Константин 24.09.2026:
  1. «когда выбираем межкомнатные двери, то примечание должно активировать
     глаз, что двери не входят»;
  2. «сделай выбор количества межкомнатных дверей, как Flow Vilpe менять
     количество».

Проба нажимает и смотрит на итог, а не на разметку:

  • на карточке дверей есть счётчик; три двери — цена на карточке втрое,
    итог расчёта вырос ровно на две цены двери, в названии «за 3 двери»;
  • отмеченные двери гасят примечание «Межкомнатные двери в базовую
    комплектацию не входят», снятые — возвращают;
  • открытый заново сохранённый расчёт помнит количество: и цену, и название.

    python3 check_doors_qty.py
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
ДВЕРЬ = 21500
ОПЦИИ = [o for o in ДАННЫЕ["pricing_options"] if o["option_id"] != "w15"] + [
    {"product": "frame", "option_id": "w15", "section": "windows",
     "name": "Межкомнатные двери — МДФ (доборы, наличники, ручки), за 1 дверь",
     "included": False, "price": ДВЕРЬ, "formula": None, "status": None, "sort": 50}]
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(ДАННЫЕ, pricing_options=ОПЦИИ), ensure_ascii=False) + ");")
ПРИМЕЧАНИЕ = "Межкомнатные двери в базовую комплектацию не входят"
НАХОДКИ = []


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


ШАГИ = """async ([примечание]) => {
  const пауза = (мс = 250) => new Promise(r => setTimeout(r, мс));
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  selectProjectOption(0); await пауза(800);
  const цифры = т => Number(String(т || '').replace(/\\D/g, '')) || 0;
  const имя = () => (document.querySelector('#lbl_w15 .opt-name') || {}).textContent || '';
  const цена = () => цифры((document.getElementById('optprice_w15') || {}).textContent);
  const строка = () => [...document.querySelectorAll('.note-item')].find(э => (э.innerText || '').includes(примечание.slice(0, 30)));
  const погашена = () => { const с = строка(); return с ? с.classList.contains('note-hidden') : null; };
  const в_ = {};
  в_.счётчик = !!document.querySelector('#lbl_w15 .opt-qty-stepper');
  в_.примечаниеДо = погашена();
  toggleOpt('w15'); await пауза();
  в_.примечаниеПри = погашена();
  const итог1 = _currentTotal;
  changeQty('w15', 1); changeQty('w15', 1); await пауза();
  в_.цена3 = цена(); в_.имя3 = имя(); в_.прирост = _currentTotal - итог1;
  // сохранённый расчёт: снимок, сброс количества, восстановление
  const снимок = JSON.parse(JSON.stringify(collectState()));
  changeQty('w15', -1); changeQty('w15', -1); await пауза();
  в_.цена1 = цена(); в_.имя1 = имя();
  restoreState(снимок); await пауза(800);
  в_.ценаПосле = цена(); в_.имяПосле = имя();
  toggleOpt('w15'); await пауза();
  в_.примечаниеПосле = погашена();
  return в_;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 390, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            if not стр.evaluate("() => typeof restoreState === 'function' && typeof collectState === 'function'"):
                плохо("нет restoreState/collectState — проверить открытие расчёта нечем")
            try:
                в = стр.evaluate(ШАГИ, [ПРИМЕЧАНИЕ])
            except Exception as e:
                плохо(f"проба оборвалась: {e!s:.300}")
                в = None
            if в:
                if not в["счётчик"]:
                    плохо("на карточке дверей нет счётчика количества")
                if в["примечаниеДо"] is None:
                    плохо("примечания про двери в разделе нет — проверять нечего")
                elif в["примечаниеДо"] or not в["примечаниеПри"]:
                    плохо(f"примечание: до выбора погашено={в['примечаниеДо']}, при выборе={в['примечаниеПри']}")
                if в["примечаниеПосле"]:
                    плохо("двери сняты, а примечание осталось погашенным")
                if в["цена3"] != 3 * ДВЕРЬ:
                    плохо(f"три двери на карточке стоят {в['цена3']}, ждали {3 * ДВЕРЬ}")
                if в["прирост"] != 2 * ДВЕРЬ:
                    плохо(f"итог вырос на {в['прирост']}, ждали {2 * ДВЕРЬ}")
                if not в["имя3"].rstrip().endswith("за 3 двери"):
                    плохо(f"название при трёх дверях: «{в['имя3']}»")
                if not в["имя1"].rstrip().endswith("за 1 дверь") or в["цена1"] != ДВЕРЬ:
                    плохо(f"одна дверь: «{в['имя1']}», {в['цена1']}")
                if в["ценаПосле"] != 3 * ДВЕРЬ or not в["имяПосле"].rstrip().endswith("за 3 двери"):
                    плохо(f"открытый расчёт забыл количество: «{в['имяПосле']}», {в['ценаПосле']}")
                print(f"  три двери: {в['цена3']} ₽, «…{в['имя3'][-12:]}», итог +{в['прирост']}; "
                      f"после открытия: {в['ценаПосле']} ₽")
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
    print("Чисто: двери считаются счётчиком — цена, итог и название следуют количеству, "
          "открытый расчёт его помнит, а примечание гаснет при выборе и возвращается при снятии.")


if __name__ == "__main__":
    главная()
