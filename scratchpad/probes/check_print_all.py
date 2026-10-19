#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Печатать всё»: комплект документов одним заданием принтеру.

Константин 18.10.2026: «В режиме спецификации добавь ещё кнопку «Печатать
всё» — там выпадающий список, стоят галочки на все документы. Если нужно
какой-то убрать, снимает — далее нажимает «Печать» и в задание принтеру по
порядку весь комплект загружается. Чтобы каждый отдельно не печатать».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • кнопка есть только у спецификации; список — документы меню в его порядке,
    все с галочкой; спецификация — строкой на каждый договор платёжного плана
    («Спецификация · Основной договор»), в ней разделы своего договора и его
    номер с кодом, выбор разделов в окне печати после сборки прежний; снятая галочка снимается и помнится, число на кнопке
    «Печать» меняется, без единой галочки печать выключена;
  • менеджеру до согласования договорные документы в списке приглушены, без
    галочки и со словами «После согласования спецификации»;
  • комплект — один документ: Chromium печатает его в PDF ровно на столько
    страниц, сколько выходит у документов по отдельности, и каждая страница
    комплекта совпадает со страницей своего документа, кроме номера страницы
    в верхнем поле (его в комплекте нет — счётчик у задания один); версия
    договора в поле остаётся; лист реквизитов договора — с полями документа;
  • «Выбрать все / Снять все» в заголовке списка: надпись по состоянию,
    список не закрывается, закрытые документы не трогаются; в строке
    заголовка, не вплотную, тише строк, поле нажатия не меньше 38 px;
  • вёрстка на 390 и 1440: «Печать / PDF» и «Печатать всё» в одном ряду,
    на 1440 весь ряд кнопок — одной строкой; список в экране, строки списка
    и кнопка печати не ниже 44 px по полю нажатия.

    python3 check_print_all.py
