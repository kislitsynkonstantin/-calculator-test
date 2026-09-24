#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба журнала действий: заведение и правка комплектаций.

24.09.2026, Константин: «добавь в журнал действий действия по добавлению и
изменению комплектаций, чтобы можно было видеть, как и когда по ним идёт
процесс». До этого в журнал попадало только применение комплектации к
расчёту, а сама работа над комплектациями не оставляла следа.

Проба держит:

  • подход, а не нажатие: пока комплектации правят, строк в журнале нет;
    сводка приходит при закрытии окна или после 30 секунд тишины — и не
    раньше;
  • по строке на уровень: «Стандарт» изменён — что добавлено, что убрано;
    пустой прежде «Премиум» заведён — с ручной позицией и её ценой; уровни,
    которых не трогали, в журнал не идут вовсе;
  • «было» берётся из базы, поэтому отмеченная и тут же снятая опция в сводку
    не попадает;
  • строка комплектации не цепляет к себе открытый рядом пресет и его код;
  • правка, сделанная прямо перед замком, стоит в журнале до замка, а сам
    замок — отдельной строкой;
  • сборка по образцу — одна строка с именем образца, а не четыре сводки;
  • в журнале строки подписаны словами, а не голым ключом.

    python3 check_kit_log.py
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
ПРОЕКТ = "Проба 6×4"
ЧУЖОЙ = "Чужой 9×5"
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(найденные[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    класс.log_message = lambda *а, **к: None
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(текст):
    НАХОДКИ.append(текст)


def спросить(стр, js, *арг):
    """Вычисление, которое может не найти новой функции: на прежней версии файла
    проба должна показать все находки, а не упасть на первой."""
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:120])
        return None


def проект(имя, порядок):
    return {"product": "frame", "sort": порядок, "slug": имя, "name": имя,
            "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
            "floors": 1, "roof_type": "двускатная", "warm": True,
            "open_area": 10, "closed_area": 20, "facade_area": 60,
            "paint_area": 60, "roof_area": 40}


ТАБЛИЦЫ = {
    "pricing_projects": [проект(ПРОЕКТ, 1), проект(ЧУЖОЙ, 2)],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
    "project_kits": [], "project_kit_locks": [], "events": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}

ПОДГОТОВКА = """async (а) => {
  const беда = document.getElementById('pricingErrorScreen');
  if (беда) беда.style.display = 'none';
  const индекс = PROJECTS.findIndex(p => p[0] === а.проект);
  if (индекс < 0) return { беда: 'проекта нет в списке' };
  selectProjectOption(индекс);
  await new Promise(r => setTimeout(r, 400));
  // Опции берём из каталога самой страницы: на выдуманных именах сводка
  // сводила бы неизвестные ключи и проба зеленела бы, ничего не проверив.
  const ид = OPTIONS.filter(o => !o.included && o.status !== 'legacy' && KOMPL_ID_TO_NAME[o.id])
    .slice(0, 8).map(o => o.id);
  if (ид.length < 8) return { беда: 'в каталоге меньше восьми опций комплектаций' };
  const ключ = projectSlug(а.проект), ключЧужого = projectSlug(а.чужой);
  window.__ТАБЛИЦЫ.project_kits = [
    { project_key: ключ, name: 'Стандарт', option_ids: ид.slice(0, 5), base_off: [], custom_items: [] },
    { project_key: ключ, name: 'Комфорт', option_ids: [ид[0], ид[1], ид[6]], base_off: [], custom_items: [] },
    { project_key: ключ, name: 'Тёплый контур', option_ids: [], base_off: [], custom_items: [] },
    { project_key: ключ, name: 'Премиум', option_ids: [], base_off: [], custom_items: [] },
    { project_key: ключЧужого, name: 'Стандарт', option_ids: [ид[2], ид[3]], base_off: [], custom_items: [] },
  ];
  await loadKitsForCurrentProject();
  // Рядом открыт пресет с кодом: строка комплектации его цеплять не должна.
  window._activeSharedCode = '481516';
  return { ид, имена: ид.map(и => KOMPL_ID_TO_NAME[и]) };
}"""

СОБЫТИЯ = """() => (window.__ТАБЛИЦЫ.events || [])
  .filter(с => /^kit_(created|edited|cleared|seeded|locked|unlocked)$/.test(с.event_type))
  .map(с => ({ вид: с.event_type, проект: с.project_name, д: с.details }))"""


def ряды(событие):
    return {р["k"]: р for р in ((событие.get("д") or {}).get("rows") or [])}


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
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                "window.addEventListener('DOMContentLoaded', function () {\n"
                "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n"
                "});")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            готово = стр.evaluate(ПОДГОТОВКА, {"проект": ПРОЕКТ, "чужой": ЧУЖОЙ})
            if готово.get("беда"):
                плохо("подготовка не удалась: " + готово["беда"])
            else:
                проверить(стр, готово["имена"])
            важные = [о for о in ошибки if "supabase.co" not in о and "цены" not in о]
            for о in важные[:3]:
                плохо("ошибка страницы: " + о[:160])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: комплектации пишутся в журнал сводкой за подход — по строке на уровень, "
          "с добавленным, убранным и ручными позициями; нетронутые уровни молчат, "
          "пресет рядом не цепляется, правка стоит до замка, сборка по образцу — одной строкой.")


