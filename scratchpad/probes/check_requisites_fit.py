#!/usr/bin/env python3
"""Реквизиты сторон — на последнем листе текста, когда там хватает места.

Константин, 22.10.2026, снимком правил эксплуатации бруса, где лист с разделом
«Подписание» на две трети пуст, а реквизиты ушли на следующий: «Делай
проверку, если хватает места, зачем оставлять пустое и переносить на ещё один
лист». Блок реквизитов стоит на своей именованной странице (без подписей в
нижнем поле), а смена имени страницы всегда начинает лист; уложитьРеквизиты
раскладывает лист колонками 190 × 257 мм и снимает это, когда блок помещается.

Проба печатает в PDF настоящим Chromium договоры бруса и правила с парной и без
и по готовому PDF проверяет:
  • решение документа (keep-fit) совпадает с печатью: помещается — реквизиты на
    одной странице с последним пунктом перед ними; не помещается — на своей;
  • на листе, где реквизиты легли под текст, нет второй пары подписей
    («подпись, М.П.» блока) — подписи этого листа в нижнем поле;
  • на своём листе реквизитов строки подписей блока есть;
  • хотя бы один документ фикстуры укладывается (иначе проба ничего не держит).

    python3 check_requisites_fit.py
"""
import io, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_contracts as кд
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

НАХОДКИ = []
ШРИФТЫ = (pathlib.Path(__file__).parent / "шрифты_google.css").read_text()

# Документ, последний пункт перед реквизитами и строка из самих реквизитов.
ДОКУМЕНТЫ = [
    ("основной договор", "сПалитрой(buildContractHtmlKar(getContractVarsKar(1)))", "Акт выполненных работ", "30101 810 4 0000 0000225"),
    ("договор на отделку", "сПалитрой(buildContractHtmlKar(getContractVarsKar(2)))", "Акт выполненных работ", "30101 810 4 0000 0000225"),
    ("договор на покраску", "сПалитрой(buildContractHtmlKar(getContractVarsKar(3)))", "Акт выполненных работ", "30101 810 4 0000 0000225"),
    ("правила с парной", "сПалитрой(buildRulesHtml(getContractVarsKar(естьДоговор(2) ? 2 : 1)))", "Правила подписаны в двух", "генерального директора"),
]


# pypdf вставляет пробелы внутрь слов и перед знаками — сравнение без пробелов.
def сжать(т):
    return re.sub(r"\s+", "", т)


def страница(тексты, что):
    for и, т in enumerate(тексты):
        if сжать(что) in сжать(т):
            return и
    return -1


def напечатать(бр, html):
    п = бр.new_page()
    п.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    п.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    п.set_content(html, wait_until="load")
    п.wait_for_timeout(800)
    вместе = п.evaluate("() => !!document.querySelector('.keep.keep-fit')")
    п.emulate_media(media="print")
    pdf = п.pdf(prefer_css_page_size=True, print_background=True)
    п.close()
    return вместе, [с.extract_text() or "" for с in PdfReader(io.BytesIO(pdf)).pages]


def прогон(бр, порт, без_парной):
    стр = бр.new_page()
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(кд.таблицы(), ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    кд.открыть(стр, "glulam")
    стр.evaluate("""() => { const з = (id, в) => { const э = document.getElementById(id); if (э) э.value = в; };
      з('clientName', 'Иванов Пётр Сергеевич'); з('contractDate', '2026-10-22'); }""")
    документы = ДОКУМЕНТЫ
    if без_парной:
        стр.evaluate("""() => { ['steam', 'stove'].forEach(р => OPTIONS.filter(o => o.section === р && checkedOptions[o.id] && !o.included).forEach(o => toggleOpt(o.id))); calc(); }""")
        документы = [("правила без парной", ДОКУМЕНТЫ[3][1], ДОКУМЕНТЫ[3][2], ДОКУМЕНТЫ[3][3])]
    итоги = []
    for имя, выр, перед, свой in документы:
        html = стр.evaluate("() => " + выр)
        вместе, тексты = напечатать(бр, html)
        и_перед, и_рекв = страница(тексты, перед), страница(тексты, свой)
        if и_перед < 0 or и_рекв < 0:
            НАХОДКИ.append(f"{имя}: в PDF не найдены строки «{перед}» ({и_перед}) или «{свой}» ({и_рекв})")
            continue
        if вместе and и_рекв != и_перед:
            НАХОДКИ.append(f"{имя}: документ решил, что реквизиты помещаются, а печать унесла их со страницы {и_перед + 1} на {и_рекв + 1}")
        if not вместе and и_рекв == и_перед:
            НАХОДКИ.append(f"{имя}: реквизиты на одной странице с текстом, хотя документ решил иначе")
        подписи = "подпись" in сжать(тексты[и_рекв]).lower()
        if вместе and подписи:
            НАХОДКИ.append(f"{имя}: на листе с текстом и реквизитами — вторая пара подписей блока")
        if not вместе and not подписи:
            НАХОДКИ.append(f"{имя}: на своём листе реквизитов нет строк подписей блока")
        итоги.append((имя, вместе, len(тексты)))
        print(f"  {имя}: {'вместе с текстом' if вместе else 'своим листом'}, страниц {len(тексты)}")
    стр.close()
    return итоги


def главная():
    с, порт = м.сервер()
    итоги = []
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            итоги += прогон(бр, порт, False)
            итоги += прогон(бр, порт, True)
            бр.close()
    finally:
        с.shutdown()
    if not any(в for _, в, _ in итоги):
        НАХОДКИ.append("ни один документ фикстуры не уложил реквизиты под текст — проба ничего не проверяет")
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: реквизиты остаются на последнем листе текста, когда помещаются, и уходят своим листом, когда нет; решение документа совпадает с печатью Chromium, подписи не двоятся.")


if __name__ == "__main__":
    главная()
