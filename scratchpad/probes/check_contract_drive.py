#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договор подряда на Google Диск — кнопка в окне печати.

Константин 01.10.2026: «добавь кнопку сохранить на гугл диск. Скачать Word
убери… договор грузится в диск сотрудника, который открывает. Эта кнопка будет
не у всех ролей», затем по макету contract-final-v1: «макет утверждаю,
внедряй в калькулятор».

Проба на 390 и 1440, с настоящими шрифтами, держит:
  • у менеджера кнопки «Google Диск» нет; у ролей из РОЛИ_ДИСКА она есть —
    только когда в окне печати открыт договор, не спецификация;
  • кнопка в пределах экрана и не налезает на соседние кнопки панели;
  • нажатие открывает Google Диск в новой вкладке и скачивает файл
    «Договор подряда <номер>.docx»;
  • файл — настоящий .docx: в нём все 14 разделов, строки платежей и итог,
    участок и объект, реквизиты сторон; две картинки (логотип и шкала
    гарантии); шрифты по именам Google — Unbounded и Geologica; файл
    открывается сторонним разборщиком docx (docx-preview) без ошибок.

    python3 check_contract_drive.py
"""
import io, pathlib, re, sys, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЗДЕСЬ = pathlib.Path(__file__).parent


def начать(бр, порт, ш, роль):
    к = бр.new_context(viewport={"width": ш, "height": 900}, accept_downloads=True)
    к.route("**/drive.google.com/**", lambda r: r.fulfill(status=200, body="drive"))
    стр = СоШрифтами(к).new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.add_init_script(f"window.__ТАБЛИЦЫ.profiles = [{{ id: 'u-проба', role: '{роль}', first_name: 'Анна', last_name: 'Соколова', app_settings: {{}} }}];")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      await loadSbProfile(); applyUiStyle('blank', false); applyTone('bmsk', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
      document.getElementById('contractNumber').value = '11112222'; openPrintPreview(); await new Promise(r => setTimeout(r, 400)); }""")
    return к, стр, ош


КНОПКА = """() => { const б = document.getElementById('contractDriveBtn'); if (!б) return null; const р = б.getBoundingClientRect();
  const сос = [...б.parentElement.children].filter(э => э !== б && э.tagName === 'BUTTON' && э.offsetParent).map(э => э.getBoundingClientRect())
    .filter(q => !(q.right <= р.left || q.left >= р.right || q.bottom <= р.top || q.top >= р.bottom));
  return { видна: getComputedStyle(б).display !== 'none' && р.width > 0, внутри: р.left >= 0 && р.right <= innerWidth + .5, налезает: сос.length }; }"""


def прогон(бр, порт, ш):
    for роль in ("manager", "admin"):
        н = f"[{ш} {роль}]"
        к, стр, ош = начать(бр, порт, ш, роль)
        спец = стр.evaluate(КНОПКА)
        стр.evaluate("async () => { setPreviewEntity('contract'); await new Promise(r => setTimeout(r, 800)); }")
        дог = стр.evaluate(КНОПКА)
        if роль == "manager":
            if not дог or дог["видна"]:
                НАХОДКИ.append(f"{н} у менеджера видна кнопка «Google Диск»: {дог}")
            к.close(); continue
        if спец and спец["видна"]:
            НАХОДКИ.append(f"{н} кнопка «Google Диск» видна у спецификации")
        if not дог or not дог["видна"] or not дог["внутри"] or дог["налезает"]:
            НАХОДКИ.append(f"{н} кнопка «Google Диск» в договоре: {дог}")
            к.close(); continue
        if ш == 1440:
            стр.screenshot(path=str(м.СНИМКИ / "contract-drive-1440.png"))
        with к.expect_page() as нов, стр.expect_download(timeout=30000) as з:
            стр.click("#contractDriveBtn")
        if "drive.google.com" not in нов.value.url:
            НАХОДКИ.append(f"{н} открылась не Google Диск: {нов.value.url}")
        имя = з.value.suggested_filename
        if имя != "Договор подряда 11112222-КАР.docx":
            НАХОДКИ.append(f"{н} имя файла: {имя}")
        путь = ЗДЕСЬ / f"_договор_{ш}.docx"; з.value.save_as(str(путь))
        try:
            зп = zipfile.ZipFile(путь); doc = зп.read("word/document.xml").decode("utf-8")
            текст = re.sub(r"<[^>]+>", "", doc)
            нужно = ["Предмет договора", "Цена и порядок оплаты", "Платёж № 1", "Итого", "Адрес участка", "Кадастровый номер",
                     "Адреса и реквизиты", "ООО «ПСК ВЕГА»", "Паспортные данные", "Рабочее время", "подпись, М.П."]
            нет = [х for х in нужно if х.lower() not in текст.lower()]
            разделов = len(re.findall(r"(?<!\d)(\d{1,2})\.\s", текст))
            картинок = len([и for и in зп.namelist() if и.startswith("word/media/") and not и.endswith("/")])
            шрифты = set(re.findall(r'w:ascii="([^"]+)"', doc))
            if нет:
                НАХОДКИ.append(f"{н} в .docx нет: {нет}")
            if картинок != 2:
                НАХОДКИ.append(f"{н} картинок в .docx {картинок}, ждали 2 (логотип и шкала): {[(и, зп.getinfo(и).file_size) for и in зп.namelist() if и.startswith('word/media/')]}")
            if not шрифты or not шрифты <= {"Unbounded", "Geologica"}:
                НАХОДКИ.append(f"{н} шрифты в .docx не по именам Google: {шрифты}")
            for номер in range(1, 15):
                if f"{номер}. " not in текст and f"{номер}." not in текст:
                    НАХОДКИ.append(f"{н} в .docx нет раздела {номер}"); break
        except Exception as e:
            НАХОДКИ.append(f"{н} .docx не разбирается: {e}")
        # Сторонний разборщик: docx-preview открывает файл без ошибок.
        вид = к.new_page()
        вид.goto(f"http://127.0.0.1:{порт}/scratchpad/word_view/view.html?f=../probes/{путь.name}"); вид.wait_for_timeout(2500)
        р = вид.evaluate("() => ({ ok: window.__ok, err: window.__err, таблиц: document.querySelectorAll('table').length })")
        if not р["ok"] or р["таблиц"] < 8:
            НАХОДКИ.append(f"{н} docx-preview: {р}")
        if ш == 1440:
            вид.screenshot(path=str(м.СНИМКИ / "contract-docx-1440.png"), full_page=True)
        вид.close()
        путь.unlink(missing_ok=True)
        for о in [о for о in ош if "supabase.co" not in о][:3]:
            НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
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
    print("Чисто: «Google Диск» в окне печати — только у ролей из РОЛИ_ДИСКА и только у договора; открывает Диск и отдаёт "
          ".docx со всеми разделами, платежами и итогом, реквизитами, двумя картинками и шрифтами Google; docx-preview "
          "открывает файл без ошибок — на 390 и 1440.")


if __name__ == "__main__":
    главная()
