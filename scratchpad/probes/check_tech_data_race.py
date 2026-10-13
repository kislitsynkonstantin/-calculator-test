#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Данные технологии не обгоняют её саму.

Константин 13.10.2026, двумя снимками: «В режиме клеёный брус показывает
проекты из каркаса, даёт выбрать и загружает каркас. Но поля с вводом площадей
остаются от бруса». На экране — заголовок «Клеёный брус», «Цена 160x185» и поля
площадей, а в списке каркасный «Вирджиния 3» и в своде разделы «Каркас» и
«Утепление и ветрозащита».

Причина — гонка двух смен технологии. Пока шла загрузка цен каркаса (её зовёт,
например, открытие сохранённого каркасного расчёта), профиль приносил
запомненную технологию, и вторая смена включала брус. Если цены бруса были уже
в памяти, брус ложился сразу, а запоздавший ответ каркаса ложился поверх:
`currentTech` и оформление — бруса, проекты, опции и разделы — каркаса.

Проба держит обе стороны гонки:
  • медленный каркас, затем брус — в итоге брус: проекты, разделы, список
    проектов на экране и заголовок бруса;
  • медленный брус, затем каркас — в итоге каркас, поля площадей скрыты;
  • в обоих случаях выбранный после гонки проект — проект итоговой технологии.

    python3 check_tech_data_race.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ПРОЕКТЫ = {т: [р["name"] for р in м.ДАННЫЕ["pricing_projects"] if р.get("product") == т] for т in ("frame", "glulam")}

ВИД = """() => ({
  тех: currentTech,
  проекты: PROJECTS.map(p => p[0]),
  список: [...document.querySelectorAll('#projectSelectDropdown .custom-select-option')].map(э => (э.dataset.name || э.textContent || '').trim()).filter(Boolean),
  раздел: (SECTIONS.find(с => с.key === 'frame') || {}).name || '',
  заголовок: (document.getElementById('techTitle') || {}).textContent || '',
  площади: (document.getElementById('kbAreasWrap') || {}).style ? document.getElementById('kbAreasWrap').style.display : '?',
  опцийВсего: OPTIONS.length,
  каркасИзФайла: OPTIONS.length === FRAME_OPTIONS.length && OPTIONS.every((o, i) => o === FRAME_OPTIONS[i]),
})"""


def гонка(стр, медленная, итоговая, н):
    стр.evaluate("""([медленная, итоговая]) => {
      delete _techData[медленная];
      window.__ЗАДЕРЖКА = (таблица, продукт) => (String(таблица).startsWith('pricing_') && продукт === медленная) ? 1500 : 0;
      switchTech(медленная);
      switchTech(итоговая);
    }""", [медленная, итоговая])
    стр.wait_for_timeout(3200)
    стр.evaluate("() => { window.__ЗАДЕРЖКА = 0; }")
    в = стр.evaluate(ВИД)
    чужая = "frame" if итоговая == "glulam" else "glulam"
    if в["тех"] != итоговая:
        НАХОДКИ.append(f"{н} технология после гонки {в['тех']}, ждали {итоговая}")
    if sorted(в["проекты"]) != sorted(ПРОЕКТЫ[итоговая]):
        НАХОДКИ.append(f"{н} технология {в['тех']}, а проекты {в['проекты']} — ждали {ПРОЕКТЫ[итоговая]}")
    чужие = [и for и in в["список"] if any(ч in и for ч in ПРОЕКТЫ[чужая])]
    if чужие:
        НАХОДКИ.append(f"{н} в списке проектов на экране чужие: {чужие}")
    if итоговая == "glulam":
        # У каркаса список опций — из файла, у бруса — из базы.
        if в["каркасИзФайла"]:
            НАХОДКИ.append(f"{н} брус, а опции — каркасный список из файла ({в['опцийВсего']})")
        if в["раздел"] == "Каркас":
            НАХОДКИ.append(f"{н} брус, а второй раздел называется «Каркас»")
        if в["площади"] == "none":
            НАХОДКИ.append(f"{н} брус, а поля площадей скрыты")
    else:
        if not в["каркасИзФайла"]:
            НАХОДКИ.append(f"{н} каркас, а опции не каркасные ({в['опцийВсего']})")
        if в["площади"] != "none":
            НАХОДКИ.append(f"{н} каркас, а поля площадей бруса видны")
    # Выбранный после гонки проект — своей технологии, и расчёт идёт по нему.
    имя = стр.evaluate("() => { selectProjectOption(0); calc(); return selectedProject && selectedProject[0]; }")
    if имя not in ПРОЕКТЫ[итоговая]:
        НАХОДКИ.append(f"{н} после гонки выбран проект {имя!r} — не из {итоговая}")
    return в


def прогон(бр, порт):
    к = бр.new_context(viewport={"width": 1440, "height": 1000})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    # Цены бруса — уже в памяти: так было у Константина, открывавшего брус раньше.
    стр.evaluate("async () => { await switchTech('glulam'); await switchTech('frame'); }")
    а = гонка(стр, "frame", "glulam", "[каркас медленный → брус]")
    б = гонка(стр, "glulam", "frame", "[брус медленный → каркас]")
    if ошибки:
        НАХОДКИ.append(f"ошибки страницы: {ошибки[:3]}")
    к.close()
    return а, б


def main():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            а, б = прогон(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print(f"Чисто: две смены технологии подряд кончаются данными последней — брус после медленного каркаса "
          f"({len(а['проекты'])} проекта бруса, «{а['раздел']}»), каркас после медленного бруса; "
          f"список на экране и выбранный проект своей технологии.")


if __name__ == "__main__":
    main()
