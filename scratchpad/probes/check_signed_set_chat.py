#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подписанный комплект — PDF в чат пресета после «Подписан».

Константин 21.10.2026, на вопрос «класть ли при подписании PDF договоров,
спецификации и правил в чат»: «Ты читаешь мои мысли… Делай». Заморозка держит
цены и опции подписанного расчёта, но не тексты договоров и правил: они живут
в коде и меняются с версиями. PDF в чате — тот текст, что подписан.

Проба держит, на заглушке базы и с библиотеками PDF из пакетов npm:
  • после «Подписан» в чат приходят заключение, ТЗ и следом одно сообщение с
    PDF: спецификация (по договорам), основной договор, договор на отделку и
    правила эксплуатации — каждый своим файлом с кодом пресета в имени;
  • сообщение называет документы и говорит, что тексты — на день подписания;
  • каждый PDF — A4, страниц у договора больше двух, ни одна страница не пуста;
  • лист не режет строку: у каждого документа ноль разрезов «вслепую» — там,
    где между строками и блоками не нашлось места (проба оборачивает
    pdfДокумента и читает счётчик с готового файла);
  • ошибок страницы нет.

    python3 check_signed_set_chat.py
"""
import base64, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_approval as па
import check_approval_report as з
import check_tz_chat as тз
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЖДЁМ = ["Спецификация_Основной_договор_", "Спецификация_Договор_на_отделку_", "Основной_договор_", "Договор_на_отделку_", "Правила_эксплуатации_"]


def плохо(т):
    НАХОДКИ.append(т)


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = з.начать(бр, порт, ш, в)
    стр.on("console", lambda с: ошибки.append(с.text) if "[комплект в чат]" in с.text else None)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(па.ДАННЫЕ, код)
    стр.evaluate(з.ХРАНИЛИЩЕ)
    стр.evaluate("""() => { window.__вслепую = []; const был = window.pdfДокумента;
      window.pdfДокумента = async h => { const б = await был(h); window.__вслепую.push(б.вслепую); return б; }; }""")
    стр.evaluate("""() => { window.__проверкаБыла = проверкаПоЧекЛисту;
      window.проверкаПоЧекЛисту = function () { const п = window.__проверкаБыла.apply(this, arguments); п.замечания = п.замечания.filter(з => !з.стоп); return п; }; }""")
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-send"); стр.wait_for_timeout(600)
    стр.evaluate("() => { window.__ТАБЛИЦЫ.preset_approvals.forEach(с => { с.price_by = 'u-ред'; с.price_name = 'Ольга Проверкина'; с.price_at = new Date().toISOString(); с.price_print = с.sent_print; }); _согласование.когда = 0; }")
    па.роль(стр, "specialist")
    стр.evaluate("() => решитьСогласование('approved', 'check')"); стр.wait_for_timeout(1500)
    па.роль(стр, "manager")
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-sign")
    if not тз.ждатьPdf(стр, "Правила_эксплуатации_", 240):
        плохо(f"{н} после «Подписан» подписанный комплект не пришёл в чат: {стр.evaluate('() => window.__PDF.map(п => п.имя)')}, {ошибки[:3]}")
        стр.close(); return
    стр.wait_for_timeout(1500)
    имена = стр.evaluate("() => window.__PDF.map(п => п.имя)")
    for ж in ЖДЁМ:
        if not any(и.startswith(ж) and код in и for и in имена):
            плохо(f"{н} в чате нет PDF «{ж}…» с кодом пресета: {имена}")
    if not any(и.startswith(f"Заключение_{код}_") for и in имена) or not any(и.startswith(f"ТЗ_{код}_") for и in имена):
        плохо(f"{н} заключение или ТЗ не пришли вместе с комплектом: {имена}")
    с = стр.evaluate("""() => { const с = window.__ТАБЛИЦЫ.preset_messages.filter(х => (х.attachments || []).some(в => /^Правила_эксплуатации_/.test(в.name || ''))).pop();
      return с ? { текст: с.body, файлов: с.attachments.length } : null; }""")
    if not с or с["файлов"] != len(ЖДЁМ) or "Подписанный комплект" not in с["текст"] or "в день подписания" not in с["текст"]:
        плохо(f"{н} сообщение с комплектом: {с}")
    from PIL import Image
    for ж in ЖДЁМ:
        п = next((п for п in стр.evaluate("() => window.__PDF") if п["имя"].startswith(ж)), None)
        if not п:
            continue
        картинки, инфо = з.страницыPdf(base64.b64decode(п["данные"]), f"{н} {ж}")
        if "595.28 x 841.89" not in инфо and "595 x 842" not in инфо:
            плохо(f"{н} {ж}: не A4 — {инфо!r}")
        if ж in ("Основной_договор_", "Договор_на_отделку_") and len(картинки) < 3:
            плохо(f"{н} {ж}: всего {len(картинки)} стр. — договор не мог так ужаться")
        for i, к in enumerate(картинки):
            лист = Image.open(к).convert("L")
            ш_, в_ = лист.size
            if лист.getextrema()[0] > 200:
                плохо(f"{н} {ж}: страница {i + 1} пустая")
    # После подписи карточку проекта перерисовывают без пересчёта — «Цена за
    # м²» не должна остаться заглушкой «… ₽/м²» (21.10.2026, снимок ленты).
    м2 = стр.evaluate("() => { const ч = document.getElementById('pricePerM2Chip'); return ч ? ч.innerText.replace(/\\s+/g, ' ').trim() : null; }")
    if м2 is not None and ("…" in м2 or "Цена за м" not in м2):
        плохо(f"{н} после подписи «Цена за м²» осталась заглушкой: «{м2}»")
    # Вес: подписанный комплект не должен раздувать хранилище чата.
    for п_ in стр.evaluate("() => window.__PDF.map(п => [п.имя, п.данные.length])"):
        if any(п_[0].startswith(ж) for ж in ЖДЁМ) and п_[1] * 3 / 4 > 2.5e6:
            плохо(f"{н} {п_[0]} весит {п_[1] * 3 / 4 / 1e6:.1f} МБ — больше 2,5")
    # Кадр ленты с комплектом — для статьи о выпуске и для глаза.
    стр.evaluate("() => { if (!document.getElementById('presetChipCard').classList.contains('show')) document.querySelector('#presetChip .pc-body').click(); }")
    стр.wait_for_timeout(400)
    стр.evaluate("() => { const т = document.getElementById('pcTab-m'); if (т) т.click(); }"); стр.wait_for_timeout(1200)
    стр.evaluate("() => { const л = document.querySelector('#presetChipCard .pc-chl'); if (л) л.scrollTop = л.scrollHeight; }"); стр.wait_for_timeout(500)
    стр.screenshot(path=str(з.СНИМКИ / f"signed-set-chat-{ш}.png"))
    сл = стр.evaluate("() => window.__вслепую")
    if len(сл) != len(ЖДЁМ) or any(сл):
        плохо(f"{н} разрезы листа вслепую по документам: {сл} — где-то лист режет строку")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    if not з.JSPDF.exists() or not з.H2C.exists():
        print("нет библиотек PDF"); sys.exit(2)
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: после «Подписан» в чат приходят заключение, ТЗ и одним сообщением PDF спецификации по договорам, обоих договоров "
          "и правил с кодом пресета в имени; сообщение говорит, что тексты — на день подписания; каждый PDF — A4, без пустых "
          "страниц, лист не режет строку.")


if __name__ == "__main__":
    главная()
