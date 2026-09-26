#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Стрелка «Сбросить» делает оборот после нажатия пункта меню.

Константин 26.09.2026: «добавь анимацию на „Сбросить“: когда нажимаю любую
кнопку из выпадающего меню, то стрелочка перед кнопкой „Сбросить“
прокручивается».

Проба держит на 390 и 1440, в «Бланке» и «Модерне», для каждого пункта меню:
  • после нажатия у стрелки идёт анимация оборота;
  • посреди оборота стрелка действительно повёрнута (мерим матрицу, а не
    класс: класс без правила в стилях ничего не крутит);
  • через секунду оборот кончился и стрелка стоит как прежде;
  • выключенные пункты (сбрасывать нечего) нажатия не получают и в счёт не
    идут — чтобы их было несколько, проба сначала выделяет пару опций, дарит их и
    ставит звёзды;
  • в покое, до нажатий, стрелка не крутится.

    python3 check_reset_spin.py
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
  window.confirm = () => false;
  const кнопка = document.getElementById('resetDropdownBtn');
  const знак = кнопка && кнопка.querySelector('svg');
  const угол = () => { if (!знак) return null; const м = getComputedStyle(знак).transform;
    if (!м || м === 'none') return 0; const ч = м.match(/-?[\\d.e]+/g).map(Number); return Math.round(Math.atan2(ч[1], ч[0]) * 180 / Math.PI); };
  const покой = { анимация: знак ? getComputedStyle(знак).animationName : null, угол: угол() };
  // Пункты меню активны, только когда есть что сбрасывать: отмечаем пару
  // опций (выделение, подарок, звезда). «Сбросить всё» жмём последним — после него остальные гаснут, а
  // выключенная кнопка нажатия не получает вовсе.
  const ид = OPTIONS.filter(o => !o.included).slice(0, 2).map(o => o.id);
  ид.forEach(и => { highlightedOpts.add(и); giftedOpts.add(и); starredOpts.add(и); });
  updateResetDropdownVisibility(); await ждать(200);
  const пункты = [...document.querySelectorAll('#resetDropdownMenu .reset-dropdown-item')].map(п => (п.textContent || '').trim());
  const порядок = пункты.map((_, i) => i).reverse();
  const итог = [];
  for (const i of порядок) {
    toggleResetDropdown(); await ждать(120);
    const п = document.querySelectorAll('#resetDropdownMenu .reset-dropdown-item')[i];
    if (!п || !п.offsetWidth || п.disabled) { итог.push({ имя: пункты[i], скрыт: true }); closeResetDropdown(); continue; }
    п.click();
    await ждать(260);
    const посреди = { анимация: getComputedStyle(знак).animationName, угол: угол() };
    await ждать(900);
    итог.push({ имя: пункты[i], посреди, после: { анимация: getComputedStyle(знак).animationName, угол: угол() } });
  }
  return { есть: !!знак, покой, итог };
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
                    стр.evaluate(f"""async () => {{
                      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                      applyUiStyle('{тема}', false);
                      selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
                    }}""")
                    р = стр.evaluate(СЦЕНАРИЙ)
                    н = f"[{ш} {тема}]"
                    if ш == 390 and тема == "blank":
                        print("  " + json.dumps(р, ensure_ascii=False)[:700])
                    if not р["есть"]:
                        плохо(н + " у кнопки «Сбросить» нет стрелки"); стр.close(); continue
                    if р["покой"]["анимация"] not in ("none", "") or р["покой"]["угол"]:
                        плохо(н + f" стрелка крутится без нажатия ({р['покой']})")
                    видимых = [п for п in р["итог"] if not п.get("скрыт")]
                    if len(видимых) < 2 or not any("всё" in п["имя"] for п in видимых):
                        плохо(н + f" нажимаемых пунктов {len(видимых)} — мерить не на чем")
                    for п in видимых:
                        if п["посреди"]["анимация"] in ("none", "") or abs(п["посреди"]["угол"] or 0) < 20:
                            плохо(н + f" «{п['имя']}»: стрелка не крутится ({п['посреди']})")
                        if п["после"]["анимация"] not in ("none", "") or п["после"]["угол"]:
                            плохо(н + f" «{п['имя']}»: оборот не кончился ({п['после']})")
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
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: после каждого пункта меню «Сбросить» стрелка делает оборот и встаёт на место, в покое не крутится — "
          "на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
