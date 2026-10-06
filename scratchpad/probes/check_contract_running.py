#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Колонтитулы основного договора: версия, «Страница N из M», подписи на каждой странице.

Константин 06.10.2026, снимками прежнего договора из Word: «чтобы не путаться
в версиях, вверху слева на договоре добавим версию. Для договора по каркасу
поставь пока 2.1»; «колонтитулы на каждом листе версия / лист, листов,
подписи… сделать также, чтобы ставилось на каждый лист. Пока только на
договор основной».

Проба печатает договор в PDF Chromium с настоящими шрифтами и держит:
  • на каждой странице основного договора — «Версия 2.1» и «Страница N из M»
    в верхнем поле, «Подрядчик … Баранов Г. Н.» и «Заказчик … <фамилия>» в
    нижнем; номера страниц идут подряд и M — число страниц;
  • фамилия с инициалами не растянута выключкой: «Баранов Г. Н.» одной
    строкой текста, а не тремя кусками по полю;
  • подписи не налезают на текст договора: от нижней строки текста до
    подписей — не меньше 3 мм на любой странице;
  • на первой странице версия одна: строка над логотипом в Chromium на
    печати снята (её заменяет верхнее поле), а без признака Chromium —
    так печатает Safari, который поля страницы не слушает, — она видна;
  • на экране строка версии стоит над логотипом;
  • договор на отделку, правила и согласие — без версии и без подписей в
    поле, номер страницы у них по-прежнему внизу справа;
  • в Word у основного договора то же: в верхнем колонтитуле версия и поля
    номера страницы, в нижнем — подписи сторон.

    python3 check_contract_running.py
