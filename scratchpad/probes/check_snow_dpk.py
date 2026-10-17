#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Проверка»: снегозадержатели на скатной кровле (4-6), крючки на Шинглас (4-2)
и марка ДПК (5-8) — у каркаса и клеёного бруса.

Константин 17.10.2026, снимком трёх строк разбора проверок: «Эти сделай».
Правила каркаса по одному держит check_checklist_rules.py; эта проба — то,
чего там нет: брус с его общими с каркасом строками, форма кровли проекта и
переименование строки снегозадержателей при Шингласе. Держит, в обеих
технологиях:
  • двускатный и односкатный проект при неплоском покрытии без
    снегозадержателей — «Добавить снегозадержатели», ведёт к их строке;
    плоский проект, плоское покрытие или формы нет — молчит;
  • нынешний Шинглас переименовывает снегозадержатели в «(крючки)» — пункта
    4-2 нет; старая строка Шингласа или трубчатые — «На Шинглас
    снегозадержатели — крючки, заменить трубчатые», ведёт к строке трубчатых;
  • строка ДПК бруса — с маркой из общей строки каркаса, пункта нет; своя
    позиция из ДПК без марки — «Указать марку ДПК», ведёт к ней.
Названия опций и цены в пробе выдуманы, кроме имён из файла калькулятора.

    python3 check_snow_dpk.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))


def опция(продукт, ид, раздел, имя, статус=None, общая=None):
    ФИКСТУРА["pricing_options"].append({"product": продукт, "option_id": ид, "name": имя, "section": раздел, "included": False,
                                        "price": 1000, "formula": None, "status": статус, "sort": 900, "shared_option": общая})


for ид, раздел, имя, статус in [("ex11", "exterior", "Учебная ДПК", "formula"), ("r8", "roof", "Учебные снегозадержатели", None),
                                ("r10", "roof", "Учебные трубчатые", "legacy"), ("r11", "roof", "Учебная скоба", "legacy"),
                                ("r16", "roof", "Учебный Шинглас", "formula"), ("r17", "roof", "Учебная наплавляемая", "formula")]:
    опция("frame", ид, раздел, имя, статус)
for ид, раздел, имя, общая in [("kb_ex8", "exterior", "Террасная доска - ДПК (указать марку)", "ex11"), ("kb_r4", "roof", "Снегозадержатели", None),
                               ("kb_r6", "roof", "Снегозадержатели трубчатые", "r10"), ("kb_r12", "roof", "шинглас", "r16"),
                               ("kb_r13", "roof", "наплавляемая", "r17"), ("kb_r1", "roof", "Учебный Шинглас своей строкой бруса", None)]:
    опция("glulam", ид, раздел, имя, None, общая)
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


