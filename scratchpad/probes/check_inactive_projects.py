#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Неактивный проект не попадает в список проектов.

Константин 09.10.2026: «Если коннектор не даёт удалять. Сделай неактивными» —
про «Sandy Wood» и «Гессен» 4х8 у клеёного бруса. У проектов появилась колонка
status; 'legacy' значит «неактивен»: строка и цены в базе остаются, в список
проектов калькулятора он не попадает.

Проба смотрит на список проектов и на выпадающий список на экране:

  • неактивного проекта нет ни в PROJECTS, ни в выпадающем списке, ни в
    поиске по названию;
  • активные проекты на месте;
  • у каркаса без пометки всё по-прежнему.

    python3 check_inactive_projects.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СНЯТ = "Брус снятый проба"


def таблицы():
    т = г.таблицы()
    брус = [п for п in т["pricing_projects"] if п["product"] == "glulam"][0]
    т["pricing_projects"].append(dict(брус, slug="kb_snyat", name=СНЯТ, sort=5, status="legacy"))
    return т


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ош = []
            стр.on("pageerror", lambda e: ош.append(str(e)))
            стр.add_init_script(г.ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                                + json.dumps(таблицы(), ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            р = стр.evaluate("""async (снят) => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
              await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
              const вСписке = PROJECTS.map(p => p[0]);
              toggleProjectDropdown(); await new Promise(r => setTimeout(r, 300));
              const наЭкране = document.getElementById('projectSelectDropdown').textContent;
              toggleProjectDropdown();
              const поиск = document.getElementById('projectSearch'); поиск.value = 'снятый'; filterProjects();
              await new Promise(r => setTimeout(r, 300));
              const вПоиске = document.getElementById('projectSelectDropdown').textContent;
              поиск.value = ''; filterProjects();
              await switchTech('frame'); await new Promise(r => setTimeout(r, 400));
              return { вСписке, наЭкране: наЭкране.includes(снят), вПоиске: вПоиске.includes(снят),
                       каркас: PROJECTS.map(p => p[0]) }; }""", СНЯТ)
            бр.close()
    finally:
        с.shutdown()
    if СНЯТ in р["вСписке"] or р["наЭкране"] or р["вПоиске"]:
        НАХОДКИ.append(f"неактивный проект виден: в списке {СНЯТ in р['вСписке']}, на экране {р['наЭкране']}, в поиске {р['вПоиске']}")
    if "Брус проба 6×6" not in р["вСписке"]:
        НАХОДКИ.append(f"активный проект бруса пропал: {р['вСписке']}")
    if "Каркас проба 6×4" not in р["каркас"]:
        НАХОДКИ.append(f"у каркаса пропал проект: {р['каркас']}")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"ошибка страницы: {о[:160]}")
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print(f"Чисто: неактивного проекта нет ни в списке, ни на экране, ни в поиске; активные на месте ({len(р['вСписке'])}), каркас без изменений.")


if __name__ == "__main__":
    главная()
