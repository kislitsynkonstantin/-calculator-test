#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Нигде нет цветной черты сбоку — ни в выделении, ни в плашках.

Константин 18.10.2026, снимком всплывающих уведомлений с обведённой чертой
слева: «Вот боковое выделение убери — нигде его не используй. Запиши в
правила. Эту вертикальную полоску». До этого, тем же днём: «И нигде вот эту
дешевую полоску в выделении не используй».

Проба смотрит не исходник, а отрисовку: черта рождается и рамкой, и
inset-тенью, и узким псевдоэлементом, и встроенным стилем из скрипта.
В каждом состоянии она обходит все видимые элементы (и документы в кадрах
окна печати) и ищет:
  • рамку слева толщиной от 1,5 px, которой нет справа (или она другого
    цвета) — черта, а не рамка вокруг;
  • inset-тень со сдвигом по горизонтали и без размытия — черта тенью;
  • ::before / ::after шириной до 4,5 px и высотой от 10 px с заливкой или
    рамкой — черта слоем.
Состояния: главный экран с отмеченными опциями, выделенной строкой и
примечанием; мини-окно — «Пресет», «Сводка», «Журнал», «Проверка» с
плашкой согласования и правками из чата, «Чат» с ответом-цитатой и опцией;
окно «Пресеты» со своими, избранными и общими карточками; колокольчик;
окно печати с договором, где правлен пункт; «Копировать из комплектации».

    python3 check_no_side_stripe.py
