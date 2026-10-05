#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Количество поштучных опций и площадь — и в комплектациях.

Константин 05.10.2026, снимками редактора комплектаций и карточки дверей:
«в комплектациях сделай тоже возможность выбора количества, там где это
предусмотрено (также это есть в Flow Vilpe для кровли). Все опции проверь,
где ручной выбор есть количества или площади».

Проба на 390 и 1440 нажимает и смотрит на суммы:
  • в редакторе у отмеченной поштучной опции — счётчик; у неотмеченной — нет;
    у террасы (площадь) — поле, куда площадь вписывается;
  • двери ×3 — строка редактора и цена комплектации растут ровно на две
    двери; терраса 20 м² — 144 000 × 20 / 12; колпаки Flow Vilpe ×3 — втрое;
  • цена комплектации не зависит от количества, открытого в спецификации;
  • в таблице комплектаций рядом с галочкой — «3 двери»;
  • количество уходит в базу (`project_kits.option_qty`) и возвращается
    загрузкой; снятая из комплектации опция теряет и количество;
  • применённая комплектация ставит количество в спецификацию («за 3
    двери»), итог расчёта равен цене комплектации; поменяли количество в
    спецификации — расчёт уже не совпадает с комплектацией;
  • строка со счётчиком не вылезает за список.

    python3 check_kit_qty.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_doors_qty as д  # noqa: E402  (сервер, Chromium, заглушка базы)
from playwright.sync_api import sync_playwright  # noqa: E402

НАХОДКИ = []
ДВЕРЬ, ТЕРРАСА = 24000, 144000
# Строки опций — как в базе на 05.10.2026.
СТРОКИ = [
    {"product": "frame", "option_id": "w15", "section": "windows", "included": False, "price": ДВЕРЬ, "formula": None, "status": None, "sort": 90,
     "name": "Межкомнатные двери — МДФ (доборы, наличники, ручки), за 1 дверь"},
    {"product": "frame", "option_id": "e10", "section": "extra", "included": False, "price": ТЕРРАСА, "formula": None, "status": None, "sort": 220,
     "name": "Устройство открытой террасы 12 м²"},
    {"product": "frame", "option_id": "r23", "section": "roof", "included": False, "price": None, "status": "formula", "sort": 113,
     "name": "Кровельный вентиляционный выход с колпаком Flow Vilpe (1 шт.)",
     "formula": {"coef": 17000, "mult": 1.1, "areaSrc": "qty", "comment": "Количество колпаков.", "qtyOption": True, "defaultQty": 1, "defaultMargin": 0.3}},
]
ОПЦИИ = [o for o in д.ДАННЫЕ["pricing_options"] if o["option_id"] not in {с["option_id"] for с in СТРОКИ}] + СТРОКИ
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(д.ДАННЫЕ, pricing_options=ОПЦИИ), ensure_ascii=False) + ");")

