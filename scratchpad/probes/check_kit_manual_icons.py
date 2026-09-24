#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Правка и удаление ручной опции в редакторе комплектаций — значки без рамки.

Константин 24.09.2026, снимком редактора в «Бланке»: «возле кнопки
„редактирования“ ручных опций убери обрамление. Когда опция в 2 строки —
получается некрасивое обрамление». Рамку давало правило для кнопки «+ Ручная»:
его выборка `button[onclick*="openKedCustomForm"]` ловила и значок правки в
каждой строке — обработчик тот же, только с номером опции.

Проба меряет отрисовку, а не разметку, в обеих темах, днём и ночью, на 390 и
1440 px, на ручной опции в одну строку и в две (на телефоне):

  • у значков правки и удаления в строке нет видимой рамки и заливки;
  • нарисованы они не выше 20 px — строка в две строки их не вытягивает;
  • палец ловит значок в 12 px над и под его серединой и у краёв — площадь
    нажатия держит невидимое поле, а не нарисованная коробка; больше дать
    нельзя: строки идут с шагом 30 px, и поле залезло бы на соседнюю;
  • обратная сторона: «+ Ручная» в «Бланке» рамку сохраняет — сужение
    выборки не должно снять её с той кнопки, ради которой правило писалось.

    python3 check_kit_manual_icons.py
