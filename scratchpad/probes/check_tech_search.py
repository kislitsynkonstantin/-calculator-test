#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: смена технологии обновляет открытые окна.

Константин 20.09.2026, снимком поиска: «когда включена технология Клеёный
брус, через поиск выдаёт опции на Каркас. Нужно разделить: когда находишься
в Клеёном брусе — поиск должен давать только его опции и базу».

Причина не в самом поиске: он честно читает `OPTIONS`, а их `applyTechData`
подменяет при переключении. Окно, открытое до смены технологии, просто
оставалось нарисованным по-старому — главная страница перерисовывалась,
а окно нет.

Проба это и меряет:

  • поиск, открытый в каркасе, после перехода в брус показывает позиции
    бруса, не трогая окна руками; запрос при этом остаётся в поле;
  • обратный переход возвращает каркас;
  • окна, собранные из самого расчёта, при смене технологии закрываются:
    расчёта больше нет, а из печати документ уходит клиенту;
  • позиция, дописанная руками в каркасе, в брусе не видна — и наоборот,
    а по возвращении находится на месте. Обе технологии писали в один
    `customOptions`, и каркасная строка попадала в брусовый поиск и во
    вкладку «Ручные».

Каркасные позиции лежат в самом файле, брусовые приходят из базы, поэтому
в обстановке у брусовых имена с приставкой «БРУС: » — по ней и видно, чьи
строки в окне.

    python3 check_tech_search.py
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
ЗАПРОС = "маслом"
МЕТКА = "БРУС: "
РУЧНАЯ = "РУЧНАЯ каркасная позиция маслом"

# У каркаса список опций лежит в файле, база даёт только цены и статусы;
# у бруса из базы приходит весь список. Поэтому здесь брусовые придуманы,
# а каркасные придут свои, настоящие, — и перепутать их нельзя.
_ИМЕНА = ["Покраска снаружи маслом Osmo", "Обработка фасада маслом",
          "Кровля металлочерепица", "Полок из липы"]
ОПЦИИ = [{"product": "glulam", "option_id": "kb_g%d" % (н + 1),
          "section": ["paint", "paint", "roof", "steam"][н],
          "name": МЕТКА + имя, "included": False, "price": 10000,
          "formula": None, "status": None, "sort": н + 1}
         for н, имя in enumerate(_ИМЕНА)]
ОПЦИИ.append({"product": "glulam", "option_id": "kb_g9", "section": "paint",
              "name": МЕТКА + "базовая покраска маслом", "included": True,
              "price": 0, "formula": None, "status": None, "sort": 9})

ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": п, "sort": и, "slug": "%s %d×4" % (п, и), "name": "%s %d×4" % (п, и),
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True, "open_area": 10,
        "closed_area": 20, "facade_area": 60, "paint_area": 60, "roof_area": 40,
    } for п in ("frame", "glulam") for и in (1, 2)],
    "pricing_matrix": [{"product": о["product"], "project_slug": "glulam 1×4",
                        "option_id": о["option_id"], "price": 30000} for о in ОПЦИИ],
    "pricing_options": ОПЦИИ,
    "pricing_sections": [{"product": п, "section_key": к, "pct": None, "fixed": None}
                         for п in ("frame", "glulam")
                         for к in ("paint", "roof", "steam", "frame")],
    "project_kits": [], "project_kit_locks": [], "presets": [], "preset_links": [],
    "client_links": [], "client_link_visits": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}

# Окна, собранные из расчёта: при смене технологии их надо закрыть.
ОКНА = ["printOverlay", "paymentPlanOverlay", "contractDataOverlay",
        "contractValOverlay", "contractPreviewOverlay", "komplOverlay"]


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


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