def проверить(стр, имена):
    # ── 1. Подход: три правки подряд, одна из них отменена тут же ──
    # Окно перечитывает комплектации из базы — править можно только после этого,
    # иначе правку затрёт само чтение.
    спросить(стр, "() => { openKompl(); switchKomplTab('editor'); }")
    стр.wait_for_timeout(1000)
    спросить(стр, """(и) => {
      const ст = KOMPL_CONFIGS.standart;
      ст.add(и[5]); ст.delete(и[0]);
      KOMPL_CUSTOM.push({ id: 'cu_проба', name: 'Навес по проекту', price: 12000, section: 'extra',
        kitChecked: { econom: false, standart: false, comfort: false, premium: true } });
      autoSaveKompl();
    }""", имена)
    стр.wait_for_timeout(1200)
    спросить(стр, """(и) => {
      const ст = KOMPL_CONFIGS.standart;
      ст.add(и[6]);
      ст.add(и[7]); autoSaveKompl();
    }""", имена)
    стр.wait_for_timeout(1200)
    спросить(стр, """(и) => { KOMPL_CONFIGS.standart.delete(и[7]); autoSaveKompl(); }""", имена)
    стр.wait_for_timeout(1200)
    рано = спросить(стр, СОБЫТИЯ) or []
    if рано:
        плохо(f"сводка пришла до конца подхода: {len(рано)} строк(и), пока окно открыто и пауза не вышла")

    спросить(стр, "() => closeKompl()")
    стр.wait_for_timeout(600)
    события = спросить(стр, СОБЫТИЯ) or []
    по_виду = {}
    for с in события:
        по_виду.setdefault((с["вид"], (с["д"] or {}).get("obj")), []).append(с)
    изм = по_виду.get(("kit_edited", "Стандарт"), [])
    if len(изм) != 1:
        плохо(f"«Стандарт»: ждали одну строку «изменена», пришло {len(изм)} — {события}")
    else:
        р = ряды(изм[0])
        доб = (р.get("Добавлены") or {}).get("b", "").split("\n")
        убр = (р.get("Убраны") or {}).get("b", "").split("\n")
        if sorted(доб) != sorted([имена[5], имена[6]]):
            плохо(f"«Стандарт»: «Добавлены» — {доб}, ждали {[имена[5], имена[6]]}; "
                  "отмеченная и тут же снятая опция в сводку попадать не должна")
        if убр != [имена[0]]:
            плохо(f"«Стандарт»: «Убраны» — {убр}, ждали {[имена[0]]}")
        поз = р.get("Позиций") or {}
        if (поз.get("a"), поз.get("b")) != ("5", "6"):
            плохо(f"«Стандарт»: «Позиций» {поз.get('a')} → {поз.get('b')}, ждали 5 → 6")
        if изм[0]["проект"] != ПРОЕКТ:
            плохо(f"строка комплектации записана на проект «{изм[0]['проект']}», а не «{ПРОЕКТ}»")
        if (изм[0]["д"] or {}).get("presetCode") or (изм[0]["д"] or {}).get("preset"):
            плохо("строка комплектации цепляет открытый рядом пресет: " + json.dumps(изм[0]["д"], ensure_ascii=False)[:160])
    зав = по_виду.get(("kit_created", "Премиум"), [])
    if len(зав) != 1:
        плохо(f"«Премиум»: ждали одну строку «заведена», пришло {len(зав)}")
    else:
        ручные = (ряды(зав[0]).get("Ручные добавлены") or {}).get("b", "").replace(" ", " ")
        if "Навес по проекту" not in ручные or "12 000" not in ручные:
            плохо(f"«Премиум»: ручная позиция записана без имени или цены — «{ручные}»")
    лишние = [с for с in события if (с["д"] or {}).get("obj") in ("Комфорт", "Тёплый контур")]
    if лишние:
        плохо(f"в журнал попали нетронутые уровни: {[ (с['вид'], с['д'].get('obj')) for с in лишние ]}")

    # ── 2. Пауза: без закрытия окна сводка приходит через 30 секунд, не раньше ──
    стр.clock.install()
    было = len(спросить(стр, СОБЫТИЯ) or [])
    спросить(стр, "() => { openKompl(); switchKomplTab('editor'); }")
    стр.clock.run_for(1000)
    стр.wait_for_timeout(500)
    спросить(стр, """() => {
      const ci = KOMPL_CUSTOM.find(x => x.id === 'cu_проба'); if (ci) ci.price = 15000; autoSaveKompl(); }""")
    стр.clock.run_for(700)
    стр.wait_for_timeout(500)
    стр.clock.run_for(28000)
    стр.wait_for_timeout(300)
    if len(спросить(стр, СОБЫТИЯ) or []) != было:
        плохо("сводка пришла раньше 30 секунд тишины")
    стр.clock.run_for(3000)
    стр.wait_for_timeout(500)
    после = спросить(стр, СОБЫТИЯ) or []
    нов = после[было:]
    if len(нов) != 1 or нов[0]["вид"] != "kit_edited":
        плохо(f"после 30 секунд тишины ждали одну строку «изменена», пришло: {[с['вид'] for с in нов]}")
    else:
        правка = (ряды(нов[0]).get("Ручные изменены") or {}).get("b", "").replace(" ", " ")
        if "12 000" not in правка or "15 000" not in правка:
            плохо(f"правка цены ручной позиции записана без «было → стало»: «{правка}»")

    # ── 3. Замок: правка прямо перед ним стоит в журнале раньше ──
    было = len(спросить(стр, СОБЫТИЯ) or [])
    спросить(стр, """(и) => { KOMPL_CONFIGS.comfort.add(и[2]); autoSaveKompl(); }""", имена)
    стр.clock.run_for(700)
    стр.wait_for_timeout(500)
    спросить(стр, "async () => { await toggleKitLock(); }")
    стр.wait_for_timeout(500)
    нов = [с["вид"] for с in (спросить(стр, СОБЫТИЯ) or [])[было:]]
    if нов != ["kit_edited", "kit_locked"]:
        плохо(f"замок: ждали «изменена», затем «закрыты», пришло {нов}")
    спросить(стр, "async () => { await toggleKitLock(); }")
    стр.wait_for_timeout(400)
    if (спросить(стр, СОБЫТИЯ) or [{}])[-1].get("вид") != "kit_unlocked":
        плохо("снятие замка не записано в журнал")

    # ── 4. Сборка по образцу — одна строка ──
    было = len(спросить(стр, СОБЫТИЯ) or [])
    спросить(стр, """async () => { openKompl(); switchKomplTab('editor'); await openKomplSeedDialog(); }""")
    стр.wait_for_timeout(400)
    индекс = спросить(стр, "(имя) => _komplSeedSources.findIndex(s => s.name === имя)", ЧУЖОЙ)
    if индекс is None or индекс < 0:
        плохо("сборка: в списке образцов нет проекта с комплектациями")
    else:
        спросить(стр, "(и) => applyKomplSeed(и)", индекс)
        стр.clock.run_for(700)
        стр.wait_for_timeout(500)
        спросить(стр, "() => { closeKomplSeedDialog(); closeKompl(); }")
        стр.wait_for_timeout(500)
        нов = (спросить(стр, СОБЫТИЯ) or [])[было:]
        if [с["вид"] for с in нов] != ["kit_seeded"]:
            плохо(f"сборка по образцу: ждали одну строку «собраны по образцу», пришло {[с['вид'] for с in нов]}")
        elif (ряды(нов[0]).get("Образец") or {}).get("b") != ЧУЖОЙ:
            плохо("сборка по образцу записана без имени образца")

    # ── 5. В журнале — слова, а не ключи ──
    подписи = спросить(стр, """() => ['kit_created','kit_edited','kit_cleared','kit_seeded','kit_locked','kit_unlocked']
      .filter(к => !AL_ВИДЫ[к])""")
    if подписи:
        плохо(f"у событий нет подписи в журнале, строка покажет голый ключ: {подписи}")

    # ── 6. Как строки выглядят в самом журнале ──
    стр.clock.run_for(1000)
    спросить(стр, """async () => {
      // В базе время ставит сама база; заглушка его не знает, а журнал без
      // времени строку за период не покажет.
      const т = Date.now();
      (window.__ТАБЛИЦЫ.events || []).forEach((с, н) => {
        if (!с.created_at) с.created_at = new Date(т - 60000 + н * 1000).toISOString();
        if (!с.id) с.id = 'e' + н;
      });
      openActionLog();
    }""")
    стр.clock.run_for(1500)
    стр.wait_for_timeout(1200)
    текст = спросить(стр, "() => (document.getElementById('actionLogOverlay') || {}).innerText || ''") or ""
    for подпись in ("Комплектация изменена", "Комплектация заведена",
                    "Комплектации закрыты и показаны менеджерам", "Комплектации собраны по образцу"):
        if подпись not in текст:
            плохо(f"в окне журнала нет строки «{подпись}»")
    for ширина in (1440, 390):
        стр.set_viewport_size({"width": ширина, "height": 900})
        стр.wait_for_timeout(300)
        стр.screenshot(path=str(pathlib.Path(__file__).parent / f"журнал-комплектации-{ширина}.png"))


if __name__ == "__main__":
    главная()
