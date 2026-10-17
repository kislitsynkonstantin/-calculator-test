#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Форма кровли ручного проекта — обязательное поле «Скатная» / «Плоская».

Константин 16.10.2026: «Может сделать обязательное поле, при добавлении
проекта. Чтобы указывали форму кровли, если не переходит с другого проекта»;
по макету custom-project-roof-v2: «Форма кровли поставь: Скатная и Плоская,
чтобы оставить только 2 варианта»; решение по уже заведённым проектам и
окну правки: «Давай так».

Прежде форма не спрашивалась: каждый ручной проект молча записывал
«двус-ая», и «Проверка» считала её заглушкой. Проба держит:
  • в форме добавления поле стоит под типом этажности, два сегмента;
  • двускатный проект каталога ставит «Скатная» сам и называет, откуда она;
    односкатный оставляет поле пустым — на два сегмента он не ложится;
  • без формы проект не сохраняется: поле краснеет и говорит почему, а
    всплывающего сообщения про кровлю нет (оно закрывало форму в макете);
  • выбранная форма уходит в проект и в базу (roof_type), форма после
    добавления очищается;
  • «Проверка» сверяет в обе стороны: плоский проект без плоского покрытия —
    СТОП, ведёт к наплавляемой кровле, её отметка СТОП снимает; скатный с
    плоским покрытием — СТОП; то же у бруса;
  • окно правки: у своего проекта тот же выбор, правка без формы не проходит
    (прежняя заглушка «двус-ая» формой не считается), выбранная — сохраняется;
    у проекта базы сегменты закрыты, подсказка называет форму как в базе;
  • плашка проекта, лист печати и выгрузка пишут форму словом: «одн-ая»
    прежде печаталась сокращением, заглушку «двус-ая» своего проекта лист
    выдавал за «Двускатную»;
  • «Взять из выбранного» и «Скрыть пустые» набраны Geologica, а не Arial;
  • на 390 / 768 / 1440 поле не вылезает, сегменты 44 px высотой, подсказка
    не прилипает к соседнему полю, сегменты не касаются друг друга.

    python3 check_cp_roof_form.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
КАДРЫ = pathlib.Path(os.environ.get("BM_SHOTS") or (ЗДЕСЬ / "кадры_кровля"))
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
# Как в живой базе: каталог пишет «двус-ая» и «одн-ая».
for п in ФИКСТУРА["pricing_projects"]:
    п["roof_type"] = "одн-ая" if "6×6" in п["name"] else "двус-ая"
# Наплавляемая кровля бруса — своя строка, общая с каркасной, как в базе.
ФИКСТУРА["pricing_options"].append({"product": "glulam", "option_id": "kb_r13", "name": "Материал кровельного покрытия — наплавляемая",
                                    "section": "roof", "included": False, "price": 100000, "formula": None, "status": None,
                                    "sort": 20, "shared_option": "r17"})
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


ВЫБРАТЬ = """async (часть) => { const и = filteredProjects.findIndex(х => х[0].includes(часть)); selectProjectOption(и);
  await new Promise(r => setTimeout(r, 300)); return selectedProject && selectedProject[0]; }"""
ПОЛЕ = """(пр) => { const п = document.getElementById(пр + 'RoofField'); if (!п) return null;
  const к = [...п.querySelectorAll('.roof-btn')];
  return { есть: true, кнопки: к.map(б => б.textContent.trim()), выбрано: (к.find(б => б.classList.contains('active')) || {}).textContent || '',
    закрыто: к.map(б => б.disabled), ошибка: п.classList.contains('is-err'),
    подсказка: (document.getElementById(пр + 'RoofHint') || {}).textContent || '' }; }"""
# Плоское покрытие: отметить или снять наплавляемую (с ценой, если её нет).
ПЛОСКАЯ = """async (надо) => { const кр = idВРасчёте('r17'); if (!кр) return null;
  const п = document.getElementById('por_' + кр);
  if (п && !п.value.replace(/\\D/g, '')) { п.value = '100000'; п.dispatchEvent(new Event('input', { bubbles: true })); }
  if (!!checkedOptions[кр] !== надо) document.getElementById('lbl_' + кр).click();
  await new Promise(r => setTimeout(r, 150)); calc(); return !!checkedOptions[кр]; }"""
СТОП = """() => { const пр = проверкаПоЧекЛисту(); const з = пр.замечания.find(з => з.стоп && /форма кровли/i.test(з.т));
  return з ? { т: з.т, эл: з.эл } : null; }"""
