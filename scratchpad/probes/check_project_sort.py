#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Порядок проектов в списке: по названию, по частоте, по умолчанию.

Константин 24.09.2026 выбрал вид 01 макета project-sort-v1 — три значка в
строке «Снять выбор» — и ответил на вопросы: частота у каждого менеджера
своя, за всё время, выбор запоминается в аккаунте.

Проба меряет поведение и место, а не разметку:

  • каждый значок выстраивает список своим порядком — проверяется сам
    порядок названий в открытом списке;
  • список после нажатия остаётся открытым (кнопка уходит из документа
    при перерисовке, и нажатие легко принять за нажатие снаружи);
  • выбор уходит в настройки аккаунта — в строку профиля, а не только в
    память браузера;
  • частота — сколько раз менеджер выбирал проект (Константин: «частоту
    проектов определяй по тому, как менеджер часто его выбирал»): выбор в
    этом заходе поднимает проект сразу, каждый выбор — на единицу, а печать
    не считается вовсе;
  • база не ответила — список в обычном порядке, страница не падает;
  • без выбранного проекта значки на месте, рядом подпись;
  • палец: в 18 px над и под значком и в 13 px вбок нажатие ловит его же,
    сам значок нарисован не больше 26 px; от правого края строки значки
    отстоят, а не прилипают.

Оборвавшаяся проверка — тоже находка: иначе проба, упавшая на полпути,
молча выглядела бы прошедшей.

    python3 check_project_sort.py
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

ЭССЕН, БЕРЛИН, ВИГО, ААХЕН = ("Фахверковая баня «Эссен» 6х4", "Баня «Берлин» 9х5",
                             "Хай-тек баня «Виго» 7,7х8,2", "Баня «Аахен» 4х4")
ПО_УМОЛЧАНИЮ = [ЭССЕН, БЕРЛИН, ВИГО, ААХЕН]
ПО_НАЗВАНИЮ = [ААХЕН, БЕРЛИН, ЭССЕН, ВИГО]
ПО_ЧАСТОТЕ = [ВИГО, БЕРЛИН, ЭССЕН, ААХЕН]


def проект(имя, порядок):
    return {"product": "frame", "sort": порядок, "slug": имя, "name": имя,
            "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
            "floors": 1, "roof_type": "двускатная", "warm": True, "open_area": 10,
            "closed_area": 20, "facade_area": 60, "paint_area": 60, "roof_area": 40}


ТАБЛИЦЫ = dict(ДАННЫЕ,
               pricing_projects=[проект(и, н + 1) for н, и in enumerate(ПО_УМОЛЧАНИЮ)],
               profiles=[{"id": "u-проба", "role": "manager", "first_name": "Проба",
                          "last_name": "", "app_settings": {}}],
               events=[])
ЧАСТОТА = [
    {"project_name": ВИГО, "picks": 7, "last_used": "2026-09-10T10:00:00Z"},
    {"project_name": БЕРЛИН, "picks": 3, "last_used": "2026-09-20T10:00:00Z"},
    {"project_name": ЭССЕН, "picks": 3, "last_used": "2026-09-01T10:00:00Z"},
]
ПОДГОТОВКА_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
                 + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");"
                 "window.__RPC = window.__RPC || {};"
                 "window.__RPC.project_picks = " + json.dumps(ЧАСТОТА, ensure_ascii=False) + ";"
                 "try { localStorage.removeItem('appSettings_v1'); } catch (e) {}")


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


СПИСОК = """() => [...document.querySelectorAll('#projectSelectDropdown .cso-name')]
  .map(э => э.textContent.trim())"""

ОТКРЫТ = "() => document.getElementById('projectSelectWrap').classList.contains('open')"

ЗНАЧКИ = """([вверх, вбок]) => {
  const ряд = document.querySelector('#projectSelectDropdown .cs-sortrow');
  if (!ряд) return null;
  const р = ряд.getBoundingClientRect();
  const кн = [...ряд.querySelectorAll('.cs-sbtn')];
  return {
    подпись: (ряд.querySelector('.cs-sortcap') || {}).textContent || '',
    снять: !!ряд.querySelector('.custom-select-deselect'),
    вкл: (ряд.querySelector('.cs-sbtn.on') || { dataset: {} }).dataset.sort || null,
    значки: кн.map(к => {
      const б = к.getBoundingClientRect();
      const x = б.left + б.width / 2, y = б.top + б.height / 2;
      const ловит = [[x, y - вверх], [x, y + вверх], [x - вбок, y], [x + вбок, y]].map(([тx, тy]) => {
        const э = document.elementFromPoint(тx, тy);
        return !!(э && э.closest && э.closest('.cs-sbtn') === к);
      });
      return { код: к.dataset.sort, ш: Math.round(б.width), в: Math.round(б.height), ловит,
               доПравого: Math.round(р.right - б.right), x: Math.round(x), y: Math.round(y) };
    }),
  };
}"""

ДНЕЙ = """(имя) => {
  if (typeof _частотаПроектов === 'undefined' || !_частотаПроектов) return null;
  const з = _частотаПроектов.get(имя);
  return з ? з.раз : 0;
}"""


