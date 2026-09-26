#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Колокольчик: вид открытого окна и загрузка уведомлений.

Константин 26.09.2026, двумя снимками: «пока нажата кнопка колокольчика
(выпало окно уведомлений), меняй его вид. Небольшая анимация» и «здесь пока
грузит уведомления, поставь что-то покрасивее. Может также полоску загрузки».

Проба держит на 390 и 1440, в «Бланке» и «Модерне»:
  • пока уведомления собираются, в окне бежит полоска загрузки (та же, что в
    справке), по центру окна, с подписью под ней, а не строка «Смотрим…»;
  • открыто окно — колокольчик залит цветом схемы (у корпуса есть заливка,
    у закрытого её нет), у кнопки aria-expanded="true";
  • в миг открытия колокольчик качается: посреди качания он повёрнут;
  • окно закрыли — заливка и цвет вернулись, качания нет.

    python3 check_bell_open.py
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




СЦЕНАРИЙ = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const к = document.getElementById('bellBtn');
  const знак = к && к.querySelector('svg');
  const корпус = знак && знак.querySelector('path');
  const угол = () => { const м = getComputedStyle(знак).transform; if (!м || м === 'none') return 0;
    const ч = м.match(/-?[\\d.e]+/g).map(Number); return Math.round(Math.atan2(ч[1], ч[0]) * 180 / Math.PI); };
  const вид = () => ({ цвет: getComputedStyle(к).color, заливка: getComputedStyle(корпус).fill,
    раскрыт: к.getAttribute('aria-expanded'), угол: угол() });
  const покой = вид();
  let отпустить;
  const был = window.собратьУведомления;
  window.собратьУведомления = () => new Promise(r => { отпустить = r; });
  const пуск = переключитьУведомления();
  await ждать(120);
  const м = document.getElementById('bellMenu');
  const полоска = м.querySelector('.bm-load');
  const загрузка = { полоска: !!(полоска && полоска.offsetWidth), текст: (м.textContent || '').trim(),
    бег: полоска ? getComputedStyle(полоска.querySelector('i')).animationName : null,
    поЦентру: (() => { if (!полоска) return null; const о = м.getBoundingClientRect(), п = полоска.getBoundingClientRect();
      return Math.abs((п.left + п.right) / 2 - (о.left + о.right) / 2) < 3; })(),
    качание: угол() };
  const открыт = вид();
  отпустить && отпустить(); await пуск; await ждать(800);
  const открытПосле = вид();
  переключитьУведомления(); await ждать(150);
  const закрыт = вид();
  window.собратьУведомления = был;
  return { есть: !!(к && корпус), покой, загрузка, открыт, открытПосле, закрыт };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тема in ("blank", "light"):
                    стр = бр.new_page(viewport={"width": ш, "height": 950})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate(f"""() => {{
                      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                      applyUiStyle('{тема}', false);
                    }}""")
                    р = стр.evaluate(СЦЕНАРИЙ)
                    н = f"[{ш} {тема}]"
                    if ш == 390 and тема == "blank":
                        print("  " + json.dumps(р, ensure_ascii=False)[:900])
                    if not р["есть"]:
                        плохо(н + " нет кнопки колокольчика"); стр.close(); continue
                    з = р["загрузка"]
                    if not з["полоска"] or з["бег"] in (None, "none"):
                        плохо(н + f" пока уведомления собираются, полоски загрузки нет ({з['текст']!r})")
                    elif not з["поЦентру"]:
                        плохо(н + " полоска загрузки не по центру окна")
                    if "Смотрим" in з["текст"]:
                        плохо(н + " в окне по-прежнему «Смотрим…»")
                    п, о, оп, зк = р["покой"], р["открыт"], р["открытПосле"], р["закрыт"]
                    # В «Модерне» колокольчик и в покое цвета схемы — там перемена в заливке.
                    if о["заливка"] in ("none", "") or о["заливка"] == п["заливка"] or о["раскрыт"] != "true":
                        плохо(н + f" открытое окно не меняет вид колокольчика ({о} против {п})")
                    if abs(з["качание"] or 0) < 4:
                        плохо(н + f" в миг открытия колокольчик не качается (угол {з['качание']})")
                    if оп["угол"]:
                        плохо(н + f" качание не кончилось ({оп['угол']}°)")
                    if оп["заливка"] in ("none", ""):
                        плохо(н + " после загрузки списка колокольчик потерял вид открытого")
                    if зк["заливка"] != п["заливка"] or зк["цвет"] != п["цвет"] or зк["раскрыт"] == "true":
                        плохо(н + f" окно закрыто, а колокольчик не вернулся ({зк} против {п})")
                    for о_ in [о_ for о_ in ошибки if "supabase.co" not in о_][:3]:
                        плохо(f"{н} ошибка страницы: {о_[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    печать()


def печать():
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: пока уведомления собираются, по центру окна бежит полоска; открытый колокольчик залит цветом схемы "
          "и качнулся, закрытый вернулся к прежнему виду — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
