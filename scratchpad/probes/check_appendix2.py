#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно печати: третий документ — Приложение № 2 «Визуализация и планировка».

Константин 30.09.2026: «макет нормальный, встраивай в версию для печати и
выкладывай на тест» (макет — mockups/appendix-2-blank-v1.html).

Проба на 1440 и 390, с настоящими шрифтами (Google Fonts подменяются
шрифты_google.css) и настоящими снимками (визуализация и планировка):
  • в меню документа есть «Визуализация и планировка»; выбор ставит подпись
    кнопки, прячет инструменты спецификации и строку «Состав»;
  • снимки добавлены планировкой вперёд — код сам раскладывает: визуализация
    на первый лист, планировка на второй; второго вида нет — пустое место без
    подписи; листов два, «Лист 1 из 2», номера версии нет;
  • два вида и планировка — оба вида на первом листе;
  • «Зелёный-графит» — заголовок раздела графитом, черта зелёная; бирюза —
    бирюзовые; логотип под тон;
  • шрифты легли (ширина строки в Unbounded не равна подменной), ничего не
    вылезает за лист, в кадре нет ошибок;
  • «Печать / PDF» открывает окно с тем же документом.

    python3 check_appendix2.py
"""
import base64, io, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright
from PIL import Image

НАХОДКИ = []
ЗДЕСЬ = pathlib.Path(__file__).parent
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text()
ОБРАЗЦЫ = ЗДЕСЬ / "образцы_приложения2"


def data_url(путь, ш=900):
    к = Image.open(путь).convert("RGB"); к.thumbnail((ш, ш * 2))
    б = io.BytesIO(); к.save(б, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(б.getvalue()).decode()


# Снимки — адресами, как после выгрузки в хранилище: заглушка хранилища
# подменяет data: на адрес логотипа, и проба мерила бы логотип.
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ПЛАН = "/scratchpad/probes/образцы_приложения2/планировка.png"

ВИД = """() => { const к = document.querySelector('#appxPreviewDoc iframe'); if (!к) return null; const д = к.contentDocument;
  const листы = [...д.querySelectorAll('.sheet')];
  const c = д.createElement('canvas').getContext('2d'); const ширина = ш => { c.font = '20px ' + ш; return c.measureText('Визуализация и планировка').width; };
  return { листов: листы.length,
    номера: листы.map(л => (л.querySelector('.run') || {}).textContent || ''),
    версия: /Версия/.test(д.body.textContent),
    виды1: листы[0] ? листы[0].querySelectorAll('.fig--view img').length : 0,
    пустых1: листы[0] ? листы[0].querySelectorAll('.slot').length : 0,
    текстПустых: листы[0] ? [...листы[0].querySelectorAll('.slot')].map(с => с.textContent.trim()).join('') : '',
    план2: листы[1] ? листы[1].querySelectorAll('.fig--plan img').length : 0,
    планСрц: листы[1] && листы[1].querySelector('.fig--plan img') ? листы[1].querySelector('.fig--plan img').src.slice(0, 40) : '',
    шапка: (д.querySelector('.head') || {}).textContent || '',
    заголовок: getComputedStyle(д.querySelector('.sec-t')).color, черта: getComputedStyle(д.querySelector('.sec')).borderBottomColor,
    тон: д.documentElement.getAttribute('data-tone') || '',
    лого: (д.querySelector('.logo') || {}).src ? д.querySelector('.logo').src.length : 0,
    шрифт: [ширина("'Unbounded'"), ширина('serif')],
    вылез: листы.reduce((с, л) => { const q = л.getBoundingClientRect(); return с + [...л.querySelectorAll('*')].filter(э => { const w = э.getBoundingClientRect(); return w.width && (w.right > q.right + .5 || w.left < q.left - .5 || w.bottom > q.bottom + .5); }).length; }, 0),
    ширинаКадра: д.documentElement.scrollWidth, окно: innerWidth }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async ([виз, план]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); applyTone('bmsk', false); selectProjectOption(0); await new Promise(r => setTimeout(r, 900));
      document.getElementById('contractNumber').value = '11112222';
      canvasAddImage(план); canvasAddImage(виз); await new Promise(r => setTimeout(r, 300));
      openPrintPreview(); await new Promise(r => setTimeout(r, 400)); }""", [ВИЗ, ПЛАН])
    # Выбор документа — нажатием, как менеджер.
    стр.locator("#previewEntityBtn").click(); стр.wait_for_timeout(200)
    # Порядок: сразу после спецификации (30.09.2026: «поставь после Спецификации в списке»).
    порядок = стр.evaluate("() => [...document.querySelectorAll('#previewEntityMenu [data-entity]')].map(б => б.dataset.entity)")
    if порядок != ["spec", "appx", "contract"]:
        НАХОДКИ.append(f"{н} порядок документов в меню: {порядок}")
    пункт = стр.locator('#previewEntityMenu [data-entity="appx"]')
    if not пункт.count():
        НАХОДКИ.append(f"{н} в меню документа нет «Визуализация и планировка»"); стр.close(); return
    пункт.click(); стр.wait_for_timeout(1500)
    панель = стр.evaluate("""() => ({ подпись: document.getElementById('previewEntityLabel').textContent,
      стиль: getComputedStyle(document.getElementById('printStyleDropWrap')).display, состав: getComputedStyle(document.getElementById('printSectionsBar')).display,
      спец: getComputedStyle(document.getElementById('printDoc')).display })""")
    if панель["подпись"] != "Визуализация и планировка" or панель["стиль"] != "none" or панель["состав"] != "none" or панель["спец"] != "none":
        НАХОДКИ.append(f"{н} панель в режиме приложения: {панель}")
    с = стр.evaluate(ВИД)
    if not с:
        НАХОДКИ.append(f"{н} кадра приложения нет"); стр.close(); return
    if с["листов"] != 2 or с["номера"] != ["Лист 1 из 2", "Лист 2 из 2"] or с["версия"]:
        НАХОДКИ.append(f"{н} листы: {с['листов']} {с['номера']} версия={с['версия']}")
    if с["виды1"] != 1 or с["пустых1"] != 1 or с["текстПустых"] or с["план2"] != 1:
        НАХОДКИ.append(f"{н} раскладка снимков (планировка добавлена первой): видов {с['виды1']}, пустых {с['пустых1']} «{с['текстПустых']}», планировок на 2-м {с['план2']}")
    if "11112222-КАР" not in с["шапка"]:
        НАХОДКИ.append(f"{н} в шапке нет номера договора: {с['шапка'][:120]}")
    if с["тон"] != "bmsk" or с["заголовок"] != "rgb(36, 39, 31)" or с["черта"] != "rgb(112, 173, 52)":
        НАХОДКИ.append(f"{н} «Зелёный-графит»: тон {с['тон']}, заголовок {с['заголовок']}, черта {с['черта']}")
    if abs(с["шрифт"][0] - с["шрифт"][1]) < 1:
        НАХОДКИ.append(f"{н} Unbounded не лёг: {с['шрифт']}")
    if с["вылез"] or с["ширинаКадра"] > с["окно"]:
        НАХОДКИ.append(f"{н} вылезает за лист: {с['вылез']} элементов, ширина кадра {с['ширинаКадра']} при окне {с['окно']}")
    кадр = стр.locator("#appxPreviewDoc iframe")
    кадр.screenshot(path=str(м.СНИМКИ / f"appendix2-{ш}.png"))
    # Два вида и планировка — оба вида на первом листе.
    стр.evaluate("async (виз) => { canvasAddImage(виз); await показатьПриложение2(); await new Promise(r => setTimeout(r, 900)); }", ВИЗ)
    с2 = стр.evaluate(ВИД)
    if not с2 or с2["виды1"] != 2 or с2["пустых1"] != 0 or с2["листов"] != 2:
        НАХОДКИ.append(f"{н} два вида: {с2 and {к: с2[к] for к in ('виды1', 'пустых1', 'листов')}}")
    # Бирюза — заголовок и черта бирюзовые, логотип свой.
    стр.evaluate("async () => { applyTone('teal', false); await показатьПриложение2(); await new Promise(r => setTimeout(r, 900)); }")
    с3 = стр.evaluate(ВИД)
    if not с3 or с3["заголовок"] != "rgb(30, 108, 114)" or с3["черта"] != "rgb(30, 108, 114)" or с3["лого"] == с["лого"]:
        НАХОДКИ.append(f"{н} бирюза: {с3 and {к: с3[к] for к in ('заголовок', 'черта', 'лого')}}")
    # Печать — окно с тем же документом.
    печать = стр.evaluate("""async () => { let html = ''; const был = window.open;
      window.open = () => ({ document: { write: т => { html += т; }, close(){}, fonts: { ready: Promise.resolve() }, images: [] }, focus(){}, print(){} });
      await печатьПриложения2(); window.open = был; return { листов: (html.match(/class="sheet"/g) || []).length, a4: /size:A4/.test(html) }; }""")
    if печать["листов"] != 2 or not печать["a4"]:
        НАХОДКИ.append(f"{н} печать: {печать}")
    # Пустых листов в PDF нет: и со своими полями, и с полями Safari (по 12,7 мм,
    # с адресом и номером страницы) — страниц столько же, сколько листов.
    # 30.09.2026 Safari печатал пустую страницу за каждым листом.
    html = стр.evaluate("async () => сПалитрой(await собратьПриложение2())").replace('src="/scratchpad', f'src="http://127.0.0.1:{порт}/scratchpad')
    листов = html.count('class="sheet"')
    п = бр.new_page()
    п.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    import pymupdf
    п.set_content(html); п.wait_for_timeout(800)
    страниц = pymupdf.open(stream=п.pdf(print_background=True, prefer_css_page_size=True), filetype="pdf").page_count
    if страниц != листов:
        НАХОДКИ.append(f"{н} печать: страниц {страниц} при {листов} листах — лишние пустые")
    # Safari правило страницы не слушает и ставит свои поля по 12,7 мм: лист
    # обязан поместиться в 297 − 25,4 = 271,6 мм, иначе его хвост уходит на
    # отдельную пустую страницу. Chromium этого не повторяет — меряется геометрия.
    п.emulate_media(media="print")
    высоты = п.evaluate("() => [...document.querySelectorAll('.sheet')].map(л => л.getBoundingClientRect().height * 25.4 / 96)")
    if any(в_ > 271.6 for в_ in высоты):
        НАХОДКИ.append(f"{н} печать: лист выше страницы Safari (271,6 мм): {[round(в_) for в_ in высоты]} мм")
    п.close()
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 1440, 900)
            прогон(бр, порт, 390, 844)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: «Визуализация и планировка» — третий документ окна печати; снимки раскладываются сами (планировка "
          "на второй лист, второго вида нет — пустое место), два листа без номера версии, цвета и логотип по тону, "
          "шрифты легли, ничего не вылезает, печать уходит тем же документом — на 1440 и 390.")


if __name__ == "__main__":
    главная()
