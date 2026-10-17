#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пустая этажность и форма кровли проекта — «Проверка» просит указать, редактор даёт заполнить.

Константин 17.10.2026, на предложение проставить всем проектам бруса один
этаж: «Всем не надо ставить этаж. Заполним этажность и форму кровли, где нет.
Там где нет, просто предлагай заполнить в правках, когда менеджер его
открывает. И когда нажимает на пункт — перекидывать на поле заполнения в
редакторе проекта». В каталоге у бруса этажности нет ни у одного проекта,
формы кровли — у 17 из 46; у каркаса этажности нет у 9, формы — у 10.

Проект каталога в редакторе — только для чтения; пустые поля в нём теперь
можно заполнить, и запись идёт в каталог функцией базы fill_project_gaps,
которая пишет лишь в пустые поля. Проба держит:
  • у проекта без этажности и формы — один пункт «Указать этажность и форму
    кровли проекта», адрес — поле этажности в редакторе; без одного из них —
    пункт про другое; у заполненного — пункта нет;
  • переход по пункту открывает редактор, пустое поле открыто, в фокусе и
    подсвечено, остальные поля закрыты, кнопка — «Сохранить»;
  • сохранение зовёт функцию базы с технологией, slug проекта, «1.5» и
    «одн-ая»; проект получает этажность и форму, пункт уходит, редактор
    закрыт; неверная этажность до базы не доходит; отказ базы ничего не
    меняет;
  • заполненный проект каталога — редактор только для чтения, как был;
  • свой проект правится как прежде, кнопка — «Применить»;
  • у бруса — тот же пункт.

    python3 check_project_gaps.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


ФИКСТУРА = json.loads((pathlib.Path(__file__).parent / "kit_fixture.json").read_text(encoding="utf-8"))
for п in ФИКСТУРА["pricing_projects"]:
    if "6×6" in п["name"]:
        п["floors"] = None; п["roof_type"] = None
ТАБЛИЦЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
           "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
# Функция базы — как в миграции: пишет только в пустые поля.
RPC = """window.__ВЫЗОВЫ = []; window.__RPC = window.__RPC || {};
window.__RPC.fill_project_gaps = (а) => { window.__ВЫЗОВЫ.push(а); if (window.__ОТКАЗ) return null;
  const р = (window.__ТАБЛИЦЫ.pricing_projects || []).find(x => x.product === а.p_product && x.slug === а.p_slug); if (!р) return null;
  if (р.floors == null || String(р.floors).trim() === '') р.floors = а.p_floors || р.floors;
  if (!р.roof_type) р.roof_type = а.p_roof || р.roof_type;
  return Object.assign({}, р); };"""
ВЫБРАТЬ = """async (часть) => { const и = filteredProjects.findIndex(х => х[0].includes(часть)); selectProjectOption(и);
  await new Promise(r => setTimeout(r, 300)); calc(); }"""
ПУНКТ = """() => { const з = проверкаПоЧекЛисту().замечания.find(з => /^Указать (этажность|форму кровли)/.test(з.т)); return з ? { т: з.т, эл: з.эл } : null; }"""
РЕДАКТОР = """() => { const ф = document.getElementById('editProjectForm'), к = [...ф.querySelectorAll('.btn-confirm-edit')].filter(к => к.offsetParent);
  const откр = [...ф.querySelectorAll('input, select, .roof-btn')].filter(э => !э.disabled && э.offsetParent).map(э => э.id || ('кровля:' + э.dataset.roof));
  return { открыт: ф.classList.contains('open'), открыто: откр, фокус: document.activeElement && (document.activeElement.id || document.activeElement.dataset.roof || ''),
    кнопка: к.map(к => к.textContent.trim()).join('|'), подсветка: !!document.querySelector('#editProjectForm .pc-flash-box') }; }"""


