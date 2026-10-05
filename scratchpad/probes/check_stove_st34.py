#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Печь Изистим Ялта в камне до 25 м³ — дровяная печь каталога, как остальные.

Константин 05.10.2026, снимком своей опции «Печь Изистим Ялта в камне до
25м3» за 229 000 ₽: «добавь эту опцию с такой ценой».

Проба нажимает и смотрит на поведение, а не на разметку:
  • опция st34 стоит в разделе «Печь и комплектующие» сразу после печи
    Grill’D и стоит 229 000 ₽ (цена в пробе — та же, что в базе);
  • выбрана — закрывает остальные дровяные и электрические печи и сама
    ставит обязательный набор дровяной печи: установку, дымоход, портал,
    притопочный лист, камень;
  • выбрана другая дровяная — закрыта уже Ялта;
  • в «Проверке» Ялта — печь в камне: при дымоходе в металле есть замечание
    о разной облицовке, а «Указать модель печи» при установке печи — нет.

    python3 check_stove_st34.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_doors_qty as д  # noqa: E402  (сервер, Chromium, заглушка базы)
from playwright.sync_api import sync_playwright  # noqa: E402

НАХОДКИ = []
ЯЛТА = 229000
# Цены — как в базе на 05.10.2026: опция без цены не отмечается вовсе.
ЦЕНЫ = {"st34": ЯЛТА, "st16": 58700, "st17": 73300, "st3": 64700, "st4": 66660,
        "st1": 89645, "st6": 97700, "st15": 53145, "st12": 2300, "st20": 28200, "st27": 15850}
ОПЦИИ = [o for o in д.ДАННЫЕ["pricing_options"] if o["option_id"] not in ЦЕНЫ] + [
    {"product": "frame", "option_id": к, "section": "stove", "name": "", "included": False,
     "price": ц, "formula": None, "status": None, "sort": 200} for к, ц in ЦЕНЫ.items()]
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(д.ДАННЫЕ, pricing_options=ОПЦИИ), ensure_ascii=False) + ");")

ШАГИ = """async () => {
  const пауза = (мс = 250) => new Promise(r => setTimeout(r, мс));
  const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  selectProjectOption(0); await пауза(800);
  const закрыта = id => { const л = document.getElementById('lbl_' + id); return !!л && л.dataset.blocked === '1'; };
  const р = {};
  const печи = OPTIONS.filter(o => o.section === 'stove').map(o => o.id);
  р.место = печи.indexOf('st34') === печи.indexOf('st25') + 1 && печи.includes('st34');
  р.имя = (OPTIONS.find(o => o.id === 'st34') || {}).name || '';
  р.цена = getOptPrice(OPTIONS.find(o => o.id === 'st34'));
  toggleOpt('st34'); await пауза();
  р.отмечена = !!checkedOptions.st34;
  р.набор = ['st1', 'st6', 'st15', 'st12', 'st20'].filter(id => !checkedOptions[id]);
  // Снятые с продажи (status legacy, например st5) на экран не выходят — закрывать нечего.
  р.открыты = ['st16', 'st17', 'st25', 'st3', 'st4', 'st5'].filter(id => document.getElementById('lbl_' + id) && !закрыта(id));
  toggleOpt('st27'); await пауза();
  const замечания = проверкаПоЧекЛисту();
  р.проверка = (Array.isArray(замечания) ? замечания : (замечания && замечания.замечания) || []).map(з => з.т || '');
  toggleOpt('st27'); await пауза();
  toggleOpt('st34'); await пауза();
  toggleOpt('st16'); await пауза();
  р.ялтаЗакрыта = закрыта('st34');
  return р;
}"""


def главная():
    с, порт = д.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=д.хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 390, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(д.ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            р = стр.evaluate(ШАГИ)
            if р["имя"] != "Печь Изистим Ялта в камне до 25 м³" or not р["место"]:
                НАХОДКИ.append(f"опция Ялты: «{р['имя']}», после Grill’D: {р['место']}")
            if р["цена"] != ЯЛТА:
                НАХОДКИ.append(f"цена Ялты {р['цена']}, ждали {ЯЛТА}")
            if not р["отмечена"]:
                НАХОДКИ.append("Ялта не отмечается")
            if р["набор"]:
                НАХОДКИ.append(f"обязательный набор дровяной печи не встал сам: нет {р['набор']}")
            if р["открыты"]:
                НАХОДКИ.append(f"при Ялте остались открыты другие печи: {р['открыты']}")
            if True:
                if not any("облицовк" in т for т in р["проверка"]):
                    НАХОДКИ.append(f"«Проверка»: Ялта в камне с дымоходом в металле — замечания об облицовке нет: {р['проверка']}")
                if any("Указать модель печи" in т for т in р["проверка"]):
                    НАХОДКИ.append("«Проверка» просит указать модель печи, хотя Ялта выбрана")
            if not р["ялтаЗакрыта"]:
                НАХОДКИ.append("выбрана другая дровяная печь, а Ялта открыта")
            for е in ошибки[:3]:
                НАХОДКИ.append(f"ошибка страницы: {е[:160]}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: печь Изистим Ялта в камне — дровяная печь каталога за 229 000 ₽: закрывает остальные печи, ставит "
          "обязательный набор, закрывается другой дровяной; в «Проверке» — печь в камне.")


if __name__ == "__main__":
    главная()
