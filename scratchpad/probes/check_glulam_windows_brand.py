#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: переключатель Veka / Rehau — как у каркаса.

Константин 09.10.2026, снимком окон бруса на телефоне: «А где переключатель
Века/Рехау? Также как в каркасе должно быть». У бруса те же четыре строки, что
у каркаса: базовые окна (строка базы), окна 70 и 82 мм, стеклянная дверь. Имена
— каркасные, бренд один на расчёт.

Цены здесь выдуманные. Проба нажимает и смотрит на имя, отметку и итог:

  • у четырёх строк бруса есть переключатель, по умолчанию Veka, имена —
    каркасные (Veka WHS 72, softline 70, softline 82 MD, дверь Veka);
  • щелчок Rehau на одной строке переводит все четыре, отметка и итог не
    меняются; в печати стоит выбранное имя;
  • сохранённый расчёт бруса открывается с тем брендом, с которым сохранён, —
    и Rehau, и Veka; Veka не должен превращаться в Rehau оттого, что при
    открытии каркасные id вычищаются;
  • расчёт бруса без бренда, и тот, где бренд записан только каркасной строкой
    (так сохранял боевой калькулятор до переключателя), открывается с Rehau —
    окна бруса тогда назывались только Rehau;
  • вид: переключатель в строке базы и в строках опций не вылезает за строку
    и не прилипает к соседям — на 390 и 1440.

Слепое пятно, закрытое 09.10.2026: в первой версии у всех окон была цена в
прайсе, а в базе у окон бруса она только в таблице проекта. Такую строку
перестраивает refreshOptPricesInDOM, и переключатель терялся — проба этого
не видела, а на снимке с настоящими данными его не оказалось. Теперь у окон
70 и у двери цена только в таблице проекта.

    python3 check_glulam_windows_brand.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ИДЫ = ["kb_bp_wd_1", "kb_w1", "kb_w2", "kb_w7"]
VEKA = {"kb_bp_wd_1": "Пластиковые окна Veka WHS 72, 5 камер (с фурнитурой Internika)",
        "kb_w1": "Пластиковые окна Veka softline 70, 5 камер, класс стенок А (с фурнитурой Internika)",
        "kb_w2": "Пластиковые окна Veka softline 82 MD, 7 камер, 3 контура утепления (с фурнитурой Internika)",
        "kb_w7": "Входная дверь — стеклянная ПВХ Veka"}
REHAU = {"kb_bp_wd_1": "Пластиковые окна Rehau профиль Blitz 60 (с фурнитурой Roto, Reze или аналоги)",
         "kb_w1": "Пластиковые окна Rehau профиль Grazio 70 (с фурнитурой Roto, Reze или аналоги)",
         "kb_w2": "Пластиковые окна Rehau профиль Intelio 80 (с фурнитурой Roto, Reze или аналоги)",
         "kb_w7": "Входная дверь — стеклянная ПВХ Rehau"}


def таблицы():
    т = г.таблицы()
    оп = lambda ид, имя, цена, базовая=False: {"product": "glulam", "option_id": ид, "name": имя,
            "section": "windows", "included": базовая, "status": None, "formula": None,
            "price": None if базовая else цена, "sort": 400}
    т["pricing_options"] += [
        оп("kb_bp_wd_1", "Пластиковые окна Veka WHS 72, 5 камер (с фурнитурой Internika)", None, True),
        оп("kb_w1", "Пластиковые окна Veka softline 70, 5 камер, класс стенок А (с фурнитурой Internika)", None),
        оп("kb_w2", "Пластиковые окна Veka softline 82 MD, 7 камер, 3 контура утепления (с фурнитурой Internika)", 90000),
        оп("kb_w7", "Входная дверь - стеклянная ПВХ Rehau (профиль по комплектации окон)", None),
    ]
    # Как в базе: у окон 70 и у двери цены нет в прайсе, она лежит только в
    # таблице проекта. Такая строка строится полем «введите сумму» и после
    # выбора проекта перестраивается — переключатель при этом пропадал.
    т["pricing_matrix"] += [{"product": "glulam", "project_slug": "Брус проба 6×6", "option_id": о, "price": ц}
                            for о, ц in (("kb_w1", 60000), ("kb_w7", 50000))]
    # Первым в списке — проект без таблицы цен: строки строятся полем «введите
    # сумму» и перестраиваются, когда выбран проект с ценами. Без него строки
    # сразу строились с ценой, и перестройка не проверялась.
    т["pricing_projects"].insert(0, dict([п for п in т["pricing_projects"] if п["product"] == "glulam"][0],
                                         slug="Брус без цен окон", name="Брус без цен окон", sort=0))
    return т


СОСТОЯНИЕ = """(иды) => { const р = {};
  иды.forEach(ид => { const э = document.querySelector('#lbl_' + ид + ' .opt-name');
    const к0 = document.getElementById('ovar_' + ид + '_0'), к1 = document.getElementById('ovar_' + ид + '_1');
    р[ид] = { имя: (OPTIONS.find(o => o.id === ид) || {}).name, экран: э ? э.textContent.trim() : null,
              тумблер: !!(к0 && к1 && к0.getClientRects().length), veka: !!(к0 && к0.classList.contains('active')),
              rehau: !!(к1 && к1.classList.contains('active')) }; });
  р._итог = Math.round(_currentTotal || 0); р._отм = !!checkedOptions.kb_w1; return р; }"""

