#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: скрытое примечание принадлежит своей технологии.

Ключ скрытого примечания был «раздел_номер» (`paint_0`), без технологии, а
список примечаний при переключении подменяется — значит один ключ означал
разные примечания в каркасе и в брусе. Спрятал в каркасе «Лессирующий
состав…» — в брусе пропадало «Покраска строения в базовую комплектацию не
входит»; увидеть это можно было, только сложив два клиентских листа рядом.
Константин 20.09.2026: «лечи, побочное разрешаю».

Проверяется:

  • спрятанное в каркасе не прячется в брусе — ни на экране, ни в листе
    для печати, куда примечания уходят к клиенту;
  • спрятанное в брусе остаётся спрятанным в брусе: правка разделила
    технологии, а не сбросила отметки;
  • разовый перевод старых меток: `paint_0` из памяти браузера становится
    `frame_paint_0` и продолжает прятать то же самое примечание каркаса;
  • метки без номера (`steam_stove`) не трогаются — они означают одно и то
    же в обеих технологиях.

Мерка — не сам ключ, а что видно: видимость строки на экране и наличие
текста в листе для печати. Ключ можно переименовать и сломать при этом
показ, и наоборот.

    python3 check_hidden_notes.py
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

# Проектов по два на технологию: с одним калькулятор выбирает его сам.
ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": п, "sort": и, "slug": "%s %d×4" % (п, и), "name": "%s %d×4" % (п, и),
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True, "open_area": 10,
        "closed_area": 20, "facade_area": 60, "paint_area": 60, "roof_area": 40,
    } for п in ("frame", "glulam") for и in (1, 2)],
    "pricing_matrix": [],
    # Опции бруса нужны хоть какие-то: без них раздел покраски в брусе пуст,
    # и примечания к нему не с чем показывать.
    "pricing_options": [{"product": "glulam", "option_id": "kb_p1", "section": "paint",
                         "name": "БРУС: покраска", "included": False, "price": 10000,
                         "formula": None, "status": None, "sort": 1}],
    "pricing_sections": [{"product": п, "section_key": "paint", "pct": None, "fixed": None}
                         for п in ("frame", "glulam")],
    "project_kits": [], "project_kit_locks": [], "presets": [], "preset_links": [],
    "client_links": [], "client_link_visits": [],
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


def плохо(текст):
    НАХОДКИ.append(текст)


def спросить(стр, js, *арг):
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:130])
        return None


# Что видно человеку: текст примечания и погашено ли оно глазом.
ВИДНО = """() => {
  const из = {};
  [...document.querySelectorAll('.note-item')].forEach(э => {
    const т = (э.innerText || '').replace(/\\s+/g, ' ').trim();
    if (т) из[т] = !э.classList.contains('note-hidden');
  });
  return { примечания: из, ключи: [...hiddenNotes] };
}"""



# Прятать надо так, как прячет человек, — нажатием по глазу. Иначе проба
# строит ключ сама, и на сборке без правки падает с ошибкой вместо того,
# чтобы показать сам дефект.
ГЛАЗ = """(текст) => {
  const кусок = (текст || '').slice(0, 30);
  const строка = [...document.querySelectorAll('.note-item')]
    .find(э => (э.innerText || '').includes(кусок));
  if (!строка) return false;
  const кнопка = строка.querySelector('.note-eye-btn');
  if (!кнопка) return false;
  кнопка.click();
  return true;
}"""


def спрятать(стр, текст):
    if not спросить(стр, ГЛАЗ, текст):
        плохо("глаза у примечания не нашлось — прятать нечем")


