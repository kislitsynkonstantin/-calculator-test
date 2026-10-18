#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Координаты участка в «Данных для договора» — необязательное поле.

Константин 18.10.2026: «координаты участка добавь да поле, но сделай его
необязательным. Если заполнят, то отлично. Потом едет технадзор на осмотр,
берёт точную точку участка».

Проба держит, на заглушке базы:
  • в окне «Данные для договора», в группе «Земельный участок», под
    кадастровым номером — поле «Координаты участка», без слова «необязательно»;
  • вписанные координаты стоят в договоре в скобках за адресом участка;
  • поле не входит в счёт «Заполнено N из M» и в список недостающего:
    все обязательные заполнены, координат нет — «Заполнено полностью»;
  • координаты сохраняются с расчётом и возвращаются при его открытии;
  • вписанные координаты встают в шапку ТЗ, пустые — строки нет;
  • клавиатура телефона обычная, с точкой и пробелом, а не цифровая;
  • 390 и 1440 px: поле внутри окна, подпись не обрезана.
Данные учебные.

    python3 check_plot_coords.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_approval_report as з
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
КООРД = "55.751244, 37.618423"


def плохо(т):
    НАХОДКИ.append(т)


ЗАПОЛНИТЬ = """() => { const з = { cdPhone: '+7 900 000 00 00', cdEmail: 'uchebny@example.ru', cdRegAddress: 'г. Пробный, ул. Учебная, 1',
  cdBirthDate: '1990-01-01', cdPassport: '0000 000000', cdPassportDate: '2010-01-01', cdPassportIssuer: 'Учебным отделом',
  cdPassportCode: '000-000', cdPlotAddress: 'Пробная область, участок 1', cdCadastral: '00:00:0000000:00',
  cdContractNumKar: '00000001-КАР', cdContractNumO: '00000001-ОТД' };
  Object.entries(з).forEach(([ид, в]) => { const э = document.getElementById(ид); if (э) { э.value = в; э.dispatchEvent(new Event('input', { bubbles: true })); } });
  updateContractDataStatus(); }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = з.начать(бр, порт, ш, в)
    стр.evaluate("() => openContractDataModal()"); стр.wait_for_timeout(500)
    поле = стр.evaluate("""() => { const э = document.getElementById('cdPlotCoords'); if (!э) return null;
      const п = э.closest('.field'), подпись = п && п.querySelector('label'), кад = document.getElementById('cdCadastral').closest('.field');
      const окно = э.closest('div[style*="overflow-y:auto"]').getBoundingClientRect(), r = э.getBoundingClientRect();
      return { подпись: подпись ? подпись.textContent.trim() : '', послеКадастра: кад.nextElementSibling === п,
        внутри: r.left >= окно.left - 0.5 && r.right <= окно.right + 0.5,
        обрезана: подпись ? подпись.scrollWidth > подпись.clientWidth + 1 : false }; }""")
    if not поле:
        плохо(f"{н} в «Данных для договора» нет поля координат"); стр.close(); return
    # «(необязательно)» в подписи нет: Константин 18.10.2026 — «убери слово
    # „необязательно“. Поле да, необязательное».
    if поле["подпись"] != "Координаты участка":
        плохо(f"{н} подпись поля: {поле['подпись']!r}")
    if not поле["послеКадастра"]:
        плохо(f"{н} поле координат стоит не под кадастровым номером")
    if not поле["внутри"] or поле["обрезана"]:
        плохо(f"{н} поле координат за краем окна или подпись обрезана: {поле}")
    стр.locator("#cdPlotCoords").scroll_into_view_if_needed()
    стр.screenshot(path=str(СНИМКИ / f"plot-coords-{ш}.png"))

    стр.evaluate(ЗАПОЛНИТЬ); стр.wait_for_timeout(300)
    с = стр.evaluate("() => { const s = getContractDataStatus(); return { filled: s.filled, total: s.total, нет: s.missing.kar.concat(s.missing.o), текст: document.getElementById('contractDataStatusText').textContent }; }")
    if с["filled"] != с["total"] or с["нет"] or с["текст"] != "Заполнено полностью" or с["total"] != 12:
        плохо(f"{н} без координат обязательные заполнены, а счёт не полный или считает координаты: {с}")
    ДОГОВОР = """() => { const д = document.createElement('div'); д.innerHTML = buildContractHtmlKar(getContractVarsKar(1));
      const к = [...д.querySelectorAll('.o-cap')].find(э => э.textContent.trim() === 'Адрес участка');
      return к ? к.nextElementSibling.textContent.trim() : null; }"""
    адр0 = стр.evaluate(ДОГОВОР)
    if адр0 != "Пробная область, участок 1":
        плохо(f"{н} без координат адрес участка в договоре не тот: {адр0!r}")
    тз0 = стр.evaluate("() => данныеТЗ(null).шапка.map(с => с.к)")
    if "Координаты участка" in тз0:
        плохо(f"{н} пустые координаты дали строку в шапке ТЗ: {тз0}")

    # Клавиатура телефона — обычная, с точкой и пробелом: цифровая
    # (decimal, numeric, tel) на айфоне ни того, ни другого не даёт.
    вид = стр.evaluate("() => { const э = document.getElementById('cdPlotCoords'); return [э.type, э.inputMode]; }")
    if вид[0] != "text" or вид[1] in ("decimal", "numeric", "tel"):
        плохо(f"{н} у поля координат цифровая клавиатура — точку и пробел не поставить: {вид}")
    стр.fill("#cdPlotCoords", ""); стр.type("#cdPlotCoords", КООРД, delay=5); стр.wait_for_timeout(300)
    if стр.evaluate("() => document.getElementById('cdPlotCoords').value") != КООРД:
        плохо(f"{н} набранные с клавиатуры координаты изменились в поле")
    стр.fill("#cdPlotCoords", КООРД); стр.wait_for_timeout(300)
    с2 = стр.evaluate("() => getContractDataStatus().total")
    if с2 != 12:
        плохо(f"{н} координаты вошли в счёт обязательных: из {с2}")
    тз = стр.evaluate("() => данныеТЗ(null).шапка.map(с => [с.к, с.з])")
    if ["Координаты участка", КООРД] not in тз:
        плохо(f"{н} вписанные координаты не встали в шапку ТЗ: {тз}")
    # В договоре координаты — в скобках за адресом; в ТЗ адрес остаётся без
    # них, там у координат своя строка.
    адр = стр.evaluate(ДОГОВОР)
    if адр != f"Пробная область, участок 1 ({КООРД})":
        плохо(f"{н} в договоре нет координат в скобках за адресом: {адр!r}")
    if ["Адрес участка", "Пробная область, участок 1"] not in тз:
        плохо(f"{н} в шапке ТЗ адрес участка изменился: {тз}")
    сост = стр.evaluate("() => (collectState().contractData || {}).cdPlotCoords")
    if сост != КООРД:
        плохо(f"{н} координаты не сохраняются с расчётом: {сост!r}")
    стр.evaluate("(к) => { const s = collectState(); document.getElementById('cdPlotCoords').value = ''; restoreState(s); }", КООРД)
    стр.wait_for_timeout(500)
    if стр.evaluate("() => document.getElementById('cdPlotCoords').value") != КООРД:
        плохо(f"{н} открытый заново расчёт потерял координаты")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                for ш, в in ((1440, 900), (390, 844)):
                    прогон(бр, порт, ш, в)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: координаты участка — необязательное текстовое поле под кадастровым номером, в счёт «Заполнено» не входят, "
          "в договоре стоят в скобках за адресом, сохраняются с расчётом и встают в шапку ТЗ, когда вписаны; 390 и 1440.")


if __name__ == "__main__":
    главная()