"""
import glob, os, pathlib, re, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


СПИСОК = """() => [...document.querySelectorAll('#printAllMenu .pa-i')].map(б => ({ т: б.querySelector('.pa-n > span').textContent,
  да: б.getAttribute('aria-checked') === 'true', выкл: б.classList.contains('pa-off'), почему: (б.querySelector('.pa-why') || {}).textContent || '' }))"""

ВЁРСТКА = """() => { const н = [], W = document.documentElement.clientWidth;
  const печ = document.getElementById('printDocBtn').getBoundingClientRect(), всё = document.getElementById('printAllBtn').getBoundingClientRect();
  if (Math.abs(печ.top - всё.top) > 1) н.push('«Печатать всё» не в ряду с «Печать / PDF»');
  if (всё.left - печ.right < 6) н.push('«Печатать всё» вплотную к «Печать / PDF»: ' + Math.round(всё.left - печ.right));
  const м = document.getElementById('printAllMenu'), мр = м.getBoundingClientRect();
  if (мр.left < 0 || мр.right > W + .5) н.push('список за краем экрана: ' + Math.round(мр.left) + '/' + Math.round(мр.right));
  if (м.scrollWidth > м.clientWidth + 1) н.push('список шире себя');
  м.querySelectorAll('.pa-i, .pa-go').forEach(б => { const р = б.getBoundingClientRect();
    if (р.height < 37.5) н.push('поле нажатия ' + б.className + ' по высоте ' + Math.round(р.height)); });
  if (document.documentElement.scrollWidth > W + 1) н.push('страница шире экрана');
  return н; }"""


def страниц(путь):
    return int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", путь], capture_output=True, text=True).stdout).group(1))


def в_пдф(к, html, путь):
    л = к.new_page(); л.set_content(html, wait_until="load"); л.wait_for_timeout(1500)
    л.pdf(path=путь, format="A4", prefer_css_page_size=True, print_background=True); л.close()
    return страниц(путь)


def сравнить(папка, ключи):
    """Каждая страница комплекта — против страницы своего документа."""
    from PIL import Image, ImageChops
    subprocess.run(["pdftoppm", "-r", "40", "-png", f"{папка}/комплект.pdf", f"{папка}/к"], check=True)
    к = sorted(glob.glob(f"{папка}/к-*.png")); и = 0; н = []
    for кл in ключи:
        subprocess.run(["pdftoppm", "-r", "40", "-png", f"{папка}/{кл}.pdf", f"{папка}/о-{кл}"], check=True)
        for ф in sorted(glob.glob(f"{папка}/о-{кл}-*.png")):
            if и >= len(к):
                н.append(f"в комплекте не хватает страниц ({кл})"); return н
            а = Image.open(ф).convert("L"); б = Image.open(к[и]).convert("L")
            д = ImageChops.difference(а, б).point(lambda v: 255 if v > 40 else 0)
            # Верхнее поле справа — номер страницы; его в комплекте нет.
            w, h = д.size
            д.paste(0, (int(w * .75), 0, w, int(h * .06)))
            if кл == "appx":
                # Номер листа «Вида и плана» в комплекте — строкой в самом листе:
                # содержимое листа ниже на её высоту, сверка по строкам не годится.
                и += 1; continue
            доля = sum(1 for x in д.tobytes() if x) / (w * h)
            if доля > 0.015:
                н.append(f"{кл} стр. {os.path.basename(ф)} в комплекте не такая, как отдельно: {доля:.2%}")
            и += 1
    if и != len(к):
        н.append(f"страниц в комплекте {len(к)}, по отдельности {и}")
    return н


def прогон(бр, порт, ш, полный):
    н = f"[{ш}]"
    к, стр, ош = о.начать(бр, порт, ш, "admin")
    стр.evaluate("() => { const ч = document.getElementById('cashDiscountCheck'); ч.checked = true; ч.dispatchEvent(new Event('change', { bubbles: true })); calc(); setPreviewEntity('spec'); }")
    стр.wait_for_timeout(600)
    # Кнопка — только у спецификации.
    for сущ in ("contract", "appx"):
        стр.evaluate("(с) => setPreviewEntity(с)", сущ); стр.wait_for_timeout(300)
        if стр.evaluate("() => !!document.getElementById('printAllBtn').getClientRects().length"):
            плохо(f"{н} «Печатать всё» видна не у спецификации ({сущ})")
    стр.evaluate("() => setPreviewEntity('spec')"); стр.wait_for_timeout(400)
    стр.locator("#printAllBtn").click(); стр.wait_for_timeout(300)
    с = стр.evaluate(СПИСОК)
    меню = стр.evaluate("() => [...document.querySelectorAll('#previewEntityMenu [data-entity]')].filter(б => getComputedStyle(б).display !== 'none').map(б => б.querySelector('.ent-name > span, span:not(.entity-check)').textContent.trim())")
    if [х["т"] for х in с] != ["Спецификация · Основной договор", "Спецификация · Договор на отделку", "Вид и план", "Основной договор", "Договор на отделку", "Приходный ордер", "Правила эксплуатации", "Согласие на обработку данных"] \
            or not all(х["да"] for х in с):
        плохо(f"{н} список комплекта: {с}; меню документа: {меню}")
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {т}")
    if ш >= 1024 and стр.evaluate("() => { const р = document.querySelector('.print-pair').parentElement; return new Set([...р.children].filter(э => э.getClientRects().length && getComputedStyle(э).position !== 'absolute').map(э => Math.round(э.getBoundingClientRect().top))).size; }") != 1:
        плохо(f"{н} ряд кнопок панели печати не в одну строку")
    # Спецификация делится по договорам платёжного плана (Константин,
    # 18.10.2026: «дели договоры, как они разбиты в платёжном плане»): у
    # каждой строки — разделы своего договора и его номер с кодом; выбор
    # разделов в окне печати после сборки тот же.
    сп = стр.evaluate("""async () => { const было = [...printActiveSections].sort().join(','), былД = printActiveContractId;
      const лист = к => new DOMParser().parseFromString(к, 'text/html');
      const р = {};
      for (const c of составыСпецификации()) { const д = лист(await htmlДокументаКомплекта('spec-' + c.id)), т = д.body.textContent.replace(/\\s+/g, ' ');
        // Разделы — по заголовкам разделов листа: «Каркас» есть и в строке технологии.
        const заг = [...д.querySelectorAll('.bl-sname')].map(э => э.textContent.trim());
        р[c.id] = { код: (т.match(/№\\s*\\S+-(КАР|ОТД|КБ)/) || [])[1] || '', разделы: SECTIONS.filter(с => заг.includes(с.name.replace(/^\\d+\\.\\s*/, ''))).map(с => с.key),
          свои: c.sections }; }
      return { р, назад: [...printActiveSections].sort().join(',') === было && printActiveContractId === былД }; }""")
    for ид, д in сп["р"].items():
        чужие = [к for к in д["разделы"] if к not in д["свои"]]
        if чужие or not д["разделы"] or д["код"] != ("КАР" if ид == "1" else "ОТД"):
            плохо(f"{н} спецификация договора {ид}: код «{д['код']}», разделы {д['разделы']}, чужие {чужие}")
    if not сп["назад"]:
        плохо(f"{н} после сборки спецификации по договору выбор разделов в окне печати не вернулся")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"print-all-{ш}.png"))
    # Галочка снимается, число на кнопке меняется, без галочек печать выключена.
    стр.locator("#printAllMenu .pa-i", has_text="Согласие").click(); стр.wait_for_timeout(200)
    кн = стр.evaluate("() => ({ т: document.querySelector('#printAllMenu .pa-go').textContent.trim(), выкл: document.querySelector('#printAllMenu .pa-go').disabled })")
    с = стр.evaluate(СПИСОК)
    if кн["т"] != "Печать · 7" or [х["да"] for х in с][-1]:
        плохо(f"{н} снятая галочка: {кн}, {с[-1]}")
    # Список не закрывается от галочки — их ставят по одной (Константин,
    # 18.10.2026: «чтобы можно было галочки по одной нажимать и окно не
    # закрывалось. Сейчас закрывается, каждый раз когда нажимаю»).
    открыт = "() => getComputedStyle(document.getElementById('printAllMenu')).display !== 'none'"
    if not стр.evaluate(открыт):
        плохо(f"{н} список «Печатать всё» закрылся после галочки")
    else:
        стр.locator("#printAllMenu .pa-i", has_text="Правила").click(); стр.wait_for_timeout(200)
        кн2 = стр.evaluate("() => document.querySelector('#printAllMenu .pa-go').textContent.trim()")
        if not стр.evaluate(открыт) or кн2 != "Печать · 6":
            плохо(f"{н} вторая галочка подряд: список открыт {стр.evaluate(открыт)}, кнопка «{кн2}»")
        стр.locator("#printAllMenu .pa-i", has_text="Правила").click(); стр.wait_for_timeout(200)
    стр.evaluate("() => { закрытьКомплект(); }"); стр.locator("#printAllBtn").click(); стр.wait_for_timeout(200)
    if стр.evaluate(СПИСОК)[-1]["да"]:
        плохо(f"{н} снятая галочка не запомнилась")
    # «Выбрать все / Снять все» в заголовке списка — одним нажатием вместо восьми
    # (Константин, 19.10.2026: «добавь кнопку снять/выбрать все — чтобы
    # менялась. Долго по одной нажимать»). Надпись меняется, список не
    # закрывается, кнопка печати считает заново.
    def все():
        return стр.evaluate("""() => { const б = document.querySelector('#printAllMenu .pa-all');
          return б ? б.textContent.trim() : null; }""")
    if все() != "Выбрать все":
        плохо(f"{н} одна галочка снята, а переключатель «{все()}», ждём «Выбрать все»")
    for ждём_да, ждём_кн, ждём_надпись in ((True, "Печать · 8", "Снять все"), (False, "Печать", "Выбрать все"), (True, "Печать · 8", "Снять все")):
        стр.locator("#printAllMenu .pa-all").click(); стр.wait_for_timeout(200)
        с_ = стр.evaluate(СПИСОК)
        кн_ = стр.evaluate("() => document.querySelector('#printAllMenu .pa-go').textContent.trim()")
        if not стр.evaluate(открыт):
            плохо(f"{н} список закрылся после «{ждём_надпись if not ждём_да else 'Выбрать все'}»"); break
        if any(х["да"] != ждём_да for х in с_) or кн_ != ждём_кн or все() != ждём_надпись:
            плохо(f"{н} переключатель всех: галочки {[х['да'] for х in с_]}, кнопка «{кн_}», надпись «{все()}»")
    # Вид: переключатель в строке заголовка, справа, не прилипает к заголовку и
    # к первой строке; нарисован тише строк, а поле нажатия — не меньше 38 px.
    for т in стр.evaluate("""() => { const н = [], м = document.getElementById('printAllMenu');
        const б = м.querySelector('.pa-all'), h = м.querySelector('.pa-h'), i = м.querySelector('.pa-i');
        const rb = б.getBoundingClientRect(), rh = h.getBoundingClientRect(), ri = i.getBoundingClientRect(), rm = м.getBoundingClientRect();
        if (rb.left - rh.right < 8) н.push('переключатель вплотную к заголовку: ' + Math.round(rb.left - rh.right));
        if (rm.right - rb.right < 10 || rm.right - rb.right > 26) н.push('переключатель от правого края списка: ' + Math.round(rm.right - rb.right));
        if (ri.top - rb.bottom < 4) н.push('переключатель вплотную к первой строке: ' + Math.round(ri.top - rb.bottom));
        if (Math.abs((rb.top + rb.bottom) / 2 - (rh.top + rh.bottom) / 2) > 4) н.push('переключатель не в строке заголовка');
        if (h.getClientRects().length !== 1 || rh.height > parseFloat(getComputedStyle(h).lineHeight || 0) + 14) н.push('заголовок списка перенёсся на две строки: ' + Math.round(rh.height));
        const п = getComputedStyle(б, '::before'), поле = rb.height - parseFloat(п.top) - parseFloat(п.bottom);
        if (поле < 37.5) н.push('поле нажатия переключателя ' + Math.round(поле));
        if (parseFloat(getComputedStyle(б).fontSize) >= parseFloat(getComputedStyle(i).fontSize)) н.push('переключатель не тише строк');
        return н; }"""):
        плохо(f"{н} {т}")
    стр.evaluate("() => { документыКомплекта().forEach(х => _комплектСнято.add(х.к)); отрисоватьКомплект(); }")
    if not стр.evaluate("() => document.querySelector('#printAllMenu .pa-go').disabled"):
        плохо(f"{н} без единой галочки печать не выключена")
    стр.evaluate("() => { _комплектСнято.clear(); отрисоватьКомплект(); }")
    # Ордер помнится в расчёте и в комплект идёт таким, каким его выставили
    # (Константин 18.10.2026: «Приходник заранее выставляем платёж и дату,
    # калькулятор помни. И если выбираем его по кнопке «Печать все», то он
    # печатает то состояние»).
    if полный:
        с_ = стр.evaluate("""async () => { _ордер.договор = 1; _ордер.номер = '555'; _ордер.выдан = true; _ордер.дата = '2026-10-25'; _ордер.отмечены = { 1: [2] };
          const сохр = JSON.stringify(collectState());
          _ордер = { договор: 2, номер: '', выдан: false, дата: '', отмечены: {}, список: false };
          restoreState(JSON.parse(сохр)); await new Promise(р => setTimeout(р, 600));
          const после = JSON.parse(JSON.stringify(_ордер));
          const лист = new DOMParser().parseFromString(await htmlДокументаКомплекта('cash'), 'text/html').body.innerText.replace(/\\s+/g, ' ');
          const без = JSON.parse(сохр); delete без.cashOrder; restoreState(без); await new Promise(р => setTimeout(р, 600));
          const чистый = JSON.parse(JSON.stringify(_ордер));
          restoreState(JSON.parse(сохр)); await new Promise(р => setTimeout(р, 600));
          return { после, лист, чистый }; }""")
        п_ = с_["после"]
        if п_["номер"] != "555" or п_["дата"] != "2026-10-25" or п_["отмечены"].get("1") != [2] or п_["договор"] != 1:
            плохо(f"{н} ордер не вернулся из сохранённого расчёта: {п_}")
        if "кассовому ордеру № 555" not in с_["лист"] or "25.10.2026" not in с_["лист"] or "платёж № 2" not in с_["лист"]:
            плохо(f"{н} комплект печатает не выставленный ордер: {с_['лист'][:300]}")
        if с_["чистый"]["номер"] or с_["чистый"]["выдан"] or с_["чистый"]["отмечены"]:
            плохо(f"{н} расчёт без ордера унаследовал чужой ордер: {с_['чистый']}")
        стр.evaluate("() => { закрытьКомплект(); setPreviewEntity('spec'); }"); стр.wait_for_timeout(300)
        стр.locator("#printAllBtn").click(); стр.wait_for_timeout(300)
    if полный:
        стр.evaluate("() => { window.__комплект = null; window.напечататьВКадре = (h, t) => { window.__комплект = { h, t }; }; }")
        стр.locator("#printAllMenu .pa-go").click(); стр.wait_for_timeout(4000)
        к_ = стр.evaluate("() => window.__комплект")
        if not к_:
            плохо(f"{н} «Печать» комплекта не напечатала"); к.close(); return
        if not к_["t"].startswith("Комплект_"):
            плохо(f"{н} имя файла комплекта: {к_['t']}")
        if re.search(r"counter\(\s*pages?\s*\)", к_["h"]):
            плохо(f"{н} в комплекте остался счётчик страниц")
        if "Версия " not in к_["h"]:
            плохо(f"{н} в комплекте пропала версия договора")
        # Safari на iPhone именованных страниц не знает: у всех листов комплекта
        # поля по умолчанию. Лист шире поля — и Safari уменьшает всё задание
        # (18.10.2026, «в общей печати вот так первый лист мелко»). Комплект
        # открывается без свойства page в ширину A4 за вычетом полей Safari.
        сф = бр.new_page(viewport={"width": 704, "height": 1000}); сф.emulate_media(media="print")
        сф.set_content(re.sub(r"(?<![-\w])page\s*:\s*[^;{}]+;?", "", к_["h"]), wait_until="load"); сф.wait_for_timeout(1200)
        шире = сф.evaluate("""() => { const W = document.documentElement.clientWidth;
          return [...document.body.children].filter(б => б.scrollWidth > W + 1).map(б => б.className + ' ' + б.scrollWidth); }""")
        сф.close()
        if шире:
            плохо(f"{н} в печати Safari лист комплекта шире поля страницы — Safari уменьшит всё задание: {шире}")
        ключи = стр.evaluate("() => документыКомплекта().filter(х => х.можно).map(х => х.к)")
        with tempfile.TemporaryDirectory() as папка:
            отд = {кл: в_пдф(к, стр.evaluate("async (к) => сПалитрой(await htmlДокументаКомплекта(к))", кл), f"{папка}/{кл}.pdf") for кл in ключи}
            всего = в_пдф(к, к_["h"], f"{папка}/комплект.pdf")
            if всего != sum(отд.values()):
                плохо(f"{н} страниц в комплекте {всего}, по отдельности {отд}")
            for т in сравнить(папка, ключи):
                плохо(f"{н} {т}")
    if ош:
        плохо(f"{н} ошибки страницы: {ош[:3]}")
    к.close()


def менеджер(бр, порт):
    к, стр, ош = о.начать(бр, порт, 1440, "manager")
    стр.evaluate("() => setPreviewEntity('spec')"); стр.wait_for_timeout(400)
    стр.locator("#printAllBtn").click(); стр.wait_for_timeout(300)
    с = стр.evaluate(СПИСОК)
    откр = [х["т"] for х in с if not х["выкл"]]
    закр = [х for х in с if х["выкл"]]
    if откр != ["Спецификация · Основной договор", "Спецификация · Договор на отделку", "Вид и план"] or not закр or any(х["да"] or х["почему"] != "После согласования спецификации" for х in закр):
        плохо(f"[менеджер] список до согласования: {с}")
    if стр.evaluate("() => document.querySelector('#printAllMenu .pa-go').textContent.trim()") != "Печать · 3":
        плохо("[менеджер] на кнопке печати не три документа")
    # Переключатель всех не трогает закрытые документы.
    стр.locator("#printAllMenu .pa-all").click(); стр.wait_for_timeout(150)
    стр.locator("#printAllMenu .pa-all").click(); стр.wait_for_timeout(150)
    с = стр.evaluate(СПИСОК)
    if [х["т"] for х in с if х["да"]] != ["Спецификация · Основной договор", "Спецификация · Договор на отделку", "Вид и план"]:
        плохо(f"[менеджер] «Снять все» и «Выбрать все» задели закрытые документы: {с}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, True)
                прогон(бр, порт, 390, False)
                менеджер(бр, порт)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Печатать всё» у спецификации, список документов меню с галочками, снятое помнится, менеджеру договорное закрыто; "
          "комплект — одним документом, страница в страницу с документами по отдельности, без номеров страниц; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
