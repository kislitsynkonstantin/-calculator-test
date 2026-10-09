#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус: вместо договоров и правил эксплуатации каркаса — заглушка.

Константин 09.10.2026, снимком меню документа в окне печати бруса: «В брусе
отображаются договоры каркаса. Пока заглушки поставь на договоры и правила
эксплуатации — там будут свои».

Проба на 390 и 1440 держит:
  • у бруса «Основной договор», «Договор на отделку» и «Правила
    эксплуатации» открывают заглушку со своим заголовком, а кадр договора
    каркаса скрыт;
  • на заглушке «Печать / PDF» выключена, нажатие ничего не печатает, нет
    «Скрыть поля», «Google Диска», срока и состава договора;
  • старый путь «Скачать договор» тоже ничего не печатает;
  • согласие на обработку данных у бруса открывается документом и
    печатается, как прежде;
  • у каркаса договор открывается документом, заглушки нет.

    python3 check_glulam_contract_stub.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

ВИД = """() => { const в = id => { const э = document.getElementById(id); if (!э) return false;
    const r = э.getBoundingClientRect(); return getComputedStyle(э).display !== 'none' && r.width > 0 && r.height > 0; };
  const п = document.getElementById('printDocBtn');
  return { сущность: previewEntity, заглушка: в('contractPreviewStub'), договор: в('contractPreviewDoc'),
    заголовок: (document.getElementById('contractPreviewStubTitle') || {}).textContent || '',
    текст: (document.getElementById('contractPreviewStubText') || {}).textContent || '',
    печатьВыкл: !!(п && п.disabled), поля: в('contractHlToggleBtn'), диск: в('contractDriveBtn'),
    срок: в('contractTermWrap'), состав: в('printSectionsBar') || в('printSectionDropdownWrap'),
    кадрПечати: !!document.getElementById('contractPrintFrame'),
    метка: document.getElementById('previewEntityLabel').textContent.trim(),
    шир: document.documentElement.scrollWidth, экран: innerWidth }; }"""

ЖДЁМ = {"1": "Основной договор для клеёного бруса готовится",
        "2": "Договор на отделку для клеёного бруса готовится",
        "rules": "Правила эксплуатации для клеёного бруса готовятся"}


def открыть(стр, тех):
    стр.evaluate("""async (тех) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      try { closePrintPreview(); } catch (e) {}
      await switchTech(тех); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0] === (тех === 'glulam' ? 'Брус проба 6×6' : 'Каркас проба 6×4')));
      setThickness(1); await new Promise(r => setTimeout(r, 300));
      // Отделка в расчёте — иначе второго договора нет.
      const о = OPTIONS.find(o => (o.section === 'steam' || o.section === 'interior') && !o.included && !checkedOptions[o.id]);
      if (о) toggleOpt(о.id);
      calc(); document.getElementById('contractNumber').value = '11112222';
      openPrintPreview(); await new Promise(r => setTimeout(r, 500)); }""", тех)


def выбрать(стр, что):
    if что == "rules":
        стр.evaluate("() => выбратьПравила()")
    elif что == "consent":
        стр.evaluate("() => выбратьСогласие()")
    else:
        стр.evaluate(f"() => выбратьДоговорОкна({что})")
    стр.wait_for_timeout(900)
    return стр.evaluate(ВИД)


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к = бр.new_context(viewport={"width": ш, "height": 900})
    стр = к.new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(г.таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    открыть(стр, "glulam")
    if not стр.evaluate("() => естьДоговор(2)"):
        НАХОДКИ.append(f"{н} в расчёте бруса нет договора на отделку — проверить его нечем")
    for что in ("1", "2", "rules"):
        в = выбрать(стр, что)
        if not в["заглушка"] or в["договор"]:
            НАХОДКИ.append(f"{н} брус, «{что}»: заглушка {в['заглушка']}, кадр договора каркаса {в['договор']}")
            continue
        if в["заголовок"] != ЖДЁМ[что]:
            НАХОДКИ.append(f"{н} брус, «{что}»: заголовок «{в['заголовок']}», ждали «{ЖДЁМ[что]}»")
        if not в["печатьВыкл"] or в["поля"] or в["диск"] or в["срок"] or в["состав"]:
            НАХОДКИ.append(f"{н} брус, «{что}»: печать выключена {в['печатьВыкл']}, «Скрыть поля» {в['поля']}, "
                           f"Диск {в['диск']}, срок {в['срок']}, состав {в['состав']}")
        стр.evaluate("() => { const ф = document.getElementById('contractPrintFrame'); if (ф) ф.remove(); printFromPreview(); printContractKar(); }")
        стр.wait_for_timeout(300)
        if стр.evaluate("() => !!document.getElementById('contractPrintFrame')"):
            НАХОДКИ.append(f"{н} брус, «{что}»: печать собрала документ каркаса")
        if в["шир"] > в["экран"]:
            НАХОДКИ.append(f"{н} брус, «{что}»: страница шире экрана ({в['шир']} > {в['экран']})")
        if что == "1":
            стр.screenshot(path=str(м.СНИМКИ / f"glulam-stub-{ш}.png"))
    # Старый путь «Скачать договор» — со вкладки спецификации.
    стр.evaluate("() => { setPreviewEntity('spec'); const ф = document.getElementById('contractPrintFrame'); if (ф) ф.remove(); printContractKar(); }")
    стр.wait_for_timeout(300)
    if стр.evaluate("() => !!document.getElementById('contractPrintFrame')"):
        НАХОДКИ.append(f"{н} брус: «Скачать договор» со спецификации собрал договор каркаса")
    в = выбрать(стр, "consent")
    if в["заглушка"] or not в["договор"] or в["печатьВыкл"]:
        НАХОДКИ.append(f"{н} брус, согласие: заглушка {в['заглушка']}, документ {в['договор']}, печать выключена {в['печатьВыкл']}")
    стр.evaluate("() => setPreviewEntity('spec')"); стр.wait_for_timeout(300)
    if стр.evaluate("() => document.getElementById('printDocBtn').disabled"):
        НАХОДКИ.append(f"{н} брус: после заглушки печать спецификации осталась выключенной")
    открыть(стр, "frame")
    for что in ("1", "rules"):
        в = выбрать(стр, что)
        if в["заглушка"] or not в["договор"] or в["печатьВыкл"]:
            НАХОДКИ.append(f"{н} каркас, «{что}»: заглушка {в['заглушка']}, документ {в['договор']}, печать выключена {в['печатьВыкл']}")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    print(f"  {н} проверено: брус — два договора, правила, согласие; каркас — договор и правила")
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
    print("Чисто: у бруса оба договора и правила эксплуатации — заглушка со своим заголовком, печать и Диск их не выдают; "
          "согласие у бруса и договоры каркаса открываются документом — на 390 и 1440.")


if __name__ == "__main__":
    главная()