ВИД = """(иды) => { const н = [];
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) н.push('прокрутка вбок');
  иды.forEach(ид => {
    const стр = document.getElementById('lbl_' + ид); const т = стр && стр.querySelector('.cmode-toggle');
    if (!т || !т.getClientRects().length) return;
    const р = т.getBoundingClientRect(), с = стр.getBoundingClientRect();
    if (р.right > с.right + 0.5 || р.left < с.left - 0.5) н.push(ид + ': переключатель вылезает за строку');
    const соседи = [...т.parentElement.children].filter(э => э !== т && э.getClientRects().length).map(э => э.getBoundingClientRect())
      .filter(б => б.top < р.bottom && б.bottom > р.top);
    соседи.forEach(б => { const зазор = Math.max(б.left - р.right, р.left - б.right);
      if (зазор < 2) н.push(ид + ': переключатель прилип к соседу (' + Math.round(зазор) + ' px)'); });
  });
  return н; }"""


def сверить(н, р, бренд, что):
    имена = VEKA if бренд == "veka" else REHAU
    for ид in ИДЫ:
        с = р[ид]
        if not с["тумблер"]:
            НАХОДКИ.append(f"{н} {что}: у {ид} нет переключателя")
            continue
        if с["имя"] != имена[ид] or с["экран"] != имена[ид]:
            НАХОДКИ.append(f"{н} {что}: {ид} — «{с['экран']}», ждали «{имена[ид]}»")
        if not с[бренд]:
            НАХОДКИ.append(f"{н} {что}: у {ид} нажата не та половина (veka {с['veka']}, rehau {с['rehau']})")


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к = бр.new_context(viewport={"width": ш, "height": 900})
    стр = к.new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async () => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0] === 'Брус проба 6×6'));
      setThickness(1); toggleOpt('kb_w1'); calc(); await new Promise(r => setTimeout(r, 300)); }""")
    р = стр.evaluate(СОСТОЯНИЕ, ИДЫ)
    сверить(н, р, "veka", "новый расчёт")
    итог0 = р["_итог"]
    for в in стр.evaluate(ВИД, ИДЫ):
        НАХОДКИ.append(f"{н} вид: {в}")
    try:
        стр.locator("#lbl_kb_w1").scroll_into_view_if_needed()
        стр.screenshot(path=f"/tmp/kb_brand_{ш}.png")
    except Exception:
        pass

    # Rehau одним щелчком на одной строке. Щёлкаем в строке двери: окна 82 мм
    # при отмеченных 70 мм закрыты автоматикой (v2.5.16 (13)), и переключатель
    # в закрытой строке не нажимается — так же, как у каркаса.
    if стр.locator("#ovar_kb_w7_1").count():
        стр.locator("#ovar_kb_w7_1").scroll_into_view_if_needed()
        стр.locator("#ovar_kb_w7_1").click()
        стр.wait_for_timeout(300)
    р = стр.evaluate(СОСТОЯНИЕ, ИДЫ)
    сверить(н, р, "rehau", "щелчок Rehau")
    if р["_итог"] != итог0 or not р["_отм"]:
        НАХОДКИ.append(f"{н} щелчок Rehau: итог {итог0} → {р['_итог']}, окна 70 отмечены {р['_отм']}")
    печать = стр.evaluate("async () => { openPrintPreview(); await new Promise(r => setTimeout(r, 500)); const т = document.getElementById('printDoc').textContent; closePrintPreview(); return т; }")
    if REHAU["kb_w1"] not in печать:
        НАХОДКИ.append(f"{н} в печати нет имени Rehau у окон 70")

    # Сохранили и открыли: Rehau и Veka держатся
    for бренд, i in (("rehau", 1), ("veka", 0)):
        стр.evaluate(f"""async () => {{ setOptVariant('kb_w1', {i}); const с = JSON.parse(JSON.stringify(collectState()));
          restoreState(с); await new Promise(r => setTimeout(r, 500)); calc(); }}""")
        сверить(н, стр.evaluate(СОСТОЯНИЕ, ИДЫ), бренд, f"сохранён с {бренд}, открыт")
        # и ещё раз: открытие вычищает чужие id, второй круг ловит потерю бренда
        стр.evaluate("""async () => { const с = JSON.parse(JSON.stringify(collectState()));
          restoreState(с); await new Promise(r => setTimeout(r, 500)); calc(); }""")
        сверить(н, стр.evaluate(СОСТОЯНИЕ, ИДЫ), бренд, f"сохранён с {бренд}, открыт дважды")

    # Старые расчёты: без бренда и с брендом только у каркасной строки
    for что, правка in (("без бренда", "delete с.optVariants;"),
                        ("бренд только у каркасной строки", "с.optVariants = { ex4: 0, w1: 0, w8: 0, w9: 0, w14: 0 };")):
        стр.evaluate(f"""async () => {{ setOptVariant('kb_w1', 0); const с = JSON.parse(JSON.stringify(collectState()));
          {правка} restoreState(с); await new Promise(r => setTimeout(r, 500)); calc(); }}""")
        сверить(н, стр.evaluate(СОСТОЯНИЕ, ИДЫ), "rehau", f"старый расчёт, {что}")

    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    print(f"  {н} проверено: новый, щелчок, печать, сохранение, старые расчёты")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
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
    print("Чисто: у бруса переключатель Veka/Rehau на четырёх строках, как у каркаса, — один на все, "
          "итог не трогает, сохраняется и открывается тем же брендом; старые расчёты бруса — с Rehau.")


if __name__ == "__main__":
    главная()
