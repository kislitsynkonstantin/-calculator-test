#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Парная: материал вагонки и полков, подсветка без счётчика, цены каталога.

Константин 28.10.2026, пересылкой из чата: «Тут, рядом с печью, добавить
материал вагонки и материал полков… Если цен не хватает ему для расчётов,
пусть в таблице сделаем пометку», «И чтобы внизу в парной сразу выбирался
материал», «Тут уровни убрать», «Тут цены надо поправить. Видимо в таблице».

Проба держит:
  • в карточке «Параметры парной» под печью — поля «Вагонка» и «Полки» со
    списками в присланном порядке; сибирский кедр и термоабаш — с пометкой
    «нет цены в таблице» и не выбираются;
  • доплаты к осине — формулами листа «Справочник» книги с её округлениями;
    проба считает их сама, десятичной арифметикой, а не берёт у калькулятора;
  • выбор в поле сразу отмечает строку раздела «Парное отделение» с именем
    материала, «Осина» её снимает; нажатие по строке снимает и возвращает
    её с тем же материалом; «Выбрать» у строки раскрывает поле;
  • пресет прежней сборки (ольха без поля материала) открывается с ольхой,
    материал уходит в снимок пресета;
  • подсветка полков без счётчика: 2 уровня, со спинками — 3;
  • спинки, парящий полок, масло, настил и «звёздное небо» — по каталогу
    каркаса и идут за ним; без каталога — его цены на 28.10.2026;
  • вёрстка на 390 и 1440 px: список поля в окне, без прокрутки вбок.

    python3 check_steam_materials.py