"""
import base64, io, pathlib, re, sys, tempfile, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_contract_otd as о
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
import fitz
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВЕРСИЯ = "Версия 2.1"
КЛИЕНТ = "Петров И. И."
ММ = 72 / 25.4


def pdf(кт, html, print_media=False):
    д = кт.new_page(viewport={"width": 900, "height": 1200})
    д.set_content(html, wait_until="load"); д.wait_for_timeout(900)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as ф:
        д.pdf(path=ф.name, format="A4", prefer_css_page_size=True, print_background=True)
        док = fitz.open(ф.name)
        стр = []
        for п in док:
            h = п.rect.height
            строки = []
            for б in п.get_text("dict")["blocks"]:
                for л in б.get("lines", []):
                    т = "".join(с["text"] for с in л["spans"]).strip()
                    if т:
                        строки.append((л["bbox"][1], л["bbox"][3], л["bbox"][0], т))
            стр.append({"h": h, "строки": строки, "текст": п.get_text()})
    д.close()
    return стр


def основной(кт, html, имя):
    страницы = pdf(кт, html)
    n = len(страницы)
    for i, с in enumerate(страницы, 1):
        h = с["h"]
        верх = [т for y0, y1, x, т in с["строки"] if y1 < 20 * ММ]
        низ = [(y0, т) for y0, y1, x, т in с["строки"] if y0 > h - 20 * ММ]
        тело = [y1 for y0, y1, x, т in с["строки"] if 20 * ММ <= y0 and y1 <= h - 20 * ММ]
        if ВЕРСИЯ not in верх:
            НАХОДКИ.append(f"[{имя}] стр. {i}: в верхнем поле нет «{ВЕРСИЯ}»: {верх}")
        if f"Страница {i} из {n}" not in верх:
            НАХОДКИ.append(f"[{имя}] стр. {i}: в верхнем поле нет «Страница {i} из {n}»: {верх}")
        тн = [т for _, т in низ]
        for нужно in ("Подрядчик", "Заказчик"):
            if нужно not in тн:
                НАХОДКИ.append(f"[{имя}] стр. {i}: в нижнем поле нет «{нужно}»: {тн}")
        фам = [т for т in тн if т.replace(" ", " ").startswith("Баранов")]
        if not фам or фам[0].replace(" ", " ") != "Баранов Г. Н.":
            НАХОДКИ.append(f"[{имя}] стр. {i}: фамилия подрядчика в поле не одной строкой: {тн}")
        кл = [т for т in тн if т.replace(" ", " ").startswith("Петров")]
        if not кл or кл[0].replace(" ", " ") != КЛИЕНТ:
            НАХОДКИ.append(f"[{имя}] стр. {i}: фамилия Заказчика в поле не одной строкой: {тн}")
        if низ and тело:
            зазор = (min(y for y, _ in низ) - max(тело)) / ММ
            if зазор < 3:
                НАХОДКИ.append(f"[{имя}] стр. {i}: подписи в поле в {зазор:.1f} мм от текста договора")
    if страницы and страницы[0]["текст"].count(ВЕРСИЯ) != 1:
        НАХОДКИ.append(f"[{имя}] стр. 1: «{ВЕРСИЯ}» встречается {страницы[0]['текст'].count(ВЕРСИЯ)} раз — строка над логотипом не снята")
    return n


def прочий(кт, html, имя):
    страницы = pdf(кт, html)
    n = len(страницы)
    for i, с in enumerate(страницы, 1):
        if "Версия" in с["текст"]:
            НАХОДКИ.append(f"[{имя}] стр. {i}: версия есть, а должна быть только у основного договора")
        if "Баранов Г" in с["текст"] or re.search(r"Подрядчик\s*\n\s*Баранов", с["текст"]):
            НАХОДКИ.append(f"[{имя}] стр. {i}: подписи в поле страницы, а должны быть только у основного договора")
        низ = [т for y0, y1, x, т in с["строки"] if y0 > с["h"] - 20 * ММ]
        if f"Страница {i} из {n}" not in низ:
            НАХОДКИ.append(f"[{имя}] стр. {i}: внизу нет «Страница {i} из {n}»: {низ}")


DOCX = """async (ид) => { const v = Object.assign(getContractVarsKar(ид), { clientShortName: '%s' });
  const б = await договорDocx(v); const м = new Uint8Array(await б.arrayBuffer()); let s = '';
  for (let i = 0; i < м.length; i += 8192) s += String.fromCharCode.apply(null, м.subarray(i, i + 8192)); return btoa(s); }""" % КЛИЕНТ


def word(стр, ид, имя, ждём):
    try:
        з = zipfile.ZipFile(io.BytesIO(base64.b64decode(стр.evaluate(DOCX, ид))))
    except Exception as е:
        НАХОДКИ.append(f"[Word {имя}] файл не собрался: {str(е).splitlines()[0][:160]}")
        return
    имена = з.namelist()
    шапка = "".join(з.read(и).decode("utf8") for и in имена if re.match(r"word/header\d*\.xml", и))
    подвал = "".join(з.read(и).decode("utf8") for и in имена if re.match(r"word/footer\d*\.xml", и))
    тш = re.sub(r"<[^>]+>", "", шапка); тп = re.sub(r"<[^>]+>", "", подвал)
    if ждём:
        if ВЕРСИЯ not in тш or "PAGE" not in шапка or "NUMPAGES" not in шапка:
            НАХОДКИ.append(f"[Word {имя}] в верхнем колонтитуле нет версии или номера страницы: «{тш[:80]}»")
        for нужно in ("Подрядчик", "Баранов Г. Н.", "Заказчик", КЛИЕНТ):
            if нужно not in тп:
                НАХОДКИ.append(f"[Word {имя}] в нижнем колонтитуле нет «{нужно}»: «{тп[:120]}»")
    else:
        if "Версия" in тш + тп or "Баранов" in тп:
            НАХОДКИ.append(f"[Word {имя}] колонтитулы основного договора попали в другой договор")
        if "NUMPAGES" not in подвал:
            НАХОДКИ.append(f"[Word {имя}] внизу пропал номер страницы")


ЭКРАН = """() => { const к = document.querySelector('#contractPreviewDoc iframe'); if (!к) return { нет: 'кадра' };
  const д = к.contentDocument, в = д.querySelector('.ver'), л = д.querySelector('.logo');
  if (!в) return { нет: 'строки версии' };
  const рв = в.getBoundingClientRect(), рл = л.getBoundingClientRect();
  return { текст: в.textContent.trim(), видна: getComputedStyle(в).display !== 'none' && рв.height > 0, выше: рв.bottom <= рл.top + .5, левее: Math.abs(рв.left - рл.left) < 8 }; }"""


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            к, стр, ош = о.начать(бр, порт, 1440, "admin")
            кт = СоШрифтами(бр)
            с_клиентом = "(ид) => сПалитрой(buildContractHtmlKar(Object.assign(getContractVarsKar(ид), { clientShortName: '%s' })))" % КЛИЕНТ
            html1 = стр.evaluate(с_клиентом, 1)
            n = основной(кт, html1, "основной")
            # Safari: признака Chromium нет — строка версии над логотипом остаётся на печати.
            без = html1.replace("/Chrome\\/\\d/.test", "/НетТакого/.test")
            if без == html1:
                НАХОДКИ.append("в договоре нет проверки признака Chromium для строки версии")
            else:
                д = кт.new_page(); д.set_content(без, wait_until="load"); д.emulate_media(media="print")
                if not д.evaluate("() => { const в = document.querySelector('.ver'); return !!в && getComputedStyle(в).display !== 'none'; }"):
                    НАХОДКИ.append("без признака Chromium (Safari) строки версии на печати нет — версия пропадёт совсем")
                д.close()
            прочий(кт, стр.evaluate(с_клиентом, 2), "на отделку")
            прочий(кт, стр.evaluate("() => сПалитрой(buildRulesHtml(getContractVarsKar(1)))"), "правила")
            прочий(кт, стр.evaluate("() => сПалитрой(buildConsentHtml(getContractVarsKar(1)))"), "согласие")
            word(стр, 1, "основной", True)
            word(стр, 2, "на отделку", False)
            стр.evaluate("async () => { setPreviewEntity('contract'); await new Promise(r => setTimeout(r, 900)); }")
            э = стр.evaluate(ЭКРАН)
            if э.get("нет") or not (э["видна"] and э["выше"] and э["левее"] and э["текст"] == ВЕРСИЯ):
                НАХОДКИ.append(f"на экране строка версии не над логотипом: {э}")
            for е in ош[:3]:
                НАХОДКИ.append(f"ошибка страницы: {е[:160]}")
            к.close(); бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print(f"Чисто: у основного договора на всех {n} страницах — «{ВЕРСИЯ}» и «Страница N из {n}» сверху, подписи сторон с "
          "фамилиями снизу, не ближе 3 мм к тексту; версия на первой странице одна, без Chromium (Safari) — строкой над "
          "логотипом; договор на отделку, правила и согласие — без колонтитулов основного; в Word — то же.")


if __name__ == "__main__":
    главная()