def прогон(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки, тосты = [], []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ); стр.add_init_script(RPC)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; window.__тосты = []; const с = showToast; window.showToast = (т, д) => { window.__тосты.push(т); return с(т, д); }; }")

    стр.evaluate(ВЫБРАТЬ, "6×6")
    п = стр.evaluate(ПУНКТ)
    факт(п and п["т"] == "Указать этажность и форму кровли проекта" and п["эл"] == "редактор:этажи", f"нет обоих — один пункт, ведёт к этажности: {п}")
    стр.evaluate("() => кРазделуИзПроверки('project', 'редактор:этажи')"); стр.wait_for_timeout(250)
    р = стр.evaluate(РЕДАКТОР)
    факт(р["открыт"] and sorted(р["открыто"]) == sorted(["epFloors", "кровля:двускатная", "кровля:односкатная", "кровля:плоская"]),
         f"редактор открыт, открыты только этажность и форма кровли: {р['открыто']}")
    факт(р["фокус"] == "epFloors" and р["подсветка"], f"пустое поле в фокусе и подсвечено: фокус {р['фокус']}, подсветка {р['подсветка']}")
    факт(р["кнопка"] == "Сохранить", f"кнопка — «Сохранить»: «{р['кнопка']}»")
    под = стр.evaluate("() => { const к = document.getElementById('epTopSaveBtn').getBoundingClientRect(), п = document.getElementById('epNote').getBoundingClientRect(), с = document.getElementById('epOptionSections').getBoundingClientRect(); return [Math.round(к.top - п.bottom), к.bottom < с.top]; }")
    факт(под[1] and 0 <= под[0] < 80, f"«Сохранить» — под полями, выше списка цен опций: отступ {под[0]} px")
    # Неверная этажность до базы не доходит.
    стр.fill("#epFloors", "3"); стр.click("#editProjectForm .btn-confirm-edit >> visible=true"); стр.wait_for_timeout(200)
    факт(not стр.evaluate("() => window.__ВЫЗОВЫ.length") and "Этажей — 1, 1,5 или 2" in стр.evaluate("() => window.__тосты"),
         f"этажность 3 — отказ без вызова базы: {стр.evaluate('() => window.__тосты')}")
    # Отказ базы ничего не меняет.
    стр.evaluate("() => { window.__ОТКАЗ = true; }"); стр.fill("#epFloors", "1.5")
    стр.click("#epRoofField .roof-btn[data-roof='односкатная']"); стр.click("#editProjectForm .btn-confirm-edit >> visible=true"); стр.wait_for_timeout(300)
    факт(стр.evaluate("() => selectedProject[4] == null && !selectedProject[5] && document.getElementById('editProjectForm').classList.contains('open')"),
         "база отказала — проект прежний, редактор открыт")
    # Сохранение.
    стр.evaluate("() => { window.__ОТКАЗ = false; window.__ВЫЗОВЫ = []; }")
    стр.click("#editProjectForm .btn-confirm-edit >> visible=true"); стр.wait_for_timeout(400)
    в = стр.evaluate("() => window.__ВЫЗОВЫ")
    факт(в == [{"p_product": "frame", "p_slug": "proba-dom-2", "p_floors": "1.5", "p_roof": "одн-ая"}], f"функция базы — технология, slug, «1.5», «одн-ая»: {в}")
    итог = стр.evaluate("() => ({ этажи: selectedProject[4], форма: формаКровли(selectedProject), открыт: document.getElementById('editProjectForm').classList.contains('open') })")
    факт(итог == {"этажи": 1.5, "форма": "односкатная", "открыт": False}, f"проект получил этажность и форму, редактор закрыт: {итог}")
    факт(стр.evaluate(ПУНКТ) is None, "пункт ушёл")
    # Заполненный проект каталога — только для чтения.
    стр.evaluate(ВЫБРАТЬ, "8×8"); стр.evaluate("() => openEditProject()"); стр.wait_for_timeout(150)
    р = стр.evaluate(РЕДАКТОР)
    факт(not р["открыто"] and not р["кнопка"] and стр.evaluate(ПУНКТ) is None, f"заполненный проект — пункта нет, редактор только для чтения: {р}")
    стр.evaluate("() => closeEditProject()")
    # Только форма пуста — пункт и открыто только её поле.
    стр.evaluate("() => { selectedProject[5] = null; }")
    п = стр.evaluate(ПУНКТ)
    факт(п and п["т"] == "Указать форму кровли проекта" and п["эл"] == "редактор:кровля", f"пуста только форма — пункт про неё: {п}")
    стр.evaluate("() => кРазделуИзПроверки('project', 'редактор:кровля')"); стр.wait_for_timeout(250)
    р = стр.evaluate(РЕДАКТОР)
    факт("epFloors" not in р["открыто"] and "кровля:плоская" in р["открыто"] and р["фокус"] in ("двускатная",), f"открыта только форма, фокус на ней: {р}")
    стр.evaluate("() => { closeEditProject(); selectedProject[5] = 'двус-ая'; }")
    # Свой проект — как прежде.
    стр.evaluate("""() => { const п = ['Свой проба 7×7', 3000000, 3200000, 3400000, '1', 'двус-ая', 40, 0, 0, null, null, null];
      п._tech = currentTech; п._params = { floorType: '1', source: 'manual' }; customProjects.push(п); populateProjectSelect(''); }""")
    стр.evaluate(ВЫБРАТЬ, "Свой проба"); стр.evaluate("() => кРазделуИзПроверки('project', 'редактор:кровля')"); стр.wait_for_timeout(250)
    р = стр.evaluate(РЕДАКТОР)
    факт(р["кнопка"] == "Применить" and "epPrice150" in р["открыто"], f"свой проект правится как прежде: {р['кнопка']}, открыто {len(р['открыто'])}")
    стр.evaluate("() => closeEditProject()")
    # Брус: у проекта нет этажности.
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 900)); }")
    стр.evaluate("() => { window.__ТАБЛИЦЫ.pricing_projects.forEach(x => { if (x.product === 'glulam') x.floors = null; }); }")
    стр.evaluate(ВЫБРАТЬ, "Брусовая проба 8×8"); стр.evaluate("() => { selectedProject[4] = null; }")
    п = стр.evaluate(ПУНКТ)
    факт(п and п["т"] == "Указать этажность проекта", f"брус без этажности — пункт: {п}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    for т in ОТЧЁТ:
        print("    ок ", т)
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: пустые этажность и форма кровли — пункт «Проверки», переход к полю редактора, запись в каталог только пустых полей.")


if __name__ == "__main__":
    главная()
