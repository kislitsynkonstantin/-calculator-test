#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: звезда пресета переезжает между доменами.

19.09.2026 Константин: «в тестовом на пресет поставил звезду, на боевом нет
звезды на этом пресете». Отметка лежала в localStorage, а у теста и боя это
разные origin — память у каждого своя. Теперь звезда хранится полем самого
пресета в облаке.

Проверяется:
  • нажатие звезды уходит в облако, а при отказе базы отметка возвращается
    как была — на экране и в базе одно и то же;
  • синхронизация приносит звезду, поставленную на другом домене, даже когда
    расчёт здесь свежее: звезда живёт своей жизнью, её ставят нажатием;
  • разовый перенос: звёзды, поставленные до этой правки, поднимаются в облако,
    а не гаснут при первой же синхронизации;
  • после переноса облако главное — снятая там звезда гаснет и здесь.

    python3 check_preset_stars.py
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


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(найденные[-1])


ХРОМ = хром()
ТАБЛИЦЫ = {
    "presets": [
        # Первый: в облаке звезды нет, в браузере есть — её надо поднять.
        {"id": "p1", "user_id": "u-проба", "name": "Баня «Берлин» 9×5",
         "state": {"savedAt": "2026-09-18T10:00:00Z"}, "starred": False,
         "updated_at": "2026-09-18T10:00:00Z", "deleted_at": None},
        # Второй: звезда стоит в облаке — её надо принести сюда.
        {"id": "p2", "user_id": "u-проба", "name": "Отделка парной",
         "state": {"savedAt": "2026-09-18T07:00:00Z"}, "starred": True,
         "updated_at": "2026-09-18T07:00:00Z", "deleted_at": None},
    ],
    "preset_links": [], "client_links": [], "client_link_visits": [],
    "pricing_projects": [], "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(текст):
    НАХОДКИ.append(текст)


def спросить(стр, js, *арг):
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:130])
        return None


def облако(стр):
    return спросить(стр, """() => Object.fromEntries(
      (window.__ТАБЛИЦЫ.presets || []).map(с => [с.id, !!с.starred]))""") or {}


def местные(стр):
    return спросить(стр, """() => {
      const все = loadAllPresets();
      return Object.fromEntries(Object.values(все).map(п => [п.id, !!п.starred]));
    }""") or {}


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                "window.addEventListener('DOMContentLoaded', function () {\n"
                "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n"
                "});")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            спросить(стр, """() => {
              const б = document.getElementById('pricingErrorScreen');
              if (б) б.style.display = 'none';
              // Браузер «с прошлой жизни»: звезда стоит только здесь.
              localStorage.removeItem('stars_to_cloud_v1');
              saveAllPresets({
                p1: { id: 'p1', name: 'Баня «Берлин» 9×5', starred: true,
                      state: { savedAt: '2026-09-18T10:00:00Z' }, savedAt: '2026-09-18T10:00:00Z' },
                p2: { id: 'p2', name: 'Отделка парной', starred: false,
                      state: { savedAt: '2026-09-18T07:00:00Z' }, savedAt: '2026-09-18T07:00:00Z' },
              });
            }""")

            # ── разовый перенос и встречное движение ────────────────────────
            спросить(стр, "async () => { await sbSyncPresets(true); }")
            стр.wait_for_timeout(600)
            вОблаке, здесь = облако(стр), местные(стр)
            if not вОблаке.get("p1"):
                плохо("звезда, стоявшая только в браузере, не поднялась в облако — "
                      "на другом домене её так и не будет")
            if not здесь.get("p1"):
                плохо("своя звезда погасла после первой же синхронизации")
            if not здесь.get("p2"):
                плохо("звезда, поставленная на другом домене, не приехала сюда")
            метка = спросить(стр, "() => !!localStorage.getItem('stars_to_cloud_v1')")
            if not метка:
                плохо("перенос не отмечен — он повторится и будет поднимать снятые звёзды")

            # ── после переноса облако главное ───────────────────────────────
            спросить(стр, """async () => {
              // На другом домене звезду сняли.
              (window.__ТАБЛИЦЫ.presets || []).forEach(с => { if (с.id === 'p2') с.starred = false; });
              await sbSyncPresets(true);
            }""")
            стр.wait_for_timeout(500)
            if местные(стр).get("p2"):
                плохо("звезда, снятая на другом домене, здесь осталась — облако не главное")

            # ── нажатие уходит в облако ─────────────────────────────────────
            спросить(стр, "async () => { await togglePresetStar('p2'); }")
            стр.wait_for_timeout(400)
            if not облако(стр).get("p2"):
                плохо("нажатие звезды не записалось в облако")
            if not местные(стр).get("p2"):
                плохо("нажатие звезды не отметило карточку")

            # ── отказ базы: отметка возвращается как была ───────────────────
            спросить(стр, """() => {
              const исх = _sb.from.bind(_sb);
              _sb.from = (табл) => {
                const о = исх(табл);
                if (табл !== 'presets') return о;
                о.then = (ок) => Promise.resolve(ок({ data: null, error: { message: 'нет связи' } }));
                return о;
              };
            }""")
            спросить(стр, "async () => { await togglePresetStar('p2'); }")
            стр.wait_for_timeout(500)
            if not местные(стр).get("p2"):
                плохо("база отказала, а отметка на экране изменилась — на экране одно, "
                      "в базе другое")

            важные = [о for о in ошибки if "supabase.co" not in о and "цены" not in о]
            for о in важные[:3]:
                плохо("ошибка страницы: " + о[:150])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: звезда поднимается в облако разово, приезжает с другого домена, "
          "снимается оттуда же и возвращается при отказе базы.")


if __name__ == "__main__":
    главная()