"""
import pathlib, sys
from decimal import Decimal as Д, ROUND_HALF_UP

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_steam_tab as п
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВЫХОД = pathlib.Path(__file__).parent / 'кадры_материалы'


def плохо(т):
    НАХОДКИ.append(т)


# Лист «Справочник» книги «Калькулятор парной» v2.4: обшивка, полок (₽/м²),
# раскрой, монтаж (₽/м²). K = 0,614 / (1 − 0,35), как множитель калькулятора.
СПРАВОЧНИК = {'osina': (1950, 2450, '1.08', 2600), 'lipa': (4300, 4600, '1.08', 2910), 'olha': (4750, 5100, '1.08', 4590),
              'termolipa': (5800, 6200, '1.1', 4090), 'termoolha': (6500, 7000, '1.1', 4710),
              'abash': (11000, 11800, '1.1', 4840), 'kedr-kan': (28400, 29500, '1.1', 5080)}
K = Д('0.944615')


def окр(x, n=0):
    return x.quantize(Д(1).scaleb(-n), rounding=ROUND_HALF_UP)


def обшивка(ид, s):
    c, _, e, f = СПРАВОЧНИК[ид]
    return окр(окр(s * Д(e), 1) * c * K) + окр(s * f * K)


def полки(ид, s):
    _, d, e, _ = СПРАВОЧНИК[ид]
    return окр(окр(s * Д(e), 2) * d * K)


ВАГОНКА = ['Осина', 'Липа', 'Ольха', 'Термолипа', 'Термоольха', 'Сибирский кедр', 'Канадский кедр']
ПОЛКИ = ['Осина', 'Липа', 'Термолипа', 'Ольха', 'Термоольха', 'Абаш', 'Термоабаш']
СПИСОК = """ид => [...document.querySelectorAll('#' + ид + ' .custom-select-option')].map(о => ({
  ид: о.dataset.mat, имя: о.querySelector('.cso-name').firstChild.textContent.trim(),
  мета: о.querySelector('.cso-meta').textContent.replace(/\\u00a0/g, ' ').trim(),
  выкл: о.classList.contains('cso-off'), выбран: о.classList.contains('selected') }))"""
ИТОГ = "() => Number(document.getElementById('totalDisplay').textContent.replace(/\\D/g, ''))"
СТРОКА = """к => ({ вкл: ПАР.вкл.has(к), имя: document.getElementById('name_par_' + к).textContent,
  цена: Number(document.getElementById('optprice_par_' + к).textContent.replace(/\\D/g, '')),
  отм: document.getElementById('chk_par_' + к).checked })"""


def расчёт(бр, порт):
    стр, ош = п.открыть(бр, порт, 1440)
    п.в_парную(стр, образец=False)
    г = стр.evaluate("() => { const г = парГеом(); return [г.отд, ПАР.polki]; }")
    s, сп = Д(str(г[0])), Д(str(г[1]))
    if (s, сп) != (Д('29'), Д('3.75')):
        плохо(f"начало парной: стены и потолок {s} м², полки {сп} м² — ждали 29 и 3,75")

    # Поля под печью, списки в присланном порядке.
    порядок = стр.evaluate("""() => [...document.querySelectorAll('#steamRoomCard > .field > label')].map(л => л.textContent.trim())""")
    if порядок[-3:] != ['Печь', 'Вагонка', 'Полки']:
        плохо(f"поля карточки «Параметры парной»: {порядок} — ждали «Вагонка» и «Полки» сразу под «Печь»")
    # Раскрытый список лежит поверх поля ниже — закрывается повторным нажатием.
    стр.click('#steamLiningTrigger')
    ваг = стр.evaluate(СПИСОК, 'steamLiningDropdown')
    стр.click('#steamLiningTrigger')
    стр.click('#steamBenchTrigger')
    пол = стр.evaluate(СПИСОК, 'steamBenchDropdown')
    стр.click('#steamBenchTrigger')
    if [о['имя'] for о in ваг] != ВАГОНКА or [о['имя'] for о in пол] != ПОЛКИ:
        плохо(f"списки материалов: вагонка {[о['имя'] for о in ваг]}, полки {[о['имя'] for о in пол]}")
    выкл = sorted(о['ид'] for о in ваг + пол if о['выкл'])
    if выкл != ['kedr-sib', 'termoabash'] or any(о['мета'] != 'нет цены в таблице' for о in ваг + пол if о['выкл']):
        плохо(f"без цены в «Справочнике»: {выкл} — ждали сибирский кедр и термоабаш с пометкой «нет цены в таблице»")

    # Доплаты к осине — формулами книги.
    for список, ид_дд, считать in (('ваг', 'steamLiningDropdown', lambda и: обшивка(и, s) - обшивка('osina', s)),
                                    ('пол', 'steamBenchDropdown', lambda и: полки(и, сп) - полки('osina', сп))):
        for о in (ваг if список == 'ваг' else пол):
            if о['выкл'] or о['ид'] == 'osina':
                continue
            ждём = int(считать(о['ид']))
            есть = стр.evaluate("([с, и, s]) => парДоплатаМатериала(с, и, s)", [список, о['ид'], float(s) if список == 'ваг' else float(сп)])
            в_списке = int(''.join(ч for ч in о['мета'].split('+')[-1] if ч.isdigit()) or 0)
            if есть != ждём or в_списке != ждём:
                плохо(f"доплата за {о['имя']} ({'вагонка' if список == 'ваг' else 'полки'}): калькулятор {есть}, в списке {в_списке}, по книге {ждём}")

    # Выбор в поле отмечает строку; «Осина» снимает.
    до = стр.evaluate(ИТОГ)
    стр.click('#steamLiningTrigger'); стр.click('#steamLiningDropdown [data-mat="lipa"]')
    р = стр.evaluate(СТРОКА, 'olha')
    ярл = стр.evaluate("() => document.getElementById('steamLiningLabel').textContent")
    ждём = int(обшивка('lipa', s) - обшивка('osina', s))
    if р != {'вкл': True, 'имя': 'Вагонка из липы (сорт Экстра) вместо осины', 'цена': ждём, 'отм': True} or ярл != 'Липа, сорт Экстра' \
            or стр.evaluate(ИТОГ) != до + ждём:
        плохо(f"вагонка из липы в поле: строка {р}, поле «{ярл}», итог {стр.evaluate(ИТОГ)} при {до} — ждали +{ждём} ₽")
    стр.click('#steamLiningTrigger'); стр.click('#steamLiningDropdown [data-mat="kedr-sib"]', force=True)
    if стр.evaluate("() => ПАР.матВагонки") != 'lipa' or not стр.evaluate("() => document.getElementById('steamLiningWrap').classList.contains('open')"):
        плохо("нажатие по сибирскому кедру без цены что-то выбрало или закрыло список")
    стр.click('#steamLiningDropdown [data-mat="osina"]')
    р = стр.evaluate(СТРОКА, 'olha')
    if р['вкл'] or р['отм'] or стр.evaluate(ИТОГ) != до or стр.evaluate("() => document.getElementById('steamLiningLabel').textContent") != 'Осина, сорт АБ':
        плохо(f"«Осина» в поле: строка {р}, итог {стр.evaluate(ИТОГ)} при {до}")
    # Строка возвращается с тем же материалом, снимается — поле снова «Осина».
    стр.click('#lbl_par_olha .opt-name')
    if not стр.evaluate("() => ПАР.вкл.has('olha')") or стр.evaluate("() => document.getElementById('steamLiningLabel').textContent") != 'Липа, сорт Экстра':
        плохо("нажатие по строке вагонки не вернуло её с липой")
    стр.click('#lbl_par_olha .opt-name')
    if стр.evaluate("() => ПАР.вкл.has('olha')") or стр.evaluate("() => document.getElementById('steamLiningLabel').textContent") != 'Осина, сорт АБ':
        плохо("снятая строка вагонки не вернула поле к осине")
    # «Выбрать» у строки полков раскрывает поле в карточке.
    стр.click('#lbl_par_polkiOlha .par-pick')
    стр.wait_for_timeout(500)
    if not стр.evaluate("() => document.getElementById('steamBenchWrap').classList.contains('open')"):
        плохо("«Выбрать» у строки полков не раскрыло поле «Полки»")
    стр.click('#steamBenchDropdown [data-mat="abash"]')
    р = стр.evaluate(СТРОКА, 'polkiOlha')
    ждём = int(полки('abash', сп) - полки('osina', сп))
    if р != {'вкл': True, 'имя': 'Полки из абаша вместо осины', 'цена': ждём, 'отм': True} \
            or стр.evaluate("() => document.getElementById('steamBenchLabel').textContent") != 'Абаш африканский':
        плохо(f"полки из абаша: строка {р} — ждали доплату {ждём} ₽")

    # Снимок пресета несёт материал; пресет прежней сборки — с ольхой.
    сн = стр.evaluate("() => { const с = парнаяСнимок(); return [с.матВагонки, с.матПолков, с.вкл.includes('polkiOlha')]; }")
    if сн != ['lipa', 'abash', True]:
        плохо(f"снимок пресета: {сн} — ждали материалы вагонки и полков в нём")
    стар = стр.evaluate("""() => { парнаяРазложить({ L: 3, W: 2, H: 2.3, вкл: ['olha', 'polkiOlha'], podsv: 3 }); calc();
      return [ПАР.матВагонки, ПАР.матПолков, document.getElementById('name_par_olha').textContent,
              document.getElementById('steamBenchLabel').textContent, 'podsv' in ПАР]; }""")
    if стар != ['olha', 'olha', 'Вагонка из ольхи (сорт Экстра) вместо осины', 'Ольха, сорт Экстра', False]:
        плохо(f"пресет прежней сборки: {стар} — ждали ольху на стенах и полках и без счётчика подсветки")

    # Подсветка без счётчика; цены каталога.
    стр.evaluate("() => { парнаяРазложить({}); ПАР.вкл.add('podsv'); calc(); }")
    в = стр.evaluate("() => [!!document.getElementById('qtyval_par_podsv'), Number(document.getElementById('optprice_par_podsv').textContent.replace(/\\D/g, ''))]")
    стр.evaluate("() => { ПАР.вкл.add('spinki'); calc(); }")
    в += [стр.evaluate("() => Number(document.getElementById('optprice_par_podsv').textContent.replace(/\\D/g, ''))")]
    if в != [False, 100365, 150548]:
        плохо(f"подсветка полков: счётчик {в[0]}, цена {в[1]} и со спинками {в[2]} — ждали без счётчика, 100 365 и 150 548 ₽")
    ЦЕНЫ = "() => ['spinki', 'parya', 'maslo', 'nastil', 'zvezd'].map(к => Number(document.getElementById('optprice_par_' + к).textContent.replace(/\\D/g, '')))"
    if стр.evaluate(ЦЕНЫ) != [15000, 25600, 24000, 17600, 56250]:
        плохо(f"цены по каталогу каркаса без каталога: {стр.evaluate(ЦЕНЫ)} — ждали 15 000 / 25 600 / 24 000 / 17 600 / 56 250")
    стр.evaluate("() => { FRAME_OPTIONS.forEach(о => { if (о.id === 's17') о.price = 27000; if (о.id === 's31') о.price = 25000; }); calc(); }")
    if стр.evaluate(ЦЕНЫ)[1:3] != [27000, 25000]:
        плохо(f"парящий полок и масло не идут за каталогом каркаса: {стр.evaluate(ЦЕНЫ)}")
    if ош:
        плохо(f"ошибки страницы: {ош[:3]}")
    стр.close()


def вёрстка(бр, порт):
    ВЫХОД.mkdir(exist_ok=True)
    for ш in (390, 1440):
        for ночь in (False, True):
            стр, ош = п.открыть(бр, порт, ш, ночь=ночь)
            п.в_парную(стр, образец=False)
            for ид in ('steamLiningTrigger', 'steamBenchTrigger'):
                стр.click('#' + ид)
                стр.wait_for_timeout(300)
                в = стр.evaluate("""ид => { const дд = document.getElementById(ид.replace('Trigger', 'Dropdown'));
                  const р = дд.getBoundingClientRect(), оп = [...дд.querySelectorAll('.custom-select-option')];
                  return { видно: getComputedStyle(дд).display !== 'none' && р.height > 0, лево: р.left, право: р.right, ш: innerWidth,
                           вбок: document.documentElement.scrollWidth - innerWidth,
                           низ: Math.min(...оп.map(о => о.getBoundingClientRect().height)) }; }""", ид)
                if not в['видно'] or в['лево'] < 0 or в['право'] > в['ш'] or в['вбок'] > 0 or в['низ'] < 40:
                    плохо(f"{ш} px{' ночью' if ночь else ''}, список {ид}: {в} — ждали в окне, без прокрутки вбок, пункты не ниже 40 px")
                стр.locator('#' + ид.replace('Trigger', 'Wrap')).scroll_into_view_if_needed()
                стр.screenshot(path=str(ВЫХОД / f"{ид}-{ш}{'-ночь' if ночь else ''}.png"))
                стр.mouse.click(5, 5)
            if ош:
                плохо(f"{ш} px: ошибки страницы {ош[:3]}")
            стр.close()


def main():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром())
            расчёт(бр, порт)
            вёрстка(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: у парной под печью — поля «Вагонка» и «Полки» в присланном порядке, сибирский кедр и термоабаш "
          "помечены «нет цены в таблице» и не выбираются; доплаты к осине — по формулам «Справочника» книги; выбор "
          "в поле сразу отмечает строку раздела с именем материала, «Осина» снимает, строка возвращается с тем же "
          "материалом, «Выбрать» раскрывает поле; пресет прежней сборки — с ольхой, материал в снимке; подсветка без "
          "счётчика — 2 уровня, со спинками 3; спинки, парящий полок, масло, настил и «звёздное небо» — по каталогу "
          "каркаса; списки в окне на 390 и 1440 px, днём и ночью.")


if __name__ == '__main__':
    main()
