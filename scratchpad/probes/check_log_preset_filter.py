#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий: фильтр по пресету воронкой в строке события.

Константин 26.09.2026, снимком журнала на телефоне: «добавь в правом нижнем
углу кнопку фильтра. Без обрамления. Когда нажимаю — фильтрует все события по
выбранному пресету».

Проба держит на 390 и 1440, в «Бланке» и «Модерне»:
  • воронка есть у каждого события с кодом пресета и только у них;
  • она без рамки и без заливки, в правом нижнем углу строки (правый край
    вровень с правым краем строки на телефоне, по высоте — последняя строка
    текста), и строк от неё не прибавилось; поле нажатия не меньше 40 px;
  • нажатие оставляет только события этого пресета, воронка залита, над
    лентой строка «Только пресет … · Показать все», подпись счёта называет
    пресет;
  • второе нажатие по воронке и «Показать все» возвращают все события;
  • код пресета в серой строке не рвётся переносом («235» / «788»).

    python3 check_log_preset_filter.py
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
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []


def с_(и, вид, минут, код=None, пресет=None):
    д = {"obj": "Хай-тек баня «Виго» 7,7х8,2", "rows": []}
    if код:
        д["presetCode"] = код
    if пресет:
        д["preset"] = пресет
    return {"id": и, "user_id": "u-проба", "event_type": вид, "project_name": "Хай-тек баня «Виго» 7,7х8,2",
            "total_price": 7044020, "options_count": 50, "thickness": 150, "discount": 0,
            "cash_discount": False, "checked_options": {},
            "created_at": f"2026-09-26T{10 + минут // 60:02d}:{минут % 60:02d}:00Z", "details": д}


СОБЫТИЯ = [
    с_(1, "print", 50, "321910", "Хай-тек баня «Виго» 7,7х8,2 · 25.09.26"),
    с_(2, "print", 40, "235788", "D1_Хай-тек баня «Виго» 7,7х8,2 · 24.09.26"),
    с_(3, "share_revoked", 30, "321910", "Хай-тек баня «Виго» 7,7х8,2 · 25.09.26"),
    с_(4, "print", 20),
    с_(5, "share_created", 10, "321910", "Хай-тек баня «Виго» 7,7х8,2 · 25.09.26"),
]
ТАБЛИЦЫ = {
    "events": СОБЫТИЯ,
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
    "preset_links": [], "presets": [],
}

ВИД = """() => {
  const ряды = [...document.querySelectorAll('#alFeed .al-row')];
  return { ряды: ряды.map(р => {
      const к = р.querySelector('.al-pf-btn'), код = р.querySelector('.al-code');
      const т = р.querySelector('.al-text'), в = р.querySelector('.al-top');
      if (!к) return { код: код ? код.dataset.code : null, кнопка: false };
      const кк = к.getBoundingClientRect(), тк = т.getBoundingClientRect(), вк = в.getBoundingClientRect();
      const cs = getComputedStyle(к), bf = getComputedStyle(к, '::before');
      const ctx = р.querySelector('.al-ctx').getBoundingClientRect();
      const кодК = код ? код.getClientRects().length : 0;
      return { код: код ? код.dataset.code : null, кнопка: true, вкл: к.classList.contains('on'), кодРвётся: кодК > 1,
        заливка: к.querySelector('svg').getAttribute('fill'),
        рамка: cs.borderTopWidth + ' ' + cs.backgroundColor,
        справа: Math.round(вк.right - кк.right), снизу: Math.round(тк.bottom - кк.bottom),
        высотаCtx: Math.round(ctx.height),
        поле: Math.round(кк.height - 2 * (parseFloat(bf.top) || 0)) };
    }),
    полоска: (document.querySelector('#alFeed .al-pf-bar') || {}).textContent || '',
    подпись: (document.getElementById('alSub') || {}).textContent || '' };
}"""


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





