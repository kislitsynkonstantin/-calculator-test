#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приходный кассовый ордер (КО-1) к договору — в окне печати.

Константин 18.10.2026 о макете mockups/cash-receipt-v1.html: «Макет
приходника супер, делай как в макете».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • пункт «Приходный ордер» в меню документа есть, только когда в расчёте
    отмечено «за наличные»; менеджеру без согласования он закрыт, как
    договоры, и выбрать его нельзя;
  • над листом — панель: договор (если их два), № ордера, дата (сегодня),
    платежи графика выбранного договора с суммами; первый отмечен, итог —
    его сумма;
  • платежи — выпадающим списком (Константин 18.10.2026: «Галочки выбор
    платежей сделай выпадающим списком»): на кнопке «№ 1 — сумма», список
    открывается кнопкой, после отметки остаётся открытым, закрывается
    нажатием мимо и Esc; при открытом списке выбор договора срабатывает с
    первого нажатия; список не выходит за экран;
  • лист: «ПРИХОДНЫЙ КАССОВЫЙ ОРДЕР» и «КВИТАНЦИЯ»; принято от — заказчик;
    основание «Оплата по договору подряда № … от …, платёж № 1»; два
    платежа — номера с суммами; сумма цифрами и прописью; НДС 5 % с
    копейками; дебет 50.01, кредит 62.02, финальный платёж договора на
    отделку — 62.01; кассир — менеджер из реквизитов «Фамилия И. О.»;
  • номер ордера встаёт в ордер и квитанцию, поле при наборе не теряет
    фокус; без отмеченного платежа — подсказка, печать выключена, а
    печать вызовом говорит словами и кадра не создаёт;
  • кнопка «Печать» окна печати печатает ордер (не договор и не
    спецификацию); у листа снято укрупнение текста телефоном
    (text-size-adjust: 100 %);
  • сумма прописью — на шести числах, с родом тысяч;
  • вёрстка на 390 и 1440: панель без прокрутки вбок, поля нажатия списка и
    договора не меньше 44 px, лист ордера в ширину кадра.

    python3 check_cash_receipt.py
