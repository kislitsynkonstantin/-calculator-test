#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ручной проект клеёного бруса считает базу сам.

24.09.2026: Константин прислал вкладку «Клееный брус» таблицы расчёта, план с
четырьмя вопросами согласован им и Анатолием: ставка — как в таблице, без
округления; остекление — 4 % от собственной цены каждого сечения; остекление
и «без отделки» — от одной и той же суммы; верхняя граница строки таблицы
включена. 25.09.2026 Анатолий: остекление входит всегда, без галочки, —
«у нас нет не панорамных домов».

Ставки здесь выдуманные, но той же формы, что в базе: настоящие цены в
публичный репозиторий не кладутся. Ожидаемые числа проба считает сама, своим
кодом по правилу таблицы, — страница с ним обязана совпасть до рубля.

Проба держит:

  • у бруса со ставками видны этажность, террасы и галочка «Без отделки»,
    галочки остекления нет, подсказка говорит «рассчитывается автоматически,
    с панорамным остеклением»;
  • три цены сходятся с правилом — остекление всегда в цене — на границах
    строк (10, 10,5, 30, 30,5 м²), с террасами и без отделки;
  • процент в подписи «Без отделки» берётся из базы;
  • площади фасада и кровли, вписанные над списком проектов, форма берёт сама;
  • без тёплого контура «Без отделки» ложится на цену из «Взять из
    выбранного» или вписанную руками, а не обнуляет её; остекление к ним не
    прибавляется — это уже цена дома; снятая галочка возвращает цену до рубля;
  • без ставок в базе форма ведёт себя по-старому: поля расчёта скрыты,
    цены не затираются;
  • ставки, заведённые при открытой странице, форма дочитывает сама при
    следующем открытии — без перезагрузки и не трогая вписанную цену;
  • заведённый проект помнит «Без отделки» в базе; окно «Редактировать»
    показывает галочку, подписи сечений бруса, а снятая галочка возвращает
    цену и уходит в базу вместе с правкой;
  • у каркаса поправок бруса нет, «Женева» на месте.

    python3 check_cp_glulam.py
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

СТАВКИ = {
    "1": [{"max": 10, "rate": 200000}, {"max": 30, "rate": 150000}, {"max": None, "rate": 100000}],
    "mansard": [{"max": None, "rate": 90000}],
    "1.5": [{"max": None, "rate": 95000}],
    "2": [{"max": 50, "rate": 97000}, {"max": None, "rate": 93000}],
}
КОЭФ = {"base": 1, "sections": [0.9, 1, 1.155], "terrace_closed": 30000,
        "terrace_open": 20000, "glazing": 0.04, "no_finish": 0.08}


def ожидание(этажность, тёплый, открытая=0, крытая=0, без=False):
    строки = СТАВКИ.get(этажность) or СТАВКИ["1"]
    ставка = строки[-1]["rate"]
    for с in строки:
        if с["max"] is None or тёплый <= с["max"]:
            ставка = с["rate"]
            break
    поправка = 1 + КОЭФ["glazing"] - (КОЭФ["no_finish"] if без else 0)
    террасы = крытая * КОЭФ["terrace_closed"] + открытая * КОЭФ["terrace_open"]
    # Округление как у Math.round: половина — вверх.
    return [int((тёплый * ставка * д + террасы) * поправка + 0.5) for д in КОЭФ["sections"]]


def проект(продукт, имя, порядок):
    return {"product": продукт, "sort": порядок, "slug": имя, "name": имя,
            "price_100": 2000000, "price_150": 2200000, "price_200": 2500000,
            "floors": None, "roof_type": "двускатная", "warm": None,
            "open_area": None, "closed_area": None, "facade_area": None,
            "paint_area": None, "roof_area": None}


def таблицы(со_ставками):
    т = {
        "pricing_projects": [проект("frame", "Каркас проба 6×4", 1), проект("glulam", "Брус проба 6×6", 1)],
        "pricing_matrix": [{"product": "glulam", "project_slug": "Брус проба 6×6",
                            "option_id": "kb_проба", "price": 12000}],
        "pricing_options": [{"product": "glulam", "option_id": "kb_проба", "name": "Проба опция",
                             "section": "extra", "included": False, "price": 10000,
                             "formula": None, "status": None, "sort": 1}],
        "pricing_sections": [],
        "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
        "custom_projects": [], "events": [],
    }
    т["pricing_projects"][0].update({"floors": "1", "warm": 24})
    if со_ставками:
        т["pricing_rates"] = [{"product": "glulam", "key": "cp_rates", "value": СТАВКИ},
                              {"product": "glulam", "key": "cp_coef", "value": КОЭФ}]
    return т


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
    к.log_message = lambda *а, **кк: None
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


