#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно печати: третий документ — Приложение № 2 «Визуализация и планировка».

Константин 30.09.2026: «макет нормальный, встраивай в версию для печати и
выкладывай на тест» (макет — mockups/appendix-2-blank-v1.html).

Проба на 1440 и 390, с настоящими шрифтами (Google Fonts подменяются
шрифты_google.css) и настоящими снимками (визуализация и планировка):
  • в меню документа есть «Вид и план»; выбор ставит подпись
    кнопки, прячет инструменты спецификации и строку «Состав»;
  • снимки добавлены планировкой вперёд — код сам раскладывает: визуализация
    на первый лист, планировка на второй; второго вида нет — пустое место без
    подписи; листов два, «Лист 1 из 2», номера версии нет;
  • два вида и планировка — оба вида на первом листе;
  • «Зелёный-графит» — заголовок раздела графитом, черта зелёная; бирюза —
    бирюзовые; логотип под тон;
  • шрифты легли (ширина строки в Unbounded не равна подменной), ничего не
    вылезает за лист, в кадре нет ошибок;
  • «Печать / PDF» открывает окно с тем же документом;
  • печать трёх видов и планировки (три листа) — страниц столько же и со
    своими полями, и с полями Safari по 20 мм; каждый лист на печати — простой
    поток не выше 195 мм с подписями внутри (Константин, 30.09.2026, снимками
    окна печати iPhone: «печать криво: пустые также листы»);
  • на листах видов подписи без «Подрядчик» и «Заказчик» — только фамилии и
    место для подписи; на последнем листе, после планировки, обе подписаны
    (Константин, 01.10.2026).

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
    // Под номером листа линейки нет (Константин, 06.10.2026: «эту линию убери»).
    // Номер листа — колонтитулом печати: на экране его нет (06.10.2026: «чтобы на просмотре их и не было»).
    номерНаЭкране: листы.filter(л => { const р = л.querySelector('.run'); return р && getComputedStyle(р).display !== 'none'; }).length,
    линия: листы.map(л => { const р = л.querySelector('.run'); return р ? getComputedStyle(р).borderBottomWidth : ''; }).filter(w => w && w !== '0px'),
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
    if порядок != ["spec", "appx", "contract", "contract", "rules", "consent"]:
        НАХОДКИ.append(f"{н} порядок документов в меню: {порядок}")
    пункт = стр.locator('#previewEntityMenu [data-entity="appx"]')
    if not пункт.count():
        НАХОДКИ.append(f"{н} в меню документа нет пункта приложения"); стр.close(); return
    # Подпись в окне — «Вид и план» (01.10.2026), лист называется по-прежнему.
    подп = пункт.locator("span:not(.entity-check)").first.inner_text().strip()
    if подп != "Вид и план":
        НАХОДКИ.append(f"{н} пункт меню: «{подп}», ждали «Вид и план»")
    пункт.click(); стр.wait_for_timeout(1500)
    панель = стр.evaluate("""() => ({ подпись: document.getElementById('previewEntityLabel').textContent,
      стиль: getComputedStyle(document.getElementById('printStyleDropWrap')).display, состав: getComputedStyle(document.getElementById('printSectionsBar')).display,
      спец: getComputedStyle(document.getElementById('printDoc')).display })""")
    if панель["подпись"] != "Вид и план" or панель["стиль"] != "none" or панель["состав"] != "none" or панель["спец"] != "none":
        НАХОДКИ.append(f"{н} панель в режиме приложения: {панель}")
    с = стр.evaluate(ВИД)
    if not с:
        НАХОДКИ.append(f"{н} кадра приложения нет"); стр.close(); return
    if с["листов"] != 2 or с["номера"] != ["Лист 1 из 2", "Лист 2 из 2"] or с["версия"]:
        НАХОДКИ.append(f"{н} листы: {с['листов']} {с['номера']} версия={с['версия']}")
    if с["номерНаЭкране"]:
        НАХОДКИ.append(f"{н} на экране видно «Лист N из M» на {с['номерНаЭкране']} листах — номер только колонтитулом печати")
    if с["линия"]:
        НАХОДКИ.append(f"{н} под «Лист N из M» линейка: {с['линия']}")
    if с["виды1"] != 1 or с["пустых1"] != 1 or с["текстПустых"] or с["план2"] != 1:
        НАХОДКИ.append(f"{н} раскладка снимков (планировка добавлена первой): видов {с['виды1']}, пустых {с['пустых1']} «{с['текстПустых']}», планировок на 2-м {с['план2']}")
    # Номер — как в шапке спецификации: состав «Отделка» — -ОТД, основной — -КАР
    # (30.09.2026: «когда тут стоит -ОТД, то тоже должен быть ОТД. И наоборот»).
    for ид, приписка in ((2, "-ОТД"), (1, "-КАР")):
        ш_ = стр.evaluate("""async (ид) => { printSelectContract(ид); if (printActiveContractId !== ид) printSelectContract(ид);
          await показатьПриложение2(); await new Promise(r => setTimeout(r, 700));
          const д = document.querySelector('#appxPreviewDoc iframe').contentDocument;
          return { шапка: (д.querySelector('.head') || {}).textContent || '', спец: номерСКодом(document.getElementById('contractNumber').value) }; }""", ид)
        if "11112222" + приписка not in ш_["шапка"] or ш_["спец"] not in ш_["шапка"]:
            НАХОДКИ.append(f"{н} номер договора при составе {приписка}: в приложении «{ш_['шапка'].strip()[:90]}», в спецификации {ш_['спец']}")
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
    # Обычное фото 4:3 не режется под широкий экран: вид вписан целиком
    # (object-fit: contain), без обрезки (30.09.2026: «широкий экран
    # изображения не нужен — обычно формат обычного фото»).
    фото = стр.evaluate("""async (ф) => { canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
      canvasAddImage(ф); await new Promise(r => setTimeout(r, 400)); await показатьПриложение2(); await new Promise(r => setTimeout(r, 900));
      const д = document.querySelector('#appxPreviewDoc iframe').contentDocument; const к = д.querySelector('.fig--view img'); if (!к) return null;
      const q = к.getBoundingClientRect(), ст = getComputedStyle(к);
      const ш = Math.min(q.width, q.height * к.naturalWidth / к.naturalHeight), в = ш * к.naturalHeight / к.naturalWidth;
      return { fit: ст.objectFit, д: к.naturalWidth / к.naturalHeight, видимо: [Math.round(ш), Math.round(в)], коробка: [Math.round(q.width), Math.round(q.height)] }; }""", "/scratchpad/probes/образцы_приложения2/фото_4x3.jpg")
    if not фото or фото["fit"] not in ("contain", "fill") or abs(фото["д"] - 4 / 3) > 0.02:
        НАХОДКИ.append(f"{н} фото 4:3 в приложении обрезано или не встало: {фото}")
    elif фото["fit"] == "fill" and abs(фото["коробка"][0] / max(1, фото["коробка"][1]) - фото["д"]) > 0.04:
        НАХОДКИ.append(f"{н} фото 4:3 растянуто: {фото}")
    стр.evaluate("async (s) => { canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove()); canvasAddImage(s[0]); canvasAddImage(s[1]); canvasAddImage(s[1]); canvasAddImage(s[2]); await new Promise(r => setTimeout(r, 400)); }", [ПЛАН, ВИЗ, "/scratchpad/probes/образцы_приложения2/фото_4x3.jpg"])
    # Бирюза — заголовок и черта бирюзовые, логотип свой.
    стр.evaluate("async () => { applyTone('teal', false); await показатьПриложение2(); await new Promise(r => setTimeout(r, 900)); }")
    с3 = стр.evaluate(ВИД)
    if not с3 or с3["заголовок"] != "rgb(30, 108, 114)" or с3["черта"] != "rgb(30, 108, 114)" or с3["лого"] == с["лого"]:
        НАХОДКИ.append(f"{н} бирюза: {с3 and {к: с3[к] for к in ('заголовок', 'черта', 'лого')}}")
    # Печать — окно с тем же документом.
    печать = стр.evaluate("""async () => { let html = ''; const был = window.open;
      window.open = () => ({ document: { write: т => { html += т; }, close(){}, fonts: { ready: Promise.resolve() }, images: [] }, focus(){}, print(){} });
      await печатьПриложения2(); window.open = был; return { листов: (html.match(/class="sheet[ "]/g) || []).length, a4: /size:A4/.test(html) }; }""")
    if печать["листов"] != 3 or not печать["a4"]:
        НАХОДКИ.append(f"{н} печать: {печать}")
    # Пустых листов в PDF нет: и со своими полями, и с полями Safari (по 12,7 мм,
    # с адресом и номером страницы) — страниц столько же, сколько листов.
    # 30.09.2026 Safari печатал пустую страницу за каждым листом.
    html = стр.evaluate("async () => сПалитрой(await собратьПриложение2())").replace('src="/scratchpad', f'src="http://127.0.0.1:{порт}/scratchpad')
    листов = html.count('class="sheet"') + html.count('class="sheet ')
    секции = html.split('<section')[1:]
    кто = [с.count('class="sign-who"') for с in секции]
    фамилий = [с.count('class="sign-name"') for с in секции]
    if кто[:-1] != [0] * (len(секции) - 1) or кто[-1] != 2 or any(ф != 2 for ф in фамилий):
        НАХОДКИ.append(f"{н} подписи листов: «Подрядчик/Заказчик» по листам {кто} (ждали 0 на видах и 2 на последнем), фамилий {фамилий}")
    п = бр.new_page(viewport={"width": 718, "height": 1000})
    п.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    import pymupdf
    п.set_content(html); п.wait_for_timeout(800)
    док = pymupdf.open(stream=п.pdf(print_background=True, prefer_css_page_size=True), filetype="pdf")
    страниц = док.page_count
    if страниц != листов:
        НАХОДКИ.append(f"{н} печать: страниц {страниц} при {листов} листах — лишние пустые")
    # Номер листа в Chromium — в верхнем поле страницы, один раз на странице.
    for i, стр_ in enumerate(док, 1):
        т = стр_.get_text()
        верх = стр_.get_text(clip=pymupdf.Rect(0, 0, стр_.rect.width, 20 * 72 / 25.4))
        if т.count("Лист ") != 1 or f"Лист {i} из {страниц}" not in верх:
            НАХОДКИ.append(f"{н} печать: на стр. {i} номер листа не один раз в верхнем поле: всего «Лист» {т.count('Лист ')}, в поле «{верх.strip()[:40]}»")
    # Safari поля страницы не печатает — ему строка номера в самом листе остаётся.
    сафари = бр.new_page(); сафари.set_content(html.replace("/Chrome\\/\\d/.test", "/НетТакого/.test")); сафари.emulate_media(media="print")
    if сафари.evaluate("() => [...document.querySelectorAll('.sheet .run')].filter(р => getComputedStyle(р).display !== 'none').length") != листов:
        НАХОДКИ.append(f"{н} без признака Chromium (Safari) номера листа на печати нет")
    if "/НетТакого/" not in сафари.content():
        НАХОДКИ.append(f"{н} в приложении нет проверки признака Chromium")
    сафари.close()
    # Поля Safari на iPhone шире своих и несут адрес, дату и номер страницы
    # (30.09.2026, снимок окна печати): поля по 20 мм сверху и снизу — и
    # страниц всё равно столько же, сколько листов.
    страниц = pymupdf.open(stream=п.pdf(print_background=True, prefer_css_page_size=False, format="A4",
        margin={"top": "20mm", "bottom": "20mm", "left": "12mm", "right": "12mm"}), filetype="pdf").page_count
    if страниц != листов:
        НАХОДКИ.append(f"{н} печать с полями Safari: страниц {страниц} при {листов} листах — лишние пустые")
    # Safari на iPhone печатает крупнее заданного: на снимке Константина
    # (30.09.2026, «когда 2 — вот так обрезает») вид в 72 мм вышел 81 мм, то
    # есть масштаб около 1,12, при полях около 17 мм сверху и 16 снизу.
    # Повторяем это в Chromium: масштаб 1,15 с запасом и те же поля.
    страниц = pymupdf.open(stream=п.pdf(print_background=True, prefer_css_page_size=False, format="A4", scale=1.25,
        margin={"top": "17mm", "bottom": "17mm", "left": "10mm", "right": "10mm"}), filetype="pdf").page_count
    if страниц != листов:
        НАХОДКИ.append(f"{н} печать как на iPhone (масштаб 1,25, поля Safari): страниц {страниц} при {листов} листах")
    # Safari правило страницы не слушает и ставит свои поля по 12,7 мм: лист
    # обязан поместиться в 297 − 25,4 = 271,6 мм, иначе его хвост уходит на
    # отдельную пустую страницу. Chromium этого не повторяет — меряется геометрия.
    п.emulate_media(media="print")
    # Высоту листа на печати Safari не держит (снимки встают в свой рост), так
    # что лист обязан быть коротким сам: всё его содержимое — не выше 228 мм
    # при ширине страницы 190 мм, и подписи внутри листа.
    высоты = п.evaluate("""() => [...document.querySelectorAll('.sheet')].map(л => { const р = л.getBoundingClientRect(), п = л.querySelector('.sign').getBoundingClientRect();
      return { в: р.height * 25.4 / 96, подписи: п.bottom <= р.bottom + 1, фикс: getComputedStyle(л).height.endsWith('px') && л.style.height !== '' }; })""")
    # 01.10.2026: 214 мм первого листа на iPhone не влезли — Safari пишет в поля
    # дату и адрес, подписи ушли на вторую страницу. Предел — 195 мм.
    if any(в_["в"] > 195 or not в_["подписи"] for в_ in высоты):
        НАХОДКИ.append(f"{н} печать: лист выше 195 мм или подписи вне листа: {[round(в_['в']) for в_ in высоты]} мм")
    фикс = п.evaluate("() => [...document.querySelectorAll('.sheet')].map(л => getComputedStyle(л).display + ' ' + (л.style.height || ''))")
    if any(ф.startswith("flex") for ф in фикс):
        НАХОДКИ.append(f"{н} печать: лист по-прежнему растягивается flex по высоте: {фикс}")
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