ВЕРСТКА = """(пр) => { const п = document.getElementById(пр + 'RoofField'); const р = п.getBoundingClientRect();
  const к = [...п.querySelectorAll('.roof-btn')].map(б => б.getBoundingClientRect());
  const подск = document.getElementById(пр + 'RoofHint').getBoundingClientRect();
  let сосед = п.nextElementSibling; while (сосед && !сосед.offsetParent) сосед = сосед.nextElementSibling;
  let выше = п.previousElementSibling; while (выше && !выше.offsetParent) выше = выше.previousElementSibling;
  const над = выше && выше.getBoundingClientRect();
  return { ширина: innerWidth, вылез: document.documentElement.scrollWidth - innerWidth,
    поле: [р.left, р.right], кнопки: к.map(х => [Math.round(х.left), Math.round(х.right), Math.round(х.height)]),
    зазорКнопок: к.length > 1 ? Math.round(к[1].left - к[0].right) : null,
    подсказкаНиз: подск.bottom, соседВерх: сосед ? сосед.getBoundingClientRect().top : null,
    надНиз: над ? над.bottom : null, верх: р.top }; }"""


socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])
КАДРЫ.mkdir(parents=True, exist_ok=True)


def страница(бр, ш, в):
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    return стр, ошибки


def нажать(стр, пр, вид):
    к = стр.locator(f"#{пр}RoofField .roof-btn[data-roof='{вид}']")
    if not к.count() or not к.first.is_visible():
        факт(False, f"сегмента «{вид}» в поле {пр}RoofField нет на экране")
        return
    к.first.click()
    стр.wait_for_timeout(100)