def спросить(стр, js, *арг):
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:120])
        return None


def страница(бр, порт, со_ставками, ширина=1440):
    стр = бр.new_page(viewport={"width": ширина, "height": 1000})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(таблицы(со_ставками), ensure_ascii=False) + ");\n"
        "window.addEventListener('DOMContentLoaded', function () {\n"
        "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n"
        "});")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    спросить(стр, """async () => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      await switchTech('glulam');
      await new Promise(r => setTimeout(r, 400));
      const и = PROJECTS.findIndex(p => p[0] === 'Брус проба 6×6');
      if (и >= 0) selectProjectOption(и);
      await new Promise(r => setTimeout(r, 300));
    }""")
    return стр, ошибки


ВВЕСТИ = """(а) => {
  const з = (ид, в) => { const э = document.getElementById(ид); if (э) э.value = в; };
  з('cpFloorType', а.этаж); з('cpWarm', а.тёплый); з('cpOpen', а.откр || ''); з('cpClosed', а.крыт || '');
  const о = document.getElementById('cpGlazing'); if (о) о.checked = !!а.ост;
  const б = document.getElementById('cpNoFinish'); if (б) б.checked = !!а.без;
  cpRecalcPrices();
  return ['cpPrice100','cpPrice150','cpPrice200'].map(ид =>
    Number(String(document.getElementById(ид).value).replace(/[^\\d]/g, '')) || 0);
}"""