def страница(бр, порт, память=None):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
    if память is not None:
        стр.add_init_script(
            "try { localStorage.setItem('banya_msk_hidden_notes_v1', "
            + json.dumps(json.dumps(память, ensure_ascii=False)) + "); } catch (e) {}")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    спросить(стр, """() => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      window._sbProfile = { role: 'admin', full_name: 'Проба' };
    }""")
    return стр


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

            # ── Спрятанное в каркасе не прячется в брусе ──
            стр = страница(бр, порт)
            каркасПервое = спросить(стр, "() => (SECTION_NOTES.paint || [])[0] || null")
            if not каркасПервое:
                плохо("в каркасе нет примечаний покраски — прятать нечего, "
                      "проба мерила бы вхолостую")
            # Прячем нажатием по глазу, а не своим ключом: проба, которая
            # сама строит ключ, на прежней сборке просто падает и молчит о
            # главном — что спрятанное в каркасе гасит чужое в брусе.
            спрятать(стр, каркасПервое)
            к = спросить(стр, ВИДНО) or {}
            если_видно = (к.get("примечания") or {})
            спрятано = [т for т, видно in если_видно.items()
                        if not видно and каркасПервое and каркасПервое[:40] in т]
            if not спрятано:
                плохо("примечание в каркасе не спряталось — прятать научились не тем ключом")

            брусПервое = спросить(стр, """async () => {
              await switchTech('glulam');
              await new Promise(r => setTimeout(r, 1300));
              return (SECTION_NOTES.paint || [])[0] || null;
            }""")
            б = спросить(стр, ВИДНО) or {}
            прим = б.get("примечания") or {}
            чужое = [т for т, видно in прим.items()
                     if not видно and брусПервое and брусПервое[:40] in т]
            if not брусПервое:
                плохо("в брусе нет примечаний покраски — сравнивать не с чем")
            elif чужое:
                плохо("спрятанное в каркасе спрятало чужое примечание в брусе: «"
                      + чужое[0][:70] + "» — метки технологий не разделены")

            # То же самое в листе для печати: туда примечания уходят к клиенту.
            лист = спросить(стр, """async (первое) => {
              const и = PROJECTS.findIndex(x => x && x[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              const оп = OPTIONS.find(o => o.section === 'paint' && !o.included);
              if (оп) checkedOptions[оп.id] = true;
              try { calc(); } catch (e) {}
              openPrintPreview();
              await new Promise(r => setTimeout(r, 900));
              const л = document.getElementById('printDoc');
              const т = л ? л.innerText : '';
              return { есть: первое ? т.includes(первое) : null, длина: т.length };
            }""", брусПервое)
            if лист and лист.get("длина") and лист.get("есть") is False:
                плохо("в листе бруса пропало примечание, спрятанное в каркасе — "
                      "у клиента не хватает строки, и заметно это только сверкой двух листов")
            стр.close()

            # ── Спрятанное в брусе остаётся спрятанным в брусе ──
            стр = страница(бр, порт)
            спросить(стр, """(ГЛАЗ) => { window.глазПримечания = eval('(' + ГЛАЗ + ')'); }""", ГЛАЗ)
            своё = спросить(стр, """async () => {
              await switchTech('glulam');
              await new Promise(r => setTimeout(r, 1300));
              const первое = (SECTION_NOTES.paint || [])[0] || null;
              глазПримечания(первое);
              await new Promise(r => setTimeout(r, 300));
              const до = [...document.querySelectorAll('.note-item')]
                .some(э => (э.innerText || '').includes((первое || '').slice(0, 30))
                        && э.classList.contains('note-hidden'));
              // Туда и обратно — отметка не должна потеряться.
              await switchTech('frame');
              await new Promise(r => setTimeout(r, 1300));
              await switchTech('glulam');
              await new Promise(r => setTimeout(r, 1300));
              const после = [...document.querySelectorAll('.note-item')]
                .some(э => (э.innerText || '').includes((первое || '').slice(0, 30))
                        && э.classList.contains('note-hidden'));
              return { первое, до, после };
            }""") or {}
            if not своё.get("до"):
                плохо("примечание бруса не спряталось в самом брусе")
            elif not своё.get("после"):
                плохо("отметка в брусе потерялась после перехода туда и обратно")
            стр.close()

            # ── Разовый перевод старых меток ──
            стр = страница(бр, порт, память=["paint_0", "steam_stove"])
            стар = спросить(стр, """() => {
              const первое = (SECTION_NOTES.paint || [])[0] || null;
              const спрятано = [...document.querySelectorAll('.note-item')]
                .some(э => (э.innerText || '').includes((первое || '').slice(0, 30))
                        && э.classList.contains('note-hidden'));
              return { ключи: [...hiddenNotes], спрятано, первое };
            }""") or {}
            ключи = стар.get("ключи") or []
            if "frame_paint_0" not in ключи:
                плохо(f"старая метка `paint_0` не переведена: {ключи}")
            if "paint_0" in ключи:
                плохо("старая метка осталась рядом с новой — прячет вслепую в обеих технологиях")
            if "steam_stove" not in ключи:
                плохо("метка без номера `steam_stove` переведена зря — она и так одна на обе")
            if not стар.get("спрятано"):
                плохо("после перевода примечание каркаса перестало прятаться — "
                      "перевели ключ и потеряли смысл")
            стр.close()

            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: скрытое примечание принадлежит своей технологии — в каркасе "
          "прячется своё, в брусе чужое остаётся на месте и на экране, и в листе; "
          "старые метки переведены без потери смысла.")


if __name__ == "__main__":
    главная()