"""
import os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []

ИЩЕМ = """() => {
  const прозрачно = ц => !ц || ц === 'transparent' || /rgba\\([^)]*,\\s*0\\)$/.test(ц);
  // Имя — по классам: у одинаковых строк разные id, а черта у них одна.
  const имя = э => э.tagName.toLowerCase() + (э.classList.length ? [...э.classList].slice(0, 3).map(к => '.' + к).join('') : (э.id ? '#' + э.id : ''));
  const найдено = [];
  const обойти = (док, где) => {
    док.querySelectorAll('*').forEach(э => {
      const р = э.getBoundingClientRect();
      if (!р.width || !р.height) return;
      const с = док.defaultView.getComputedStyle(э);
      if (с.visibility === 'hidden' || с.display === 'none' || +с.opacity === 0) return;
      const л = parseFloat(с.borderLeftWidth) || 0, п = parseFloat(с.borderRightWidth) || 0;
      if (л >= 1.5 && с.borderLeftStyle !== 'none' && !прозрачно(с.borderLeftColor) && р.height >= 10
          && (п < л - .5 || с.borderRightColor !== с.borderLeftColor || с.borderRightStyle === 'none'))
        найдено.push([где, имя(э), 'рамка слева ' + л + 'px ' + с.borderLeftColor]);
      (с.boxShadow || '').split(/,(?![^(]*\\))/).forEach(т => {
        if (!/inset/.test(т)) return;
        const ч = т.replace(/rgba?\\([^)]*\\)|#\\w+|inset/g, '').trim().split(/\\s+/).map(parseFloat);
        if (Math.abs(ч[0]) >= 1.5 && !ч[1] && !ч[2] && !(ч[3] > 0) && !/rgba\\([^)]*,\\s*0\\)/.test(т))
          найдено.push([где, имя(э), 'черта тенью ' + т.trim()]);
      });
      ['::before', '::after'].forEach(пс => {
        const сс = док.defaultView.getComputedStyle(э, пс);
        if (!сс || сс.content === 'none' || сс.content === 'normal' || сс.display === 'none') return;
        const ш = parseFloat(сс.width), в = parseFloat(сс.height);
        if (!(ш > 0 && ш <= 4.5 && в >= 10)) return;
        const залит = !прозрачно(сс.backgroundColor) || (сс.backgroundImage && сс.backgroundImage !== 'none')
          || (parseFloat(сс.borderLeftWidth) >= 1 && !прозрачно(сс.borderLeftColor));
        if (залит && +сс.opacity !== 0) найдено.push([где, имя(э) + пс, 'черта слоем ' + ш + '×' + Math.round(в) + ' ' + сс.backgroundColor]);
      });
    });
    док.querySelectorAll('iframe').forEach(к => { try { if (к.contentDocument && к.getBoundingClientRect().width) обойти(к.contentDocument, где + ' › кадр'); } catch (e) {} });
  };
  обойти(document, 'страница');
  const видели = new Set();
  return найдено.filter(х => { const к = х[1] + '|' + х[2].split(' ')[0] + х[2].split(' ')[1]; if (видели.has(к)) return false; видели.add(к); return true; });
}"""


ВИДЕЛИ = set()


def смотреть(стр, н, состояние):
    # Черта называется один раз — в первом состоянии, где она видна.
    for где, кто, что in стр.evaluate(ИЩЕМ):
        к = (кто, что.split(" ")[0] + что.split(" ")[1])
        if к in ВИДЕЛИ:
            continue
        ВИДЕЛИ.add(к)
        НАХОДКИ.append(f"{н} {состояние}: {кто} — {что}")


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    # Главный экран: отмеченные опции, выделенная цветом строка, примечание.
    стр.evaluate("""() => { const к = document.getElementById('presetChipCard'); if (к) к.classList.remove('show');
      const ч = [...document.querySelectorAll('.opt-item:not(.active) .opt-check')].slice(0, 4); ч.forEach(х => х.click());
      const в = document.querySelector('.opt-highlight-btn'); if (в) в.click(); }""")
    стр.wait_for_timeout(600)
    смотреть(стр, н, "главный экран")
    # Мини-окно: все вкладки; в «Проверке» — плашка согласования и правка из чата.
    стр.evaluate("""() => { window.__ТАБЛИЦЫ.preset_messages[0].review_state = 'open';
      window.__ТАБЛИЦЫ.preset_messages[1].attachments = [{ opt: 1, n: 'Полок из липы', s: 'Парная', p: 45000, k: 'p1' }]; }""")
    ч.открыть(стр)
    for вк in ["p", "s", "j", "c", "m"]:
        if стр.locator(f"#pcTab-{вк}").count():
            ч.вкладка(стр, вк); стр.wait_for_timeout(500)
            смотреть(стр, н, f"мини-окно, вкладка {вк}")
    стр.evaluate("() => { начатьОтвет && начатьОтвет('11111111-1111-4111-8111-111111111111'); }") if стр.evaluate("() => typeof начатьОтвет === 'function'") else None
    стр.wait_for_timeout(300)
    смотреть(стр, н, "чат с ответом")
    стр.mouse.click(5, 5); стр.wait_for_timeout(300)
    # Окно «Пресеты».
    стр.evaluate("() => { const к = document.getElementById('presetChipCard'); if (к) к.classList.remove('show'); openPresetPanel(); }")
    стр.wait_for_timeout(900)
    смотреть(стр, н, "окно «Пресеты»")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(300)
    # Колокольчик.
    стр.evaluate("() => { try { переключитьУведомления(); } catch (e) {} }"); стр.wait_for_timeout(900)
    смотреть(стр, н, "колокольчик")
    стр.keyboard.press("Escape"); стр.mouse.click(5, 5); стр.wait_for_timeout(300)
    # Окно печати: договор с правленым пунктом.
    стр.evaluate("""async () => { try { window._sbProfile.role = 'admin'; } catch (e) {}
      try { openContractPreview && openContractPreview(); } catch (e) {}
      try { setPreviewEntity('contract'); } catch (e) {}
      await new Promise(р => setTimeout(р, 900));
      try { buildContractHtmlKar(getContractVarsKar(1)); const т = _типовыеПункты.kar || {}, н = Object.keys(т)[4];
        _правкиДоговора.kar = { [н]: { части: [{ т: 'Изменённый пункт договора для пробы.' }], база: т[н].части, кто: 'Проба', когда: new Date().toISOString() } };
        refreshContractPreview(); } catch (e) {} }""")
    стр.wait_for_timeout(1200)
    смотреть(стр, н, "окно печати, договор")
    # «Копировать из комплектации».
    стр.evaluate("async () => { try { await openKomplCopyDialog(); } catch (e) {} }"); стр.wait_for_timeout(900)
    смотреть(стр, н, "копирование комплектации")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"stripes-{ш}.png"))
    стр.close()


# Исходник — для состояний, до которых обход не доходит (стили печати,
# редкие окна): черта рамкой от 1,5 px и черта inset-тенью.
ИСХОДНИК = [
    (re.compile(r"border-left(?:-width)?\s*:\s*(?:[2-9]|1\.[5-9])(?:\.\d+)?(?:px|pt|mm)(?![^;}'\"]*transparent)"), "рамка слева"),
    (re.compile(r"inset\s+-?(?:[2-9]|1\.[5-9])(?:\.\d+)?px\s+0(?:px)?\s+0(?:px)?\s"), "черта тенью"),
]


def исходник():
    текст = (м.КОРЕНЬ / "index.html").read_text(encoding="utf-8")
    for н, строка in enumerate(текст.split("\n"), 1):
        for шаблон, что in ИСХОДНИК:
            if шаблон.search(строка):
                НАХОДКИ.append(f"index.html:{н} — {что}: {строка.strip()[:110]}")


def главная():
    исходник()
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900)
                прогон(бр, порт, 390, 844)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: ни рамки слева, ни черты тенью, ни узкого слоя-черты — на главном экране, во всех вкладках мини-окна, "
          "в окне «Пресеты», колокольчике, окне печати с договором и в копировании комплектации, на 390 и 1440.")


if __name__ == "__main__":
    главная()