with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр, ошибки = страница(бр, 1440, 1000)

    # ── Форма добавления ──
    стр.evaluate(ВЫБРАТЬ, "8×8")
    стр.evaluate("() => toggleCustomProjectForm()")
    стр.wait_for_timeout(300)
    д = стр.evaluate(ПОЛЕ, "cp")
    факт(bool(д) and д["кнопки"] == ["Скатная", "Плоская"], f"в форме добавления поле «Форма кровли»: {д and д['кнопки']}")
    порядок = стр.evaluate("() => { const п = document.getElementById('cpRoofField'), э = document.getElementById('cpFloorTypeField');"
                           " return !!(п && э && п.previousElementSibling === э); }")
    факт(порядок, "поле стоит сразу под типом этажности")
    факт(bool(д) and д["выбрано"] == "Скатная" and "Проба дом 8×8" in д["подсказка"],
         f"двускатный проект каталога ставит «Скатная» и называет себя: {д}")
    стр.evaluate("() => toggleCustomProjectForm(true)")
    стр.evaluate(ВЫБРАТЬ, "6×6")
    стр.evaluate("() => toggleCustomProjectForm()")
    стр.wait_for_timeout(300)
    д = стр.evaluate(ПОЛЕ, "cp")
    факт(bool(д) and д["выбрано"] == "" and "Проверка" in д["подсказка"], f"односкатный проект оставляет поле пустым: {д}")
    шрифты = стр.evaluate("() => ['cpBtnCopy', 'cpToggleEmpty', 'epToggleEmpty'].map(ид => getComputedStyle(document.getElementById(ид)).fontFamily.split(',')[0].replace(/[\"']/g, ''))")
    факт(шрифты == ["Geologica"] * 3, f"«Взять из выбранного», «Скрыть пустые» (форма и окно правки) — Geologica: {шрифты}")

    # Без формы не сохраняется.
    было = стр.evaluate("() => customProjects.length")
    # Цену опции вписываем сами: у учебного 6×6 матрицы нет, и форма иначе
    # остановилась бы на ценах опций, а не на кровле.
    стр.evaluate("""() => { cpCopyFromSelected(); document.getElementById('cpName').value = 'Проба плоская 7×7';
      const о = document.querySelector('[id^=cpOpt_]'); if (о) о.value = '10 000'; confirmCustomProject(); }""")
    стр.wait_for_timeout(300)
    д = стр.evaluate(ПОЛЕ, "cp")
    тост = стр.evaluate("() => { const т = document.getElementById('toastMsg'); return т && т.classList.contains('show') ? т.textContent : ''; }")
    факт(стр.evaluate("() => customProjects.length") == было, "без формы кровли проект не добавлен")
    факт(bool(д) and д["ошибка"] and "не сохранится" in д["подсказка"], f"поле краснеет и говорит почему: {д and д['подсказка']}")
    факт("кровл" not in тост.lower(), f"всплывающего сообщения про кровлю нет: «{тост}»")
    # Подпись поля в «Бланке» задана правилом формы посильнее красного —
    # на первом снимке она осталась серой при красной линии.
    цвет = стр.evaluate("() => getComputedStyle(document.querySelector('#cpRoofField > label')).color")
    факт(цвет == "rgb(192, 57, 43)", f"подпись «Форма кровли» краснеет вместе с полем: {цвет}")
    нажать(стр, "cp", "плоская")
    д = стр.evaluate(ПОЛЕ, "cp")
    факт(bool(д) and not д["ошибка"] and д["выбрано"] == "Плоская", f"выбор снимает красное: {д}")
    стр.evaluate("() => confirmCustomProject()")
    стр.wait_for_timeout(500)
    свой = стр.evaluate("() => { const п = customProjects.find(х => х[0] === 'Проба плоская 7×7'); return п ? п[5] : null; }")
    факт(свой == "плоская", f"форма ушла в проект: {свой}")
    в_базе = стр.evaluate("() => ((window.__ТАБЛИЦЫ.custom_projects || []).find(р => р.name === 'Проба плоская 7×7') || {}).roof_type || null")
    факт(в_базе == "плоская", f"и в базу, roof_type: {в_базе}")
    д = стр.evaluate(ПОЛЕ, "cp")
    факт(bool(д) and д["выбрано"] == "", f"после добавления поле формы очищено: {д and д['выбрано']}")

    # ── «Проверка» по своему плоскому проекту ──
    стр.evaluate(ВЫБРАТЬ, "Проба плоская 7×7")
    стр.evaluate(ПЛОСКАЯ, False)
    з = стр.evaluate(СТОП)
    факт(bool(з) and "плоский" in з["т"] and з["эл"] == "lbl_r17", f"плоский проект, покрытие скатное — СТОП к наплавляемой: {з}")
    стр.evaluate(ПЛОСКАЯ, True)
    з = стр.evaluate(СТОП)
    факт(з is None, f"отмеченная наплавляемая СТОП снимает: {з}")
    плашка = стр.evaluate("() => document.getElementById('projectInfo').textContent")
    факт("Плоская" in плашка, "плашка проекта: «Кровля Плоская»")
    факт(стр.evaluate("() => названиеКровли(selectedProject)") == "Плоская", "лист печати: «Плоская»")

    # ── Окно правки своего проекта ──
    стр.evaluate("() => openEditProject()")
    стр.wait_for_timeout(300)
    д = стр.evaluate(ПОЛЕ, "ep")
    факт(bool(д) and д["выбрано"] == "Плоская" and д["закрыто"] == [False, False], f"окно правки: своя форма, выбор открыт: {д}")
    факт(not стр.evaluate("() => !!document.getElementById('epRoof')"), "текстового поля «Кровля» в окне правки больше нет")
    нажать(стр, "ep", "скатная")
    стр.evaluate("() => confirmEditProject()")
    стр.wait_for_timeout(400)
    факт(стр.evaluate("() => selectedProject[5]") == "скатная", "правка формы сохранилась: «скатная»")
    з = стр.evaluate(СТОП)
    факт(bool(з) and "скатный, покрытие плоское" in з["т"], f"скатный проект с плоским покрытием — СТОП: {з}")
    стр.evaluate(ПЛОСКАЯ, False)

    # Прежняя заглушка «двус-ая» — не форма.
    стр.evaluate("""() => { const п = ['Проба старая 5×5', 2000000, 2100000, 2200000, 1, 'двус-ая', 25, 0, 0, null, null, null];
      п._tech = currentTech; п._params = { floorType: '1', source: 'manual' }; customProjects.push(п); populateProjectSelect(''); }""")
    стр.evaluate(ВЫБРАТЬ, "Проба старая 5×5")
    факт(стр.evaluate("() => названиеКровли(selectedProject)") == "", "заглушка «двус-ая» своего проекта на лист не идёт")
    стр.evaluate("() => openEditProject()")
    стр.wait_for_timeout(300)
    д = стр.evaluate(ПОЛЕ, "ep")
    факт(bool(д) and д["выбрано"] == "", f"окно правки: у старого своего проекта форма пуста: {д and д['выбрано']}")
    стр.evaluate("() => { document.getElementById('epWarm').value = '26'; confirmEditProject(); }")
    стр.wait_for_timeout(300)
    д = стр.evaluate(ПОЛЕ, "ep")
    факт(стр.evaluate("() => [selectedProject[5], selectedProject[6]]") == ["двус-ая", 25] and д and д["ошибка"],
         f"правка без формы не проходит и поле краснеет: {стр.evaluate('() => [selectedProject[5], selectedProject[6]]')}")
    стр.evaluate("() => closeEditProject()")

    # Проект базы — только посмотреть.
    for часть, выбор, база in (("8×8", "Скатная", "двускатная"), ("6×6", "", "односкатная")):
        стр.evaluate(ВЫБРАТЬ, часть)
        стр.evaluate("() => openEditProject()")
        стр.wait_for_timeout(300)
        д = стр.evaluate(ПОЛЕ, "ep")
        факт(bool(д) and д["закрыто"] == [True, True] and д["выбрано"] == выбор and база in д["подсказка"],
             f"окно правки проекта базы {часть}: сегменты закрыты, «{выбор}», подсказка про {база}: {д}")
        стр.evaluate("() => closeEditProject()")
    факт(стр.evaluate("() => названиеКровли(selectedProject)") == "Односкатная", "лист печати: «одн-ая» словом — «Односкатная»")
    стр.evaluate(ВЫБРАТЬ, "8×8")
    стр.evaluate(ПЛОСКАЯ, True)
    з = стр.evaluate(СТОП)
    факт(bool(з) and "двускатный, покрытие плоское" in з["т"], f"двускатный проект каталога с плоским — СТОП, как было: {з}")
    стр.evaluate(ПЛОСКАЯ, False)

    # ── Брус ──
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); }")
    стр.wait_for_timeout(400)
    стр.evaluate("""() => { const п = ['Брус плоский 6×6', 3000000, 3200000, 3400000, 1, 'плоская', 36, 0, 0, null, null, null];
      п._tech = 'glulam'; п._params = { floorType: '1', source: 'manual' }; customProjects.push(п); populateProjectSelect(''); }""")
    стр.evaluate(ВЫБРАТЬ, "Брус плоский 6×6")
    отм = стр.evaluate(ПЛОСКАЯ, False)
    з = стр.evaluate(СТОП)
    факт(отм is not None and bool(з) and "плоский" in з["т"], f"брус: плоский проект без плоского покрытия — СТОП: {з}")
    стр.evaluate(ПЛОСКАЯ, True)
    факт(стр.evaluate(СТОП) is None, "брус: наплавляемая СТОП снимает")
    факт(not [о for о in ошибки if "supabase.co" not in о], f"ошибок страницы нет: {ошибки[:2]}")
    стр.close()

    # ── Вёрстка ──
    for ш, в in ((390, 844), (768, 1024), (1440, 1000)):
        стр, ошибки = страница(бр, ш, в)
        стр.evaluate(ВЫБРАТЬ, "8×8")
        стр.evaluate("() => toggleCustomProjectForm()")
        стр.wait_for_timeout(400)
        for пр in ("cp", "ep"):
            if пр == "ep":
                стр.evaluate("() => { toggleCustomProjectForm(true); openEditProject(); }")
                стр.wait_for_timeout(400)
            стр.evaluate("(ид) => document.getElementById(ид).scrollIntoView({ block: 'center' })", пр + "RoofField")
            стр.wait_for_timeout(150)
            р = стр.evaluate(ВЕРСТКА, пр)
            имя = {"cp": "форма добавления", "ep": "окно правки"}[пр]
            факт(р["вылез"] <= 0, f"{ш}, {имя}: страница не шире экрана (+{р['вылез']} px)")
            факт(all(р["поле"][0] - 1 <= к[0] and к[1] <= р["поле"][1] + 1 for к in р["кнопки"]), f"{ш}, {имя}: сегменты внутри поля: {р['кнопки']} в {р['поле']}")
            факт(all(к[2] >= 44 for к in р["кнопки"]), f"{ш}, {имя}: сегменты 44 px высотой: {[к[2] for к in р['кнопки']]}")
            факт(р["соседВерх"] is not None and р["соседВерх"] - р["подсказкаНиз"] >= 6,
                 f"{ш}, {имя}: подсказка не прилипает к следующему полю: {р['соседВерх'] is not None and round(р['соседВерх'] - р['подсказкаНиз'])} px")
            факт(р["надНиз"] is not None and р["верх"] - р["надНиз"] >= 6, f"{ш}, {имя}: поле отстоит от предыдущего: {р['надНиз'] is not None and round(р['верх'] - р['надНиз'])} px")
            стр.screenshot(path=str(КАДРЫ / f"{пр}-{ш}.png"))
        факт(not [о for о in ошибки if "supabase.co" not in о], f"{ш}: ошибок страницы нет: {ошибки[:2]}")
        стр.close()
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: форма кровли ручного проекта обязательна, «Проверка» сверяет её с покрытием в обе стороны.")
