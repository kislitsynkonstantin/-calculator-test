#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: список «Сбросить всё» свёрнут, пока не понадобится.

Константин 20.09.2026: «тут где кнопка „Сбросить всё" поставь птичку, которая
бы раскрывала тогглы. Их много, они постоянно не нужны в доступе».

Проверяется:

  • при открытии настроек список свёрнут, четырнадцати строк на экране нет;
  • в заголовке стоит счёт «N из 14», и он совпадает с тем, сколько
    переключателей включено на самом деле, — иначе цифра врёт, а ради неё
    список и не раскрывают;
  • нажатие раскрывает: строки появляются, птичка переворачивается;
  • после раскрытия заголовок остаётся виден — не уезжает под липкую полосу
    вкладок. Нажал на строку, а строки нет — это и было первым, что
    сломалось;
  • площадь нажатия заголовка не меньше 44 px по высоте, хотя сама строка
    мелкая: надпись раздувать нельзя, поле нажатия — можно;
  • переключение внутри списка меняет счёт и не схлопывает список.

    python3 check_reset_fold.py
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
ПУНКТОВ = 14
НАЖАТИЕ = 44

ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": и, "slug": "Проба %d×4" % (5 + и),
        "name": "Проба %d×4" % (5 + и),
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    } for и in (1, 2)],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(тема, текст):
    НАХОДКИ.append(f"[{тема}] {текст}")


def спросить(стр, тема, js, *арг):
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо(тема, "на странице нет того, что проверяется: "
              + str(e).split("\n")[0][:120])
        return None


СНЯТЬ = """() => {
  const шапка = document.querySelector('#settingsBody .st-fold');
  const тело = document.querySelector('#settingsBody .st-fold-body');
  if (!шапка || !тело) return { нет: true };
  const счёт = шапка.querySelector('.st-fold-n');
  const птичка = шапка.querySelector('.st-fold-v');
  const ряды = [...document.querySelectorAll('#settingsBody .st-fold-body .st-row')];
  const видно = ряды.filter(р => р.getClientRects().length > 0).length;
  const поле = getComputedStyle(шапка, '::before');
  const к = шапка.getBoundingClientRect();
  const вкладки = document.querySelector('#settingsBox > div:nth-child(2)');
  const вк = вкладки ? вкладки.getBoundingClientRect() : { bottom: 0 };
  return {
    свёрнуто: !!тело.hidden,
    открытКласс: шапка.classList.contains('open'),
    счёт: счёт ? счёт.textContent.trim() : '',
    поворот: птичка ? getComputedStyle(птичка).transform : '',
    рядовВсего: ряды.length,
    рядовВидно: видно,
    нажатие: Math.round(к.height
      + Math.abs(parseFloat(поле.top || '0')) + Math.abs(parseFloat(поле.bottom || '0'))),
    подВкладками: Math.round(к.top - вк.bottom),
  };
}"""


def включено(стр, тема):
    """Сколько переключателей списка включено на самом деле."""
    return спросить(стр, тема, """() => {
      const ключи = ['project','checkedOptions','sort','customOptions','customNotes','images',
                     'stars','highlights','printPrices','porValues','hiddenNotes','gifts',
                     'discount','requisites'];
      const cfg = appSettings.resetAllConfig || {};
      return ключи.filter(к => cfg[к] !== false).length;
    }""")


def проверить(бр, порт, тема, ширина):
    стр = бр.new_page(viewport={"width": ширина, "height": 860})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2400)
    спросить(стр, тема, """async (тема) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      document.body.classList.toggle('ui-blank', тема === 'бланк');
      window._sbProfile = { role: 'admin', full_name: 'Проба' };
      openSettings();
      await new Promise(r => setTimeout(r, 700));
      renderSettingsBody();
    }""", тема)
    стр.wait_for_timeout(400)

    с = спросить(стр, тема, СНЯТЬ) or {}
    if с.get("нет"):
        плохо(тема, "сворачивающегося раздела «Сбросить всё» в настройках нет")
        стр.close()
        return
    if not с["свёрнуто"]:
        плохо(тема, "список открыт сразу — его затем и сворачивали, что он не нужен "
                    "постоянно")
    if с["рядовВсего"] != ПУНКТОВ:
        плохо(тема, f"пунктов в списке {с['рядовВсего']}, а не {ПУНКТОВ} — счёт в "
                    "заголовке будет считать не то")
    if с["рядовВидно"]:
        плохо(тема, f"свёрнутый список всё равно показывает {с['рядовВидно']} строк")
    вкл = включено(стр, тема)
    if с["счёт"] != f"{вкл} из {ПУНКТОВ}":
        плохо(тема, f"счёт в заголовке «{с['счёт']}», а включено {вкл} из {ПУНКТОВ}")
    if с["нажатие"] < НАЖАТИЕ:
        плохо(тема, f"площадь нажатия заголовка {с['нажатие']} px при мерке {НАЖАТИЕ}")

    # ── раскрытие ──
    стр.evaluate("() => переключитьСброс()")
    стр.wait_for_timeout(1200)
    р = спросить(стр, тема, СНЯТЬ) or {}
    if р.get("свёрнуто"):
        плохо(тема, "нажатие не раскрыло список")
    if not р.get("открытКласс"):
        плохо(тема, "заголовок не помечен раскрытым — птичка смотрит в ту же сторону")
    if р.get("рядовВидно") != ПУНКТОВ:
        плохо(тема, f"после раскрытия видно {р.get('рядовВидно')} строк из {ПУНКТОВ}")
    if р.get("поворот") in ('', 'none') or р.get("поворот") == с.get("поворот"):
        плохо(тема, "птичка не перевернулась — свёрнутый и раскрытый вид одинаковы")
    if р.get("подВкладками", 0) < 0:
        плохо(тема, f"заголовок уехал под полосу вкладок на {-р['подВкладками']} px — "
                    "нажал на строку, а строки нет")

    # ── счёт живёт вместе со списком ──
    стр.evaluate("""() => {
      const в = document.querySelector('#settingsBody .st-fold-body .st-toggle input');
      if (в) { в.checked = false; в.dispatchEvent(new Event('change', { bubbles: true })); }
    }""")
    стр.wait_for_timeout(400)
    п = спросить(стр, тема, СНЯТЬ) or {}
    вкл2 = включено(стр, тема)
    if вкл2 != вкл - 1:
        плохо(тема, f"переключатель не снялся: было {вкл}, стало {вкл2}")
    elif п.get("счёт") != f"{вкл2} из {ПУНКТОВ}":
        плохо(тема, f"счёт не пошёл за переключателем: «{п.get('счёт')}» при {вкл2}")
    if п.get("свёрнуто"):
        плохо(тема, "список схлопнулся от нажатия на переключатель внутри него")

    if ошибки:
        плохо(тема, "ошибки страницы: " + "; ".join(ошибки)[:160])
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for тема, ширина in (("бланк", 390), ("модерн", 390), ("бланк", 1440)):
                проверить(бр, порт, тема, ширина)
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: список «Сбросить всё» открывается свёрнутым, счёт в заголовке "
          "сходится с переключателями, птичка раскрывает и заголовок остаётся "
          "на виду.")


if __name__ == "__main__":
    главная()
