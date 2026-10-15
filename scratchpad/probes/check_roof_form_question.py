#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Форма кровли не указана — «Проверка» просит сверить покрытие с визуализацией.

Константин 15.10.2026, снимком разбора проверки (строка «Двускатный проект и
плоское покрытие, СТОП»: у бруса молчит, у своего проекта ложный стоп): «если
не заполнена форма кровли, смотреть по визуализации. Если расхождение формы
кровли между визуализацией и заполненных данных, писать об этом».

Читать форму с картинки проверка пока не умеет (нужен вызов ИИ), поэтому
форму без поля проекта сверяет менеджер. Держит:
  • проект каталога с двускатной формой и плоским покрытием — СТОП, как было;
    вопроса о форме нет;
  • проект каталога без формы (у бруса так у всех) и визуализация в блоке —
    вопрос «Форма кровли у проекта не указана — сверить покрытие с
    визуализацией», он ведёт к блоку картинок; без визуализации вопроса нет —
    там уже просят её добавить;
  • свой проект: форма в нём — заглушка «двускатная», поэтому плоское покрытие
    СТОП не даёт, а при визуализации стоит тот же вопрос;
  • брус с проектом без формы — тот же вопрос.

    python3 check_roof_form_question.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
# Как в живой базе: у проектов бруса формы нет, у части каркасных — тоже.
for п in ФИКСТУРА["pricing_projects"]:
    if п["product"] == "glulam" or "6×6" in п["name"]:
        п["roof_type"] = None
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
# Снимок визуализации — учебный, с сервера пробы (запрос к BM_ROOT).
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ВОПРОС = "Форма кровли у проекта не указана — сверить покрытие с визуализацией"
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


# Набор: проект (по части имени или свой), покрытие плоское или нет, визуализация есть или нет.
НАБОР = """async ({ проект, плоская, виз, свой }) => {
  canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
  if (свой) {
    const п = ['Свой проба 7×7', 3000000, 3200000, 3400000, '1', 'двус-ая', 40, 0, 0, null, null, null];
    п._tech = currentTech; п._params = { floorType: '1', source: 'manual' };
    if (!customProjects.some(х => х[0] === п[0])) customProjects.push(п);
    populateProjectSelect('');
  }
  const и = filteredProjects.findIndex(х => х[0].includes(свой ? 'Свой проба' : проект));
  selectProjectOption(и); await new Promise(r => setTimeout(r, 300));
  const кр = idВРасчёте('r17'); const п = document.getElementById('por_' + кр);
  if (п && !п.value.replace(/\\D/g, '')) { п.value = '100000'; п.dispatchEvent(new Event('input', { bubbles: true })); }
  if (!!checkedOptions[кр] !== плоская) document.getElementById('lbl_' + кр).click();
  if (виз) { canvasAddImage(виз); await Promise.all(снимкиХолста().map(видКартинки)); }
  calc();
  const пр = проверкаПоЧекЛисту();
  return { проект: selectedProject && selectedProject[0], форма: selectedProject && selectedProject[5], плоская: !!checkedOptions[кр],
    стоп: пр.замечания.some(з => з.стоп && /форма кровли/i.test(з.т)), вопрос: пр.вопросы.includes(""" + json.dumps(ВОПРОС, ensure_ascii=False) + """),
    адрес: (пр.адреса[""" + json.dumps(ВОПРОС, ensure_ascii=False) + """] || {}).эл || '' }; }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def набор(стр, н, **а):
    return стр.evaluate(НАБОР, {"проект": а.get("проект", ""), "плоская": а.get("плоская", False),
                                "виз": ВИЗ if а.get("виз") else "", "свой": а.get("свой", False)})


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
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    # Каркас: двускатный проект каталога.
    д = набор(стр, "", проект="8×8", плоская=True, виз=True)
    факт(д["стоп"] and not д["вопрос"], f"каркас, двускатный проект, плоское покрытие — СТОП, вопроса о форме нет: {д}")
    # Каркас: проект без формы.
    д = набор(стр, "", проект="6×6", виз=False)
    факт(not д["вопрос"], f"проект без формы, визуализации нет — вопроса о форме нет (просят визуализацию): {д['вопрос']}")
    д = набор(стр, "", проект="6×6", виз=True)
    факт(д["вопрос"] and д["адрес"] == "imageCanvasCard", f"проект без формы и визуализация — вопрос, ведёт к картинкам: {д}")
    # Свой проект: заглушка «двускатная» — не форма.
    д = набор(стр, "", свой=True, плоская=True, виз=False)
    факт(д["проект"] == "Свой проба 7×7" and not д["стоп"], f"свой проект с плоским покрытием — ложного СТОПа нет: {д}")
    д = набор(стр, "", свой=True, плоская=True, виз=True)
    факт(д["вопрос"], f"свой проект и визуализация — вопрос о форме: {д['вопрос']}")
    # Брус: у проектов формы нет.
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); }")
    стр.wait_for_timeout(400)
    д = набор(стр, "", проект="8×8", виз=True)
    факт(стр.evaluate("() => currentTech") == "glulam" and д["вопрос"] and not д["стоп"], f"брус, проект без формы и визуализация — вопрос: {д}")
    факт(not [о for о in ошибки if "supabase.co" not in о], f"ошибок страницы нет: {ошибки[:2]}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: без формы кровли у проекта «Проверка» просит сверить покрытие с визуализацией; свой проект ложного СТОПа не даёт.")
