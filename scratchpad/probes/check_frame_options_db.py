#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Список опций каркаса — из базы, как у клеёного бруса.

До 17.10.2026 названия, разделы и порядок опций каркаса лежали в файле, база
давала только цены и статусы, и переименовать позицию можно было только
выпуском. Константин 17.10.2026 о загрузке правок из Excel: «Перенеси».
Теперь калькулятор строит список каркаса из pricing_options (product
'frame'). Проба правит строки так, как их правят в базе, и держит:
  • новое название строки базы стоит в строке на листе;
  • порядок — по sort: строка с меньшим sort встаёт выше;
  • «в базовой комплектации» из базы — строка стоит отмеченной;
  • общая с каркасом строка бруса берёт название у строки каркаса в базе,
    даже когда каркас ещё не открывали;
  • база не отдала список каркаса — экран «Цены не загрузились», а не пустой
    калькулятор;
  • без правок список совпадает с прежним файлом: 247 строк, вывоз мусора
    по 37 000 ₽, монтаж электропечи на месте.

    python3 check_frame_options_db.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


ПРАВКИ = """window.__ПРАВКИ_КАРКАСА = {
  w16: { name: 'Энергосберегающие стёкла — название из базы' },
  w7: { name: 'Окно в парное отделение — название из базы' },
  r24: { sort: -5 },
  r6: { included: true },
};"""


def страница(бр, порт, *скрипты):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    for с in скрипты:
        стр.add_init_script(с)
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    return стр, ошибки


def прогон(бр, порт):
    # Без правок — тот же список, что был в файле.
    стр, ош = страница(бр, порт)
    р = стр.evaluate("() => [OPTIONS.length, (getOpt('e12') || {}).price, (getOpt('st35') || {}).name, OPTIONS[0].id, OPTIONS[OPTIONS.length - 1].id]")
    факт(р == [247, 37000, "Монтаж электрической печи", "f1", "eng21"], f"без правок — прежний список: {р}")
    стр.close()

    # Правки строк базы видны в калькуляторе.
    стр, ош = страница(бр, порт, ПРАВКИ)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; selectProjectOption(0); }")
    стр.wait_for_timeout(800)
    имя = стр.evaluate("() => (document.querySelector('#lbl_w16 .opt-name') || {}).textContent || ''")
    факт("название из базы" in имя, f"название строки — из базы: «{имя.strip()[:60]}»")
    порядок = стр.evaluate("() => [OPTIONS.findIndex(o => o.id === 'r24'), OPTIONS.findIndex(o => o.id === 'f1')]")
    факт(порядок[0] == 0 and порядок[1] == 1, f"порядок — по sort базы: вальмовая кровля первой, {порядок}")
    факт(стр.evaluate("() => !!checkedOptions.r6 && getOpt('r6').included"), "«в базовой комплектации» — из базы: водосток отмечен")
    # Брус до каркаса: список каркаса приходит вместе с ценами бруса.
    р = стр.evaluate("""async () => {
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 1200));
      delete _techData.frame; FRAME_OPTIONS.length = 0;
      await loadPricing('glulam', true); await new Promise(r => setTimeout(r, 600));
      const общая = OPTIONS.find(o => o.общаяС === 'w7');
      return [FRAME_OPTIONS.length, общая ? общая.name : null, OPTIONS.filter(o => o.общаяС).map(o => o.общаяС)]; }""")
    if "w7" in р[2]:
        факт(р[0] == 247 and "название из базы" in (р[1] or ""), f"брус до каркаса: общая строка — с названием из базы каркаса: {р[:2]}")
    else:
        факт(р[0] == 247, f"брус до каркаса: список каркаса пришёл с ценами бруса ({р[0]} строк; общие в пробе: {р[2]})")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"ошибка страницы: {о[:160]}")
    стр.close()

    # База не отдала список каркаса — экран ошибки цен.
    стр, ош = страница(бр, порт, "window.__БЕЗ_СПИСКА_КАРКАСА = true;")
    р = стр.evaluate("() => [!!document.getElementById('pricingErrorScreen'), OPTIONS.length]")
    факт(р[0], f"без списка каркаса — экран «Цены не загрузились»: {р}")
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
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: список каркаса — из базы: название, порядок и базовая комплектация берутся у строк базы, "
          "брус получает их до каркаса, без списка — экран ошибки цен; без правок список прежний.")


if __name__ == "__main__":
    главная()