"""
import importlib.util
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
спец = importlib.util.spec_from_file_location("кк", ЗДЕСЬ / "check_kits_copy.py")
КК = importlib.util.module_from_spec(спец)
спец.loader.exec_module(КК)

НАХОДКИ = []
ДЛИННОЕ = "Обшивка стен — вагонка штиль 20×135 мм (сорт АВ) в парной и моечной, с пропиткой"

ЗНАЧКИ = """() => {
  const сп = document.getElementById('kedOptsList');
  const кн = [...сп.querySelectorAll('button[onclick*="openKedCustomForm(\\'"], button[onclick*="deleteKedCustom(\\'"]')];
  const видна = (с, сторона) => parseFloat(с['border' + сторона + 'Width']) > 0 && с['border' + сторона + 'Style'] !== 'none'
      && с['border' + сторона + 'Color'] !== 'rgba(0, 0, 0, 0)';
  return кн.map(к => {
    const с = getComputedStyle(к), б = к.getBoundingClientRect();
    const строка = к.parentElement.getBoundingClientRect();
    const x = б.left + б.width / 2, y = б.top + б.height / 2;
    const ловит = [[x, y - 12], [x, y + 12], [б.left + 1, y], [б.right - 1, y]].map(([тx, тy]) => {
      const э = document.elementFromPoint(тx, тy);
      return !!(э && (э === к || к.contains(э)));
    });
    return { что: к.getAttribute('onclick').includes('delete') ? 'удаление' : 'правка',
             рамка: ['Top', 'Right', 'Bottom', 'Left'].some(ст => видна(с, ст)),
             заливка: с.backgroundColor !== 'rgba(0, 0, 0, 0)' && с.backgroundColor !== 'transparent',
             в: Math.round(б.height), ш: Math.round(б.width),
             строкаВ: Math.round(строка.height), ловит };
  });
}"""



def проверить(стр, где, бланк):
    # Редактор при открытии дочитывает комплектации из базы и перезаписывает
    # ручные опции — добавленные сразу пропали бы до замера.
    стр.evaluate("() => { openKompl(); switchKomplTab('editor'); switchKedTab('standart'); }")
    стр.wait_for_timeout(800)
    стр.evaluate("""([длинное]) => {
      // Раздел берём у первой строки редактора: ручная опция выводится в конце
      // своего раздела, и выдуманный раздел в список не попал бы.
      const раздел = (KOMPL_ROWS.find(r => r.type === 'extra') || {}).sec;
      KOMPL_CUSTOM.push({ id: 'cu_короткая', name: 'Терраса', price: 45000, section: раздел, kitChecked: {} });
      KOMPL_CUSTOM.push({ id: 'cu_длинная', name: длинное, price: 1, section: раздел, kitChecked: {} });
      renderKedList();
    }""", [ДЛИННОЕ])
    стр.wait_for_timeout(400)
    стр.evaluate("""() => { const к = document.querySelector('#kedOptsList button[onclick*="cu_длинная"]');
                            if (к) к.scrollIntoView({ block: 'center' }); }""")
    стр.wait_for_timeout(200)
    значки = стр.evaluate(ЗНАЧКИ)
    if len(значки) < 4:
        НАХОДКИ.append(f"[{где}] значков правки и удаления у ручных опций {len(значки)}, ждали 4")
        return
    if "390" in где and max(з["строкаВ"] for з in значки) < 40:
        НАХОДКИ.append(f"[{где}] длинная ручная опция не ушла в две строки — случай со снимка не проверен")
    for з in значки:
        if з["рамка"] or з["заливка"]:
            НАХОДКИ.append(f"[{где}] у значка «{з['что']}» видна рамка или заливка")
        if з["в"] > 20:
            НАХОДКИ.append(f"[{где}] значок «{з['что']}» нарисован {з['в']} px высотой — вытянут строкой")
        мимо = [с_ for с_, п in zip(("сверху", "снизу", "слева", "справа"), з["ловит"]) if not п]
        if мимо:
            НАХОДКИ.append(f"[{где}] значок «{з['что']}»: нажатие мимо ({', '.join(мимо)})")
    if бланк:
        рамка = стр.evaluate("""() => { const к = document.querySelector('#kedOptsPanel button[onclick="openKedCustomForm()"]');
                                      return к ? getComputedStyle(к).borderTopStyle !== 'none' && parseFloat(getComputedStyle(к).borderTopWidth) > 0 : null; }""")
        if not рамка:
            НАХОДКИ.append(f"[{где}] «+ Ручная» потеряла рамку — выборка сужена не туда")
    print(f"  {где}: значки {[з['в'] for з in значки]} px, строки {sorted({з['строкаВ'] for з in значки})} px")


def главная():
    с, порт = КК.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=КК.ХРОМ, args=["--no-sandbox"])
            for бланк in (False, True):
                for ночь in (False, True):
                    for ш, в in ((390, 844), (1440, 900)):
                        где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"
                        стр = бр.new_page(viewport={"width": ш, "height": в})
                        ошибки = []
                        стр.on("pageerror", lambda e, о=ошибки: о.append(str(e)))
                        стр.add_init_script(КК.ЗАГЛУШКА)
                        стр.add_init_script(
                            "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                            "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(КК.ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                            "window.addEventListener('DOMContentLoaded', function () {\n"
                            "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n});")
                        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                        стр.wait_for_timeout(2500)
                        try:
                            готово = стр.evaluate(КК.ПОДГОТОВКА)
                            if готово.get("беда"):
                                НАХОДКИ.append(f"[{где}] подготовка: {готово['беда']}")
                            else:
                                стр.evaluate("""([б, н]) => { const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                                  applyUiStyle(б ? 'blank' : 'light', false); applyThemeMode(н ? 'dark' : 'light', false); }""", [бланк, ночь])
                                проверить(стр, где, бланк)
                        except Exception as e:
                            НАХОДКИ.append(f"[{где}] проба оборвалась: {e!s:.200}")
                        важные = [о for о in ошибки if "supabase.co" not in о and "цены" not in о]
                        if важные:
                            НАХОДКИ.append(f"[{где}] ошибки страницы: " + "; ".join(важные)[:200])
                        стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: значки правки и удаления ручных опций без рамки и не вытягиваются строкой "
          "в две строки, палец их ловит, а «+ Ручная» в «Бланке» рамку сохранила.")


if __name__ == "__main__":
    главная()