def открыть(стр, порт, бланк, ночь):
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ПОДГОТОВКА_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""([бланк, ночь]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      applyThemeMode(ночь ? 'dark' : 'light', false);
    }""", [бланк, ночь])


def нажать(стр, код):
    """Нажатие мышью по значку; список перед этим открывается, если закрыт."""
    if not стр.evaluate(ОТКРЫТ):
        стр.evaluate("toggleProjectDropdown()")
        стр.wait_for_timeout(300)
    з = стр.evaluate(ЗНАЧКИ, [18, 13])
    к = next(к for к in з["значки"] if к["код"] == код)
    стр.mouse.click(к["x"], к["y"])
    стр.wait_for_timeout(400)


def проверить(стр, где):
    стр.evaluate("toggleProjectDropdown()")
    стр.wait_for_timeout(300)
    з = стр.evaluate(ЗНАЧКИ, [18, 13])
    if not з or len(з["значки"]) != 3:
        плохо(f"[{где}] без выбранного проекта значков порядка нет")
        return
    if з["снять"] or "Порядок" not in з["подпись"]:
        плохо(f"[{где}] без выбранного проекта рядом со значками нет подписи")
    if стр.evaluate(СПИСОК) != ПО_УМОЛЧАНИЮ:
        плохо(f"[{где}] исходный порядок не по умолчанию: {стр.evaluate(СПИСОК)}")

    # ── три порядка, список не закрывается ──
    for код, ждём in (("name", ПО_НАЗВАНИЮ), ("freq", ПО_ЧАСТОТЕ), ("default", ПО_УМОЛЧАНИЮ)):
        нажать(стр, код)
        стр.wait_for_timeout(300)
        if not стр.evaluate(ОТКРЫТ):
            плохо(f"[{где}] после нажатия «{код}» список закрылся")
        есть = стр.evaluate(СПИСОК)
        if есть != ждём:
            плохо(f"[{где}] «{код}»: порядок {есть}, ждали {ждём}")
        з2 = стр.evaluate(ЗНАЧКИ, [18, 13])
        if з2 and з2["вкл"] != код:
            плохо(f"[{где}] после нажатия «{код}» отмечен «{з2['вкл']}»")

    # ── палец и вес ──
    for к in з["значки"]:
        if к["ш"] > 26 or к["в"] > 26:
            плохо(f"[{где}] значок «{к['код']}» нарисован {к['ш']}×{к['в']} px — палец оплачен весом")
        мимо = [с_ for с_, п in zip(("сверху", "снизу", "слева", "справа"), к["ловит"]) if not п]
        if мимо:
            плохо(f"[{где}] значок «{к['код']}»: нажатие мимо ({', '.join(мимо)})")
    край = з["значки"][-1]["доПравого"]
    if край < 8:
        плохо(f"[{где}] последний значок в {край} px от края строки — прилип")

    # ── выбор в аккаунте ──
    нажать(стр, "name")
    сохр = стр.evaluate("""() => {
      const п = (window.__ТАБЛИЦЫ.profiles || []).find(p => p.id === 'u-проба') || {};
      return (п.app_settings || {}).projectSort || null;
    }""")
    if сохр != "name":
        плохо(f"[{где}] выбор не ушёл в профиль аккаунта (там {сохр!r})")

    # ── частота — выборы проекта: каждый засчитан, печать нет ──
    нажать(стр, "freq")
    было = стр.evaluate(ДНЕЙ, ААХЕН)
    стр.evaluate("""async ([а, б]) => {
      const выбрать = async (имя) => {
        selectProjectOption(filteredProjects.findIndex(p => p[0] === имя));
        await new Promise(r => setTimeout(r, 500));
      };
      await выбрать(а);
      await logEvent('print', {});
      await logEvent('print', {});
      await выбрать(б);
      await выбрать(а);
      await new Promise(r => setTimeout(r, 300));
    }""", [ААХЕН, БЕРЛИН])
    стало = стр.evaluate(ДНЕЙ, ААХЕН)
    if было is None or стало is None:
        плохо(f"[{где}] счёта частоты нет — проверить засчитывание нечем")
    elif стало - было != 2:
        плохо(f"[{где}] два выбора проекта (и две печати между ними) засчитаны как "
              f"{стало - было}, ждали 2")
    print(f"  {где}: значки {[к['ш'] for к in з['значки']]} px, до края {край} px")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ночь in (False, True):
                    for ш, в in ((390, 900), (1440, 950)):
                        где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"
                        стр = бр.new_page(viewport={"width": ш, "height": в})
                        ошибки = []
                        стр.on("pageerror", lambda e, о=ошибки: о.append(str(e)))
                        открыть(стр, порт, бланк, ночь)
                        try:
                            проверить(стр, где)
                        except Exception as e:
                            плохо(f"[{где}] проба оборвалась: {e!s:.200}")
                        if ошибки:
                            плохо(f"[{где}] ошибки страницы: " + "; ".join(ошибки)[:200])
                        стр.close()

            # ── база не ответила ──
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ПОДГОТОВКА_JS)
            стр.add_init_script("window.__RPC.project_picks = () => { throw new Error('нет функции'); };")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("() => { const в = document.getElementById('loginScreen'); if (в) в.style.display='none'; }")
            try:
                нажать(стр, "freq")
                стр.wait_for_timeout(500)
                if стр.evaluate(СПИСОК) != ПО_УМОЛЧАНИЮ:
                    плохо(f"[отказ базы] список не в обычном порядке: {стр.evaluate(СПИСОК)}")
            except Exception as e:
                плохо(f"[отказ базы] проба оборвалась: {e!s:.200}")
            if ошибки:
                плохо("[отказ базы] ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: три значка выстраивают список своим порядком и не закрывают его, "
          "выбор уходит в аккаунт, каждый выбор проекта засчитывается сразу, а печать нет, "
          "отказ базы оставляет обычный порядок, палец ловит значки, а вес их прежний.")


if __name__ == "__main__":
    главная()