def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for тема in ("Модерн", "Бланк"):
                for ш in (390, 1440):
                    н = f"[{тема} {ш}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                                        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate("""async ([бланк]) => {
                      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                      _sbProfile = { role: 'admin', full_name: 'Проба' };
                      applyUiStyle(бланк ? 'blank' : 'light', false);
                      openActionLog(); await loadActionLog(true);
                      await new Promise(r => setTimeout(r, 600));
                    }""", [тема == "Бланк"])
                    в0 = стр.evaluate(ВИД)
                    if ш == 390 and тема == "Бланк":
                        print("  " + н, json.dumps(в0, ensure_ascii=False)[:900])
                    ряды = в0["ряды"]
                    if len(ряды) != 5:
                        плохо(н + f" в ленте {len(ряды)} событий вместо пяти"); стр.close(); continue
                    for р in ряды:
                        if bool(р["код"]) != р["кнопка"]:
                            плохо(н + f" событие {р['код']}: воронка {'есть' if р['кнопка'] else 'нет'} вопреки коду")
                        if not р["кнопка"]:
                            continue
                        if not р["рамка"].startswith("0px") or "rgba(0, 0, 0, 0)" not in р["рамка"]:
                            плохо(н + f" у воронки рамка или заливка ({р['рамка']})")
                        if abs(р["снизу"]) > 3:
                            плохо(н + f" воронка не на последней строке текста ({р['снизу']} px)")
                        if ш < 641 and abs(р["справа"]) > 1:
                            плохо(н + f" воронка не у правого края строки ({р['справа']} px)")
                        # Строка с кодом одна и та же с воронкой и без неё: воронка ниже
                        # строки текста не опускается и её не раздвигает.
                        if р["высотаCtx"] > 40:
                            плохо(н + f" строка с кодом выросла до {р['высотаCtx']} px")
                        if р.get("кодРвётся"):
                            плохо(н + f" код {р['код']} разорван переносом строки")
                        if р["поле"] < 40:
                            плохо(н + f" поле нажатия воронки {р['поле']} px")
                    нажата = стр.evaluate("() => { const к = document.querySelector('#alFeed .al-pf-btn[onclick*=\"321910\"]'); if (!к) return false; к.click(); return true; }")
                    if not нажата:
                        плохо(н + " у событий пресета нет воронки — фильтровать нечем"); стр.close(); continue
                    стр.wait_for_timeout(300)
                    в1 = стр.evaluate(ВИД)
                    коды = [р["код"] for р in в1["ряды"]]
                    if коды != ["321910"] * 3:
                        плохо(н + f" после фильтра в ленте {коды}")
                    if not all(р.get("вкл") and р.get("заливка") == "currentColor" for р in в1["ряды"]):
                        плохо(н + " нажатая воронка не залита")
                    if "Показать все" not in в1["полоска"] or "321 910" not in в1["полоска"]:
                        плохо(н + f" над лентой нет строки фильтра ({в1['полоска']!r})")
                    if "321 910" not in в1["подпись"] or "3 события" not in в1["подпись"]:
                        плохо(н + f" подпись счёта не называет пресет ({в1['подпись']!r})")
                    стр.evaluate("() => { const к = document.querySelector('#alFeed .al-pf-btn'); if (к) к.click(); }")
                    стр.wait_for_timeout(300)
                    в2 = стр.evaluate(ВИД)
                    if len(в2["ряды"]) != 5 or в2["полоска"]:
                        плохо(н + " второе нажатие по воронке не вернуло все события")
                    стр.evaluate("() => { const к = document.querySelector('#alFeed .al-pf-btn[onclick*=\"235788\"]'); if (к) к.click(); }")
                    стр.wait_for_timeout(300)
                    стр.evaluate("() => { const к = document.querySelector('#alFeed .al-pf-clear'); if (к) к.click(); }")
                    стр.wait_for_timeout(300)
                    в3 = стр.evaluate(ВИД)
                    if len(в3["ряды"]) != 5:
                        плохо(н + " «Показать все» не вернуло все события")
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"{н} ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: воронка стоит в правом нижнем углу каждого события с пресетом, без рамки и без лишней строки; "
          "нажатие оставляет события пресета и называет его, второе нажатие и «Показать все» возвращают все — "
          "на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