ШАГИ = """async () => {
  const пауза = (мс = 250) => new Promise(r => setTimeout(r, мс));
  const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  selectProjectOption(0); await пауза(800);
  await loadKitsForCurrentProject(); await пауза(200);
  openKompl(); await пауза(300); openKomplEditor(); await пауза(300);
  komplKedTab = 'standart'; renderKedList();
  const р = {};
  р.видно = document.getElementById('kedOptsList').getBoundingClientRect().width > 0;
  const имя = ид => KOMPL_ID_TO_NAME[ид];
  const вНабор = ид => { if (!KOMPL_CONFIGS.standart.has(имя(ид))) kedToggle(имя(ид)); };
  р.счётчикДо = !!document.getElementById('kedqty_w15');
  // Количество в спецификации — пять дверей: цена комплектации от него не зависит.
  formulaOverrides.w15 = { area: 5 };
  вНабор('w15'); await пауза();
  р.счётчикПосле = !!document.getElementById('kedqty_w15');
  const ц1 = calcKomplPrice('standart');
  kedИзменитьКоличество('w15', 1); kedИзменитьКоличество('w15', 1); await пауза();
  const ц3 = calcKomplPrice('standart');
  р.приростДверей = ц3 - ц1;
  р.значение = (document.getElementById('kedqty_w15') || {}).textContent;
  const строка = document.getElementById('kedqty_w15') && document.getElementById('kedqty_w15').closest('div[onclick]');
  р.ценаСтроки = строка ? Number((строка.querySelector('.ked-price') || {}).textContent.replace(/\\D/g, '')) : null;
  // Терраса — площадь полем.
  вНабор('e10'); await пауза();
  р.полеТеррасы = (document.getElementById('kedqty_e10') || {}).tagName;
  const цт1 = calcKomplPrice('standart');
  kedЗадатьКоличество('e10', '20'); await пауза();
  р.приростТеррасы = calcKomplPrice('standart') - цт1;
  // Колпаки Flow Vilpe — цена по формуле за штуку.
  вНабор('r23'); await пауза();
  const цк1 = calcKomplPrice('standart');
  const колпак = сКоличествамиКомплекта('standart', () => getOptPrice(getOpt('r23')));
  kedИзменитьКоличество('r23', 2); await пауза();
  р.приростКолпаков = calcKomplPrice('standart') - цк1; р.колпак = колпак;
  // Таблица комплектаций.
  renderKomplTable(); await пауза();
  р.ячейки = [...document.querySelectorAll('.kompl-qty')].map(э => э.textContent.trim());
  // Строки со счётчиком — в пределах списка.
  const список = document.getElementById('kedOptsList').getBoundingClientRect();
  р.заКраем = [...document.querySelectorAll('#kedOptsList .ked-qty')].filter(э => { const п = э.getBoundingClientRect(); return п.right > список.right + 1 || п.left < список.left - 1; }).length;
  р.кнопка = (() => { const к = document.querySelector('#kedOptsList .ked-qty .opt-qty-btn'); if (!к) return null; const п = к.getBoundingClientRect(); return [Math.round(п.width), Math.round(п.height)]; })();
  // Память браузера и база.
  try { р.память = JSON.parse(localStorage.getItem('kompl_qty_v1_standart')); } catch (e) { р.память = null; }
  await saveAllKitsForCurrentProject(); await пауза(300);
  const ряд = (window.__ТАБЛИЦЫ.project_kits || []).find(р_ => р_.name === 'Стандарт');
  р.база = ряд ? ряд.option_qty : null;
  KOMPL_QTY.standart = {};
  await loadKitsForCurrentProject(); await пауза(200);
  р.загружено = Object.assign({}, KOMPL_QTY.standart);
  // Применение.
  if (typeof closeKomplEditor === 'function') closeKomplEditor();
  formulaOverrides.w15 = { area: 7 };
  komplSelPreset('standart'); await applyKompl(); await пауза(600);
  р.вСпецификации = getOptQty(getOpt('w15'));
  р.имяВСпецификации = getOpt('w15').name;
  р.итог = _currentTotal; р.ценаКомплекта = calcKomplPrice('standart');
  р.совпадаетДо = _komplSnapshotsEqual(_komplStateSnapshot(), _appliedKitSnapshot);
  changeQty('w15', 1); await пауза();
  р.совпадаетПосле = _komplSnapshotsEqual(_komplStateSnapshot(), _appliedKitSnapshot);
  // Снятая опция теряет количество.
  openKompl(); await пауза(300); openKomplEditor(); await пауза(300); komplKedTab = 'standart';
  kedToggle(имя('w15')); await пауза();
  р.послеСнятия = KOMPL_QTY.standart.w15;
  return р;
}"""


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(д.ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    # Редактор комплектаций — у администратора.
    стр.add_init_script("document.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    try:
        р = стр.evaluate(ШАГИ)
    except Exception as e:
        НАХОДКИ.append(f"{н} проба оборвалась: {e!s:.300}"); стр.close(); return
    if not р["видно"]:
        НАХОДКИ.append(f"{н} редактор комплектаций не открылся — смотреть нечего")
    if р["кнопка"] and min(р["кнопка"]) < 18:
        НАХОДКИ.append(f"{н} кнопка счётчика в редакторе {р['кнопка']} px")
    if р["счётчикДо"] or not р["счётчикПосле"]:
        НАХОДКИ.append(f"{н} счётчик в редакторе: до отметки {р['счётчикДо']}, после {р['счётчикПосле']}")
    if р["приростДверей"] != 2 * ДВЕРЬ:
        НАХОДКИ.append(f"{н} три двери вместо одной — цена комплектации +{р['приростДверей']}, ждали +{2 * ДВЕРЬ}")
    if р["значение"] != "3" or р["ценаСтроки"] != 3 * ДВЕРЬ:
        НАХОДКИ.append(f"{н} строка дверей в редакторе: количество «{р['значение']}», цена {р['ценаСтроки']}")
    if р["полеТеррасы"] != "INPUT":
        НАХОДКИ.append(f"{н} у террасы нет поля площади: {р['полеТеррасы']}")
    if р["приростТеррасы"] != round(ТЕРРАСА * 20 / 12) - ТЕРРАСА:
        НАХОДКИ.append(f"{н} терраса 20 м² — прирост {р['приростТеррасы']}, ждали {round(ТЕРРАСА * 20 / 12) - ТЕРРАСА}")
    if not р["колпак"] or abs(р["приростКолпаков"] - 2 * р["колпак"]) > 2:
        НАХОДКИ.append(f"{н} три колпака Flow Vilpe — прирост {р['приростКолпаков']}, колпак {р['колпак']}")
    if "3 двери" not in р["ячейки"] or "20 м²" not in р["ячейки"] or "3 шт." not in р["ячейки"]:
        НАХОДКИ.append(f"{н} в таблице комплектаций количество: {р['ячейки']}")
    if р["заКраем"]:
        НАХОДКИ.append(f"{н} счётчик вылезает за список: {р['заКраем']}")
    if р["память"] != {"w15": 3, "e10": 20, "r23": 3}:
        НАХОДКИ.append(f"{н} в памяти браузера: {р['память']}")
    if р["база"] != {"w15": 3, "e10": 20, "r23": 3}:
        НАХОДКИ.append(f"{н} в базе option_qty: {р['база']}")
    if р["загружено"] != {"w15": 3, "e10": 20, "r23": 3}:
        НАХОДКИ.append(f"{н} загрузка из базы вернула: {р['загружено']}")
    if р["вСпецификации"] != 3 or not р["имяВСпецификации"].rstrip().endswith("за 3 двери"):
        НАХОДКИ.append(f"{н} после применения в спецификации: {р['вСпецификации']}, «{р['имяВСпецификации']}»")
    if р["итог"] != р["ценаКомплекта"]:
        НАХОДКИ.append(f"{н} итог после применения {р['итог']}, цена комплектации {р['ценаКомплекта']}")
    if not р["совпадаетДо"] or р["совпадаетПосле"]:
        НАХОДКИ.append(f"{н} совпадение с комплектацией: сразу {р['совпадаетДо']}, после смены количества {р['совпадаетПосле']}")
    if р["послеСнятия"] is not None:
        НАХОДКИ.append(f"{н} двери сняли из комплектации, а количество осталось: {р['послеСнятия']}")
    for е in ошибки[:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {е[:160]}")
    стр.close()


def главная():
    с, порт = д.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=д.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в комплектациях у поштучных опций и террасы — своё количество: счётчик в редакторе, цена "
          "комплектации и строки по нему, «3 двери» в таблице, база и загрузка, применение ставит количество, "
          "смена количества после — уже не комплектация; на 390 и 1440.")


if __name__ == "__main__":
    главная()