СТРОКИ = """() => [...document.querySelectorAll('#optSearchResults .ops-row')]
  .map(э => (э.innerText || '').split('\\n')[0].trim())"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            спросить(стр, """() => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
            }""")

            # ── Поиск открыт в каркасе ──
            вкаркасе = спросить(стр, """async (q) => {
              openOptSearch();
              await new Promise(r => setTimeout(r, 300));
              const п = document.getElementById('optSearchInput');
              п.value = q; renderOptSearchResults();
              await new Promise(r => setTimeout(r, 300));
              return [...document.querySelectorAll('#optSearchResults .ops-row')]
                .map(э => (э.innerText || '').split('\\n')[0].trim());
            }""", ЗАПРОС) or []
            if not вкаркасе:
                плохо(f"в каркасе по запросу «{ЗАПРОС}» не нашлось ничего — "
                      "проверять нечего, проба мерила бы вхолостую")
            elif any(и.startswith(МЕТКА) for и in вкаркасе):
                плохо("в каркасе нашлись позиции бруса: "
                      + ", ".join(и for и in вкаркасе if и.startswith(МЕТКА))[:120])

            # Позиция, дописанная руками в каркасе: в брусе её быть не должно.
            спросить(стр, """(имя) => {
              const сек = SECTIONS[0].key;
              getCustomOpts(сек).push({ id: 'проба-ручная', name: имя,
                                        price: 5000, checked: true });
              const прим = customNotes[сек] || (customNotes[сек] = []);
              прим.push({ id: 'cn-проба', text: 'КАРКАСНОЕ примечание' });
            }""", РУЧНАЯ)

            # Окна расчёта открыты — после перехода они должны закрыться.
            спросить(стр, """(окна) => okna_(окна);
              function okna_(о) { о.forEach(ид => {
                const э = document.getElementById(ид); if (э) э.style.display = 'block'; }); }""",
                     ОКНА)

            # ── Переход в брус, окна руками не трогаем ──
            спросить(стр, "async () => { await switchTech('glulam'); }")
            стр.wait_for_timeout(1800)
            вбрусе = спросить(стр, СТРОКИ) or []
            поле = спросить(стр, "() => document.getElementById('optSearchInput').value")
            открыты = спросить(стр, """(окна) => окна.filter(ид => {
              const э = document.getElementById(ид);
              return э && э.style.display !== 'none';
            })""", ОКНА) or []

            if not вбрусе:
                плохо("после перехода в брус поиск пуст — окно не перерисовалось вовсе "
                      "или позиции бруса до него не доехали")
            else:
                чужие = [и for и in вбрусе if not и.startswith(МЕТКА)]
                if чужие:
                    плохо("в брусе поиск выдаёт позиции каркаса: " + ", ".join(чужие)[:130])
            ручные = спросить(стр, """() => {
              const все = [];
              SECTIONS.forEach(s => getCustomOpts(s.key).forEach(c => все.push(c.name)));
              const прим = [];
              Object.keys(customNotes).forEach(к =>
                (customNotes[к] || []).forEach(н => прим.push(н.text)));
              return { позиции: все, примечания: прим };
            }""") or {}
            if РУЧНАЯ in (ручные.get("позиции") or []):
                плохо("дописанная в каркасе позиция осталась в брусе — руками вписанное "
                      "принадлежит своей технологии")
            if any("КАРКАСНОЕ" in т for т in (ручные.get("примечания") or [])):
                плохо("примечание, дописанное в каркасе, осталось в брусе")
            if поле != ЗАПРОС:
                плохо(f"запрос из поля пропал при смене технологии: «{поле}» вместо «{ЗАПРОС}»")
            if открыты:
                плохо("окна расчёта остались открытыми после смены технологии: "
                      + ", ".join(открыты) + " — в них прежняя технология, а из печати "
                      "документ уходит клиенту")

            # ── И обратно ──
            спросить(стр, "async () => { await switchTech('frame'); }")
            стр.wait_for_timeout(1800)
            назад = спросить(стр, СТРОКИ) or []
            if not назад:
                плохо("после возврата в каркас поиск пуст")
            elif any(и.startswith(МЕТКА) for и in назад):
                плохо("после возврата в каркас в поиске остались позиции бруса: "
                      + ", ".join(и for и in назад if и.startswith(МЕТКА))[:120])
            # Убранное не потеряно: в своей технологии оно на месте.
            вернулось = спросить(стр, """() => {
              const все = [];
              SECTIONS.forEach(s => getCustomOpts(s.key).forEach(c => все.push(c.name)));
              return все;
            }""") or []
            if РУЧНАЯ not in вернулось:
                плохо("дописанная в каркасе позиция пропала после возврата в каркас — "
                      "убрали из чужой технологии и потеряли совсем")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])

            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: открытый поиск переезжает вместе с технологией — в брусе только "
          "брус, в каркасе только каркас, запрос в поле цел, окна расчёта закрыты.")


if __name__ == "__main__":
    главная()