ВИДНО = """(ид) => { const э = document.getElementById(ид); return !!(э && э.offsetParent); }"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

            # ── со ставками ──
            стр, ошибки = страница(бр, порт, True)
            спросить(стр, "() => { kbSetArea('fasad', '45'); kbSetArea('roof', '32'); toggleCustomProjectForm(); }")
            стр.wait_for_timeout(300)
            пл = спросить(стр, "() => [document.getElementById('cpFasadArea').value, document.getElementById('cpRoofArea').value]") or []
            if пл != ["45", "32"]:
                плохо(f"площади фасада и кровли сверху не дошли до формы: {пл}")
            for ид, имя in (("cpFloorTypeField", "этажность"), ("cpOpenField", "открытая терраса"),
                            ("cpClosedField", "крытая терраса"), ("cpGlulamAdjField", "поправки")):
                if not спросить(стр, ВИДНО, ид):
                    плохо(f"у бруса со ставками не видно поля «{имя}»")
            for ид, имя in (("cpZhenevaField", "Женева"), ("cpPaintAreaField", "площадь покраски")):
                if спросить(стр, ВИДНО, ид):
                    плохо(f"у бруса видно каркасное поле «{имя}»")
            подсказка = спросить(стр, "() => document.getElementById('cpPricesHintAuto').textContent") or ""
            if "автоматически" not in подсказка:
                плохо(f"подсказка у цен бруса со ставками: «{подсказка}»")
            подписи = спросить(стр, "() => cpNoFinishPct.textContent") or ""
            if подписи != "(−8%)":
                плохо(f"процент в подписи «Без отделки» не из базы: «{подписи}»")
            if спросить(стр, "() => !!document.getElementById('cpGlazing')"):
                плохо("у бруса осталась галочка остекления — оно входит всегда")
            if "остеклением" not in (спросить(стр, "() => cpPricesHintAuto.textContent") or ""):
                плохо("подсказка у цен бруса не говорит, что остекление в цене")

            случаи = [
                ("1", 10, 0, 0, False, False), ("1", 10.5, 0, 0, False, False),
                ("1", 30, 0, 0, False, False), ("1", 30.5, 0, 0, False, False),
                ("1", 25, 12, 8, False, False), ("1", 25, 0, 0, True, False),
                ("1", 25, 0, 0, False, True), ("1", 25, 6, 4, True, True),
                ("mansard", 64, 0, 10, False, False), ("1.5", 88, 0, 0, True, False),
                ("2", 50, 0, 0, False, False), ("2", 51, 0, 0, False, False),
            ]
            for этаж, тёплый, откр, крыт, ост, без in случаи:
                есть = спросить(стр, ВВЕСТИ, {"этаж": этаж, "тёплый": str(тёплый), "откр": str(откр or ""),
                                                "крыт": str(крыт or ""), "ост": ост, "без": без})
                надо = ожидание(этаж, тёплый, откр, крыт, без)
                if есть != надо:
                    плохо(f"{этаж} этаж, {тёплый} м², терр. {откр}/{крыт}, остекл. {ост}, без отд. {без}: "
                          f"страница {есть}, правило {надо}")
            # ── без контура: поправки ложатся на цену прайса и вписанную ──
            ЦЕНЫ = "() => ['cpPrice100','cpPrice150','cpPrice200'].map(ид => Number(String(document.getElementById(ид).value).replace(/[^\\d]/g, '')) || 0)"
            ГАЛКИ = "(б) => { cpNoFinish.checked = б; cpRecalcPrices(); }"
            спросить(стр, "() => { ['cpWarm','cpOpen','cpClosed','cpPrice100','cpPrice150','cpPrice200'].forEach(ид => document.getElementById(ид).value = ''); cpNoFinish.checked = false; cpCopyFromSelected(); }")
            прайс = [2000000, 2200000, 2500000]
            if спросить(стр, ЦЕНЫ) != прайс:
                плохо(f"«Взять из выбранного» дало {спросить(стр, ЦЕНЫ)}, ждали цены прайса {прайс}")
            for б, множ in ((True, 0.92), (False, 1), (True, 0.92), (False, 1)):
                спросить(стр, ГАЛКИ, б)
                надо = [int(ц * множ + 0.5) for ц in прайс]
                есть = спросить(стр, ЦЕНЫ)
                if есть != надо:
                    плохо(f"без контура, без отделки {б}: цены {есть}, ждали {надо} — "
                          "поправка ложится на цену прайса, а не обнуляет её и не добавляет остекление")
            спросить(стр, "() => { cpPrice150.value = '1 000 000'; cpЦенаВписана(1); }")
            спросить(стр, ГАЛКИ, True)
            if (спросить(стр, ЦЕНЫ) or [0, 0])[1] != 920000:
                плохо(f"вписанная руками цена 1 000 000 без отделки стала {(спросить(стр, ЦЕНЫ) or [0, 0])[1]}, ждали 920 000")
            спросить(стр, ГАЛКИ, False)
            if (спросить(стр, ЦЕНЫ) or [0, 0])[1] != 1000000:
                плохо("снятая галочка не вернула вписанную цену к 1 000 000")

            for w in (1440, 390):
                стр.set_viewport_size({"width": w, "height": 1000})
                стр.wait_for_timeout(200)
                спросить(стр, ВВЕСТИ, {"этаж": "1", "тёплый": "25", "откр": "6", "крыт": "4", "ост": True, "без": False})
                стр.locator("#customProjectForm").screenshot(
                    path=str(pathlib.Path(__file__).parent / f"ручной-брус-{w}.png"))
            # ── заведённый проект помнит «Без отделки», и окно правки его показывает ──
            спросить(стр, """() => {
              ['cpName','cpWarm','cpOpen','cpClosed','cpPrice100','cpPrice150','cpPrice200'].forEach(ид => document.getElementById(ид).value = '');
              cpNoFinish.checked = false; _cpОснова = null;
              cpCopyFromSelected(); cpNoFinish.checked = true; cpRecalcPrices();
              cpName.value = 'Проба ручной'; confirmCustomProject();
            }""")
            стр.wait_for_timeout(400)
            строка = (спросить(стр, "() => (window.__ТАБЛИЦЫ.custom_projects || []).slice(-1)[0] || null") or {})
            if not (строка.get("params") or {}).get("noFinish"):
                плохо(f"ручной проект записан в базу без отметки «Без отделки»: params = {строка.get('params')}")
            if строка.get("price_150") != int(2200000 * 0.92 + 0.5):
                плохо(f"ручной проект записан с ценой {строка.get('price_150')}, ждали {int(2200000 * 0.92 + 0.5)}")
            окно = спросить(стр, """async () => {
              const все = [...PROJECTS, ...customProjects];
              const и = все.findIndex(p => p[0] === 'Проба ручной');
              if (и < 0) return { беда: 'проекта нет в списке' };
              selectProjectOption(и);
              await new Promise(r => setTimeout(r, 300));
              openEditProject();
              return { галочка: epNoFinish.checked, видно: !!epNoFinishField.offsetParent,
                       подпись: epPrice100Label.textContent, подсказка: epPricesHint.textContent,
                       база: epBaseSnapshot.textContent, цена: rawNum('epPrice150') };
            }""") or {}
            if окно.get("беда"):
                плохо("окно правки: " + окно["беда"])
            else:
                стр.locator("#editProjectForm").screenshot(
                    path=str(pathlib.Path(__file__).parent / "правка-бруса-1440.png"))
                if not (окно.get("видно") and окно.get("галочка")):
                    плохо(f"окно «Редактировать» не показывает, что стояло «Без отделки»: {окно}")
                if "125" not in (окно.get("подпись") or "") or "сечению бруса" not in (окно.get("подсказка") or ""):
                    плохо(f"в окне правки бруса подписи каркаса: «{окно.get('подпись')}», «{окно.get('подсказка')}»")
                if "100 мм" in (окно.get("база") or ""):
                    плохо(f"строка «Цены в базе» у бруса в миллиметрах утепления: «{окно.get('база')}»")
                спросить(стр, "() => { epNoFinish.checked = false; epБезОтделки(); }")
                вернулась = спросить(стр, "() => rawNum('epPrice150')")
                if вернулась != 2200000:
                    плохо(f"снятая в окне правки «Без отделки» вернула цену {вернулась}, ждали 2 200 000")
                спросить(стр, "() => confirmEditProject()")
                стр.wait_for_timeout(400)
                после = (спросить(стр, "() => (window.__ТАБЛИЦЫ.custom_projects || []).slice(-1)[0] || null") or {})
                if (после.get("params") or {}).get("noFinish") or после.get("price_150") != 2200000:
                    плохо(f"правка ручного проекта не дошла до базы: params {после.get('params')}, цена {после.get('price_150')}")

            # ── каркас: поправок бруса нет ──
            спросить(стр, "async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 400)); toggleCustomProjectForm(); }")
            стр.wait_for_timeout(300)
            if спросить(стр, ВИДНО, "cpGlulamAdjField"):
                плохо("у каркаса видны поправки бруса")
            if not спросить(стр, ВИДНО, "cpZhenevaField"):
                плохо("у каркаса пропала «Женева»")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                плохо("ошибка страницы: " + о[:160])
            стр.close()

            # ── без ставок: по-старому ──
            стр, ошибки = страница(бр, порт, False)
            спросить(стр, "() => toggleCustomProjectForm()")
            стр.wait_for_timeout(300)
            if спросить(стр, ВИДНО, "cpGlulamAdjField") or спросить(стр, ВИДНО, "cpFloorTypeField"):
                плохо("без ставок в базе у бруса видны поля расчёта, которые ни на что не влияют")
            цены = спросить(стр, """() => { cpPrice150.value = '1 234 567'; cpWarm.value = '30'; cpRecalcPrices();
              return cpPrice150.value; }""")
            if цены != "1 234 567":
                плохо(f"без ставок форма затёрла вписанную руками цену: «{цены}»")
            # Таблицу ставок завели, пока страница была открыта: форма
            # дочитывает её при следующем открытии сама, без перезагрузки, и
            # вписанную цену не трогает.
            спросить(стр, "(т) => { window.__ТАБЛИЦЫ.pricing_rates = т; toggleCustomProjectForm(true); toggleCustomProjectForm(); }",
                     таблицы(True)["pricing_rates"])
            стр.wait_for_timeout(600)
            if not спросить(стр, ВИДНО, "cpGlulamAdjField"):
                плохо("ставки появились в базе, но форма без перезагрузки их не дочитала")
            if спросить(стр, "() => cpPrice150.value") != "1 234 567":
                плохо("дочитав ставки, форма затёрла вписанную цену")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                плохо("ошибка страницы: " + о[:160])
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: у бруса со ставками форма считает три цены по правилу таблицы — на границах строк, "
          "с террасами и поправками, — площади сверху доходят до формы, без ставок всё по-старому, "
          "у каркаса поправок бруса нет.")


if __name__ == "__main__":
    главная()