"""
import os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_contract_otd as о
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


ЛИСТ = """() => { const ф = document.querySelector('#contractPreviewDoc iframe'); if (!ф) return null; const д = ф.contentDocument;
  const т = д.body.innerText.replace(/\\s+/g, ' ');
  const п = д.querySelector('.paper');
  return { текст: т, ширина: д.documentElement.scrollWidth, кадр: д.documentElement.clientWidth,
    лист: п ? Math.round(п.getBoundingClientRect().right) : 0, полей: д.querySelectorAll('.fv').length }; }"""

ПАНЕЛЬ = """() => { const п = document.querySelector('#contractPreviewDoc .ко-панель'); if (!п || п.hidden) return null;
  return { договоры: [...п.querySelectorAll('[data-ko-dog]')].map(к => к.textContent + (к.getAttribute('aria-pressed') === 'true' ? '*' : '')),
    чипы: [...п.querySelectorAll('.ко-пункт')].map(к => к.textContent.replace(/\\s+/g, ' ').trim() + (к.getAttribute('aria-selected') === 'true' ? '*' : '')),
    кнопка: (п.querySelector('.ко-кнопка') || {}).textContent || '', открыт: !!п.querySelector('.ко-список:not([hidden])'),
    итог: (п.querySelector('.ко-итог b') || {}).textContent || '', дата: (п.querySelector('#koDate') || {}).value || '',
    подсказка: (п.querySelector('.ко-подск') || {}).textContent || '', печать: document.getElementById('printDocBtn').disabled }; }"""

ВЁРСТКА = """() => { const н = [], п = document.querySelector('#contractPreviewDoc .ко-панель');
  if (document.documentElement.scrollWidth > innerWidth + 1) н.push('страница шире экрана');
  if (п) {
    if (п.scrollWidth > п.clientWidth + 1) н.push('панель шире себя на ' + (п.scrollWidth - п.clientWidth));
    const пр = п.getBoundingClientRect();
    п.querySelectorAll('button, input').forEach(э => { const б = э.getBoundingClientRect(); if (!б.width) return;
      if (б.left < пр.left - .5 || б.right > пр.right + .5) н.push((э.id || э.textContent.trim()) + ' за панелью');
      if (э.tagName === 'BUTTON') { const с = getComputedStyle(э, '::before'); const h = б.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
        if (h < 43.5) н.push('поле нажатия «' + э.textContent.trim() + '» по высоте ' + Math.round(h)); } });
    const с = п.querySelector('.ко-список:not([hidden])');
    if (с) { const б = с.getBoundingClientRect(); if (б.left < 0 || б.right > innerWidth + .5) н.push('список платежей за краем экрана');
      с.querySelectorAll('.ко-пункт').forEach(э => { if (э.scrollWidth > э.clientWidth + 1) н.push('пункт списка шире себя'); }); }
  }
  return н; }"""


def прогон(бр, порт, ш, полный):
    н = f"[{ш}]"
    к, стр, ош = о.начать(бр, порт, ш, "admin")
    стр.evaluate("() => { document.getElementById('managerName').value = 'Петров Иван Сергеевич'; document.getElementById('clientName').value = 'Соколов Андрей Викторович'; calc(); }")
    # Без «за наличные» пункта нет.
    видно = стр.evaluate("() => { обновитьМенюДокумента(); return getComputedStyle(document.querySelector('#previewEntityMenu [data-contract=\"cash\"]')).display !== 'none'; }")
    if видно:
        плохо(f"{н} пункт ордера виден без «за наличные»")
    стр.evaluate("() => { const ч = document.getElementById('cashDiscountCheck'); ч.checked = true; ч.dispatchEvent(new Event('change', { bubbles: true })); calc(); }")
    стр.wait_for_timeout(300)
    о.выбрать(стр, "cash")
    if стр.evaluate("() => previewEntity") != "cash":
        плохо(f"{н} пункт ордера не открыл ордер"); к.close(); return
    п = стр.evaluate(ПАНЕЛЬ)
    сегодня = стр.evaluate("() => new Date().toISOString().slice(0, 10)")
    if not п or not п["чипы"] or not п["чипы"][0].endswith("*") or any(ч.endswith("*") for ч in п["чипы"][1:]) or п["дата"] != сегодня or п["печать"]:
        плохо(f"{н} панель ордера: {п}")
    if полный and п and п["договоры"] != ["Основной*", "На отделку"]:
        плохо(f"{н} выбор договора: {п and п['договоры']}")
    л = стр.evaluate(ЛИСТ)
    р = стр.evaluate("() => { const в = getContractVarsKar(1); return { н: в.contractNumKar, д: в.contractDate, п: в.paymentRows }; }")
    п1 = р["п"][0]["amount"]
    сл = стр.evaluate("(н) => суммаПрописью(н)", п1)
    if not л or "ПРИХОДНЫЙ КАССОВЫЙ ОРДЕР" not in л["текст"] or "КВИТАНЦИЯ" not in л["текст"] \
            or f"Оплата по договору подряда № {р['н']} от {р['д'] or '________'}, платёж № 1" not in л["текст"] \
            or "Соколов Андрей Викторович" not in л["текст"] or "Петров И. С." not in л["текст"] \
            or сл not in л["текст"] or "НДС 5 % —" not in л["текст"] or "62.02" not in л["текст"] or "50.01" not in л["текст"]:
        плохо(f"{н} лист ордера: {л and л['текст'][:600]}")
    # НДС с копейками.
    коп = round(п1 * 5 / 105 * 100)
    ндс = f"НДС 5 % — {коп // 100:,} руб. {коп % 100:02d} коп.".replace(",", " ")
    if л and ндс not in л["текст"]:
        и = л["текст"].find("НДС")
        плохо(f"{н} НДС: ждали «{ндс}», на листе «{л['текст'][и:и + 40]!r}»")
    if л and (л["ширина"] > л["кадр"] + 1 or л["лист"] > л["кадр"] + 1):
        плохо(f"{н} лист ордера шире кадра: {л['ширина']} / {л['кадр']}, правый край листа {л['лист']}")
    if п and not re.match(r"^№ 1 — ", п["кнопка"].replace("\u00a0", " ").strip()):
        плохо(f"{н} на кнопке списка платежей: «{п['кнопка']}»")
    стр.locator("#contractPreviewDoc .ко-кнопка").click(); стр.wait_for_timeout(300)
    if not (стр.evaluate(ПАНЕЛЬ) or {}).get("открыт"):
        плохо(f"{н} кнопка не открыла список платежей")
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} панель: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"cash-{ш}.png"))
    стр.keyboard.press("Escape"); стр.wait_for_timeout(200)
    if (стр.evaluate(ПАНЕЛЬ) or {}).get("открыт"):
        плохо(f"{н} Esc не закрыл список платежей")

    # Два платежа.
    if len(р["п"]) > 1:
        стр.locator("#contractPreviewDoc .ко-кнопка").click(); стр.wait_for_timeout(200)
        стр.locator('#contractPreviewDoc [data-ko-p="2"]').click(); стр.wait_for_timeout(500)
        л = стр.evaluate(ЛИСТ); п = стр.evaluate(ПАНЕЛЬ)
        if not п["открыт"]:
            плохо(f"{н} список платежей закрылся после отметки — второй платёж пришлось бы открывать заново")
        if п["кнопка"].replace("\u00a0", " ").strip() != "№ 1, № 2":
            плохо(f"{н} на кнопке при двух платежах: «{п['кнопка']}»")
        стр.mouse.click(5, 5); стр.wait_for_timeout(200)
        if стр.evaluate(ПАНЕЛЬ)["открыт"]:
            плохо(f"{н} нажатие мимо не закрыло список платежей")
        п2 = р["п"][1]["amount"]
        деньги = lambda x: f"{x:,}".replace(",", " ")
        ждали = f"платежи № 1 ({деньги(п1)} руб.) и № 2 ({деньги(п2)} руб.)"
        if ждали not in л["текст"] or стр.evaluate("(н) => суммаПрописью(н)", п1 + п2) not in л["текст"] or деньги(п1 + п2) not in п["итог"].replace("\u00a0", " ").replace("\u202f", " "):
            и = л["текст"].find("платежи")
            плохо(f"{н} два платежа: ждали «{ждали}», итог {п['итог']}, на листе {л['текст'][и:и + 70]!r}")
    # Номер ордера — в ордер и квитанцию, фокус в поле остаётся.
    стр.locator("#koNum").click(); стр.keyboard.type("27"); стр.wait_for_timeout(500)
    ф = стр.evaluate("() => ({ фокус: (document.activeElement || {}).id, значение: document.getElementById('koNum').value })")
    л = стр.evaluate(ЛИСТ)
    if ф["фокус"] != "koNum" or ф["значение"] != "27" or not re.search(r"Дата составления 27 ", л["текст"]) or "кассовому ордеру № 27" not in л["текст"]:
        плохо(f"{н} номер ордера: {ф}, лист «{л['текст'][300:520]}»")
    # Кнопка «Печать» окна печати печатает ордер, а не договор и не спецификацию
    # (Константин, 18.10.2026: «когда нажимаю печать, печатает договор»).
    стр.evaluate("() => { const ф = document.getElementById('contractPrintFrame'); if (ф) ф.remove(); window.__печатьСпец = 0; const был = window.print; window.print = function () { window.__печатьСпец++; }; }")
    стр.locator("#printDocBtn").click(); стр.wait_for_timeout(700)
    пч = стр.evaluate("() => { const ф = document.getElementById('contractPrintFrame'); const т = ф && ф.contentDocument ? ф.contentDocument.body.innerText : ''; return { кадр: !!ф, ордер: т.includes('ПРИХОДНЫЙ КАССОВЫЙ ОРДЕР'), договор: /ДОГОВОР ПОДРЯДА/i.test(т), заголовок: ф && ф.contentDocument ? ф.contentDocument.title : '', спец: window.__печатьСпец }; }")
    if not пч["кадр"] or not пч["ордер"] or пч["договор"] or not пч["заголовок"].startswith("Приходный_ордер_") or пч["спец"]:
        плохо(f"{н} «Печать» в окне печати ордера: {пч}")
    # Лист не укрупняется телефоном: Safari увеличивает мелкий текст широкого
    # блока, и надписи вылезают из клеток (18.10.2026, «Приходник кривой»).
    # Chromium так не делает, поэтому проба держит само правило.
    тса = стр.evaluate("() => { const ф = document.querySelector('#contractPreviewDoc iframe'); const с = getComputedStyle(ф.contentDocument.documentElement); return с.webkitTextSizeAdjust || с.textSizeAdjust || ''; }")
    if тса != "100%":
        плохо(f"{н} у листа ордера не снято укрупнение текста телефоном: «{тса}»")
    # Ни одного платежа.
    стр.evaluate("() => { _ордер.отмечены[_ордер.договор] = []; refreshContractPreview(); }"); стр.wait_for_timeout(400)
    п = стр.evaluate(ПАНЕЛЬ)
    if not п or "Выберите хотя бы один платёж" not in п["подсказка"] or not п["печать"]:
        плохо(f"{н} без платежей: {п}")
    стр.evaluate("() => { window.__тосты = []; const был = window.showToast; window.showToast = function (т) { window.__тосты.push(String(т)); return был.apply(this, arguments); }; document.getElementById('contractPrintFrame') && document.getElementById('contractPrintFrame').remove(); printContractKar(); }")
    з = стр.evaluate("() => ({ тосты: window.__тосты, кадр: !!document.getElementById('contractPrintFrame') })")
    if з["кадр"] or not any("хотя бы один платёж" in т for т in з["тосты"]):
        плохо(f"{н} печать без платежей: {з}")
    # Договор на отделку: финальный платёж — 62.01.
    if полный:
        стр.locator("#contractPreviewDoc .ко-кнопка").click(); стр.wait_for_timeout(200)
        стр.locator('#contractPreviewDoc [data-ko-dog="2"]').click(); стр.wait_for_timeout(500)
        if стр.evaluate("() => _ордер.договор") != 2:
            плохо(f"{н} при открытом списке платежей договор не выбрался с первого нажатия")
        р2 = стр.evaluate("() => getContractVarsKar(2).paymentRows")
        if len(р2) > 1:
            последний = р2[-1]["no"]
            стр.evaluate("(н) => { _ордер.отмечены[2] = [н]; refreshContractPreview(); }", последний); стр.wait_for_timeout(400)
            л = стр.evaluate(ЛИСТ)
            if "62.01" not in л["текст"] or "62.02" in л["текст"]:
                плохо(f"{н} финальный платёж отделки не на 62.01")
            стр.evaluate("() => { _ордер.отмечены[2] = [1]; refreshContractPreview(); }"); стр.wait_for_timeout(400)
            if "62.02" not in стр.evaluate(ЛИСТ)["текст"]:
                плохо(f"{н} аванс отделки не на 62.02")
        for т in стр.evaluate(ВЁРСТКА):
            плохо(f"{н} панель отделки: {т}")
        # Сумма прописью.
        for число, ждали in [(1, "Один"), (21000, "Двадцать одна тысяча"), (360000, "Триста шестьдесят тысяч"), (1001, "Одна тысяча один"),
                             (2670560, "Два миллиона шестьсот семьдесят тысяч пятьсот шестьдесят"), (112, "Сто двенадцать")]:
            вышло = стр.evaluate("(н) => суммаПрописью(н)", число)
            if вышло != ждали:
                плохо(f"сумма прописью {число}: «{вышло}», ждали «{ждали}»")
    if ош:
        плохо(f"{н} ошибки страницы: {ош[:3]}")
    к.close()


def менеджер(бр, порт):
    к, стр, ош = о.начать(бр, порт, 1440, "manager")
    стр.evaluate("() => { const ч = document.getElementById('cashDiscountCheck'); ч.checked = true; calc(); обновитьМенюДокумента(); }")
    с = стр.evaluate("""() => { const п = document.querySelector('#previewEntityMenu [data-contract="cash"]');
      выбратьОрдер(); return { видно: getComputedStyle(п).display !== 'none', закрыт: п.classList.contains('ent-locked'), документ: previewEntity }; }""")
    if not с["видно"] or not с["закрыт"] or с["документ"] == "cash":
        плохо(f"менеджер без согласования: {с}")
    к.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
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
    print("Чисто: пункт ордера только «за наличные» и закрыт до согласования, панель договора, номера, даты и платежей, "
          "лист КО-1 с основанием, суммой прописью, НДС, счетами и подписями, номер в ордере и квитанции, без платежа не печатается, "
          "вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