# Каждый случай — с чистого листа: отметки снегозадержателей, кровли и ДПК
# сняты, своих позиций и примечаний в кровле и фасаде нет, форма проекта — та,
# что задана (у проекта пробы она в шестом поле).
СЛУЧАЙ = """async ([форма, отметить, своя]) => {
  ['r8','r10','r11','r16','r5','r17','r15','ex11','kb_r4','kb_r6','kb_r12','kb_r13','kb_r1','kb_ex8'].forEach(и => { if (getOpt(и)) checkedOptions[и] = false; });
  ['roof', 'exterior', 'extra'].forEach(р => { customOptions[р] = []; customNotes[р] = []; });
  if (!window.__форма) window.__форма = selectedProject[5];
  selectedProject[5] = форма === null ? window.__форма : форма;
  (отметить || []).forEach(и => { checkedOptions[и] = true; });
  if (своя) customOptions[своя[0]].push({ id: 'св1', name: своя[1], price: 0, checked: true });
  calc(); await new Promise(r => setTimeout(r, 150));
  const п = проверкаПоЧекЛисту();
  const з = т => (п.замечания.find(х => х.т.indexOf(т) !== -1) || null);
  const к = (т) => { const х = з(т); return х ? { т: х.т, эл: х.эл, р: х.раздел } : null; };
  return { снег: к('Добавить снегозадержатели'), крючки: к('крючки, заменить трубчатые'), дпк: к('Указать марку ДПК'),
    стоп: п.замечания.some(х => х.стоп && /Форма кровли/.test(х.т)),
    имя: (getOpt(currentTech === 'glulam' ? 'kb_r4' : 'r8') || {}).name || '', имяДпк: (getOpt(currentTech === 'glulam' ? 'kb_ex8' : 'ex11') || {}).name || '' }; }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def прогон(стр, т, снег, шинглас, трубчатые, старыйШинглас, плоское, дпк):
    def сл(форма, отметить=(), своя=None):
        return стр.evaluate(СЛУЧАЙ, [форма, list(отметить), своя])
    д = сл("двускатная")
    факт(bool(д["снег"]) and д["снег"]["эл"] == "lbl_" + снег and д["снег"]["р"] == "roof",
         f"{т}: двускатный без снегозадержателей — «Добавить снегозадержатели», ведёт к их строке: {д['снег']}")
    д = сл("односкатная")
    факт(bool(д["снег"]), f"{т}: односкатный без снегозадержателей — тоже пункт: {д['снег']}")
    факт(not сл("двускатная", [снег])["снег"], f"{т}: снегозадержатели стоят — молчит")
    факт(not сл("двускатная", (), ["roof", "Снегозадержатели заказчика"])["снег"], f"{т}: своя позиция снегозадержателей — молчит")
    д = сл("двускатная", [плоское])
    факт(not д["снег"] and д["стоп"], f"{т}: плоское покрытие — про снегозадержатели молчит, стоит стоп формы кровли: {д}")
    факт(not сл("плоская")["снег"], f"{т}: плоский проект — молчит")
    факт(not сл("")["снег"], f"{т}: формы у проекта нет — молчит")
    д = сл(None, [шинглас, снег])
    факт("крючки" in д["имя"] and not д["крючки"], f"{т}: нынешний Шинглас — строка «{д['имя']}», пункта 4-2 нет: {д['крючки']}")
    д = сл(None, [шинглас, трубчатые])
    факт(bool(д["крючки"]) and д["крючки"]["т"] == "На Шинглас снегозадержатели — крючки, заменить трубчатые" and д["крючки"]["эл"] == "lbl_" + трубчатые,
         f"{т}: Шинглас и старые трубчатые — пункт 4-2 к их строке: {д['крючки']}")
    д = сл(None, [старыйШинглас, снег])
    факт("трубчат" in д["имя"] and bool(д["крючки"]) and д["крючки"]["эл"] == "lbl_" + снег,
         f"{т}: старая строка Шингласа — снегозадержатели остались «{д['имя']}», пункт 4-2 к ним: {д['крючки']}")
    д = сл(None, [дпк])
    факт("указать марку" not in д["имяДпк"].lower() and "UnoDeck" in д["имяДпк"] and not д["дпк"],
         f"{т}: строка ДПК «{д['имяДпк']}» — с маркой, пункта 5-8 нет: {д['дпк']}")
    д = сл(None, (), ["extra", "Ступени из ДПК"])
    факт(bool(д["дпк"]) and д["дпк"]["эл"] == "lbl_custom_св1" and д["дпк"]["р"] == "extra", f"{т}: своя позиция из ДПК без марки — пункт к ней: {д['дпк']}")
    факт(not сл(None, (), ["extra", "Ступени из ДПК Savewood"])["дпк"], f"{т}: своя позиция из ДПК с маркой — молчит")
    сл(None)


with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 1000})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; selectProjectOption(0); calc(); }")
    стр.wait_for_timeout(600)
    прогон(стр, "каркас", снег="r8", шинглас="r16", трубчатые="r10", старыйШинглас="r5", плоское="r17", дпк="ex11")
    стр.evaluate("async () => { window.__форма = undefined; await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }")
    стр.wait_for_timeout(700)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    прогон(стр, "брус", снег="kb_r4", шинглас="kb_r12", трубчатые="kb_r6", старыйШинглас="kb_r1", плоское="kb_r13", дпк="kb_ex8")
    факт(not ошибки, f"ошибок страницы нет: {ошибки[:2]}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: снегозадержатели на скатной кровле, крючки на Шинглас и марка ДПК — у каркаса и бруса.")
