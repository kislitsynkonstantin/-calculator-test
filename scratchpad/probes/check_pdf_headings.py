#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF с заголовками «Визуализация» и «Планировка»: планировка картинкой — планировка.

Константин 17.10.2026 прислал наше же Приложение № 2 (визуализация на первом
листе, планировка на втором — обе картинками) «для теста проверки по ним».
Калькулятор взял оба листа видами: планировку ищут по словам «План …» в тексте
листа, а у картинки решал цвет — заливки комнат цветные. «Проверка» просила
добавить планировку, которая уже стояла. Вдобавок картинка в таком PDF лежит
крупнее листа и обрезана маской (W n), и место картинки выходило выше заголовка.

Проба собирает такие листы сама — из учебных картинок папки
образцы_приложения2, без чужих имён — и держит:
  • два листа «1. ВИЗУАЛИЗАЦИЯ» и «2. ПЛАНИРОВКА»: первый — вид, второй —
    планировка, хотя комнаты на ней залиты голубым; картинка планировки
    положена крупнее и обрезана рамкой — вырезка по рамке, заголовок в неё не
    попал;
  • «Проверка» не просит добавить планировку и задаёт один вопрос — сверить
    с планировкой-снимком габариты, этажность, террасу, парную и печь;
  • оба раздела на одном листе: верхняя картинка — вид, нижняя — планировка;
  • лист без заголовков с цветной фотографией — по-прежнему вид.

    python3 check_pdf_headings.py
"""
import base64, functools, http.server, io, json, os, pathlib, socketserver, sys, tempfile, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
PDFJS = ЗДЕСЬ / "pdfjs"
ОБРАЗЦЫ = ЗДЕСЬ / "образцы_приложения2"
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []
ПАПКА = pathlib.Path(tempfile.mkdtemp(prefix="заголовки_pdf_"))


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


def данные(имя, тип):
    return f"data:{тип};base64," + base64.b64encode((ОБРАЗЦЫ / имя).read_bytes()).decode()


ВИЗ = данные("визуализация.jpg", "image/jpeg")
ПЛАН = данные("планировка.png", "image/png")
СТИЛЬ = """<style>@page{size:A4;margin:0}body{margin:0;font-family:Arial,sans-serif}
.лист{position:relative;width:210mm;height:297mm;page-break-after:always;overflow:hidden}
.з{position:absolute;left:25mm;font-size:5mm;font-weight:bold}
.к{position:absolute;left:25mm;width:160mm;overflow:hidden}
.к img{position:absolute;display:block}
.залив{position:absolute;background:rgba(80,140,230,.45)}</style>"""


def планировка(верх, высота):
    # Картинка крупнее окна и сдвинута: окно режет её, как Pages и Keynote.
    return (f'<div class="к" style="top:{верх}mm;height:{высота}mm"><img src="{ПЛАН}" style="left:-40mm;top:-30mm;width:240mm">'
            '<div class="залив" style="left:30mm;top:40mm;width:40mm;height:30mm"></div>'
            '<div class="залив" style="left:80mm;top:50mm;width:50mm;height:35mm"></div></div>')


ДОКИ = {
    "два_листа": СТИЛЬ + '<div class="лист"><div class="з" style="top:20mm">1. ВИЗУАЛИЗАЦИЯ</div>'
        f'<div class="к" style="top:32mm;height:90mm"><img src="{ВИЗ}" style="left:0;top:0;width:160mm"></div></div>'
        '<div class="лист"><div class="з" style="top:20mm">2. ПЛАНИРОВКА</div>' + планировка(32, 150) + '</div>',
    "один_лист": СТИЛЬ + '<div class="лист"><div class="з" style="top:15mm">1. ВИЗУАЛИЗАЦИЯ</div>'
        f'<div class="к" style="top:25mm;height:80mm"><img src="{ВИЗ}" style="left:0;top:0;width:160mm"></div>'
        '<div class="з" style="top:115mm">2. ПЛАНИРОВКА</div>' + планировка(125, 150) + '</div>',
    "без_заголовков": СТИЛЬ + f'<div class="лист"><div class="к" style="top:30mm;height:100mm"><img src="{ВИЗ}" style="left:0;top:0;width:160mm"></div></div>',
}


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


def отдать(r):
    путь = PDFJS / r.request.url.rsplit("/", 1)[-1]
    r.fulfill(status=200, content_type="application/javascript", body=путь.read_bytes()) if путь.exists() else r.abort()


РАЗБОР = """async (б) => { const р = await разобратьPdf(new Uint8Array(б));
  return { виды: р.виды.length, планы: р.планы.length, типы: [...р.виды, ...р.планы].map(к => к.тип),
    картинки: [...р.виды, ...р.планы].map(к => ({ тип: к.тип, src: к.src })) }; }"""


def главная():
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
        печать = бр.new_page()
        for имя, html in ДОКИ.items():
            печать.set_content(html); печать.wait_for_timeout(300)
            печать.pdf(path=str(ПАПКА / f"{имя}.pdf"), width="210mm", height="297mm", print_background=True)
        печать.close()
        стр = бр.new_page(viewport={"width": 1440, "height": 1000})
        ошибки = []
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        стр.route("**/cdnjs.cloudflare.com/ajax/libs/pdf.js/**", отдать)
        стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ЦЕНЫ)
        стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
        стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; selectProjectOption(0); calc(); }")
        стр.wait_for_timeout(500)

        р = стр.evaluate(РАЗБОР, list((ПАПКА / "два_листа.pdf").read_bytes()))
        факт(р["типы"] == ["вид", "план"], f"два листа: визуализация — вид, планировка — планировка: {р['типы']}")
        # Вырезка планировки — по рамке: сверху нет полосы заголовка (белое
        # поле листа и чёрные буквы «ПЛАНИРОВКА»), вырезка уже листа.
        план = next((к for к in р["картинки"] if к["тип"] == "план"), None)
        if план:
            разм = стр.evaluate("""(src) => new Promise(r => { const и = new Image(); и.onload = () => r([и.naturalWidth, и.naturalHeight]); и.src = src; })""", план["src"])
            факт(разм[0] > 0 and разм[1] / разм[0] < 1.2, f"вырезка планировки — по рамке картинки, а не весь лист (ш×в {разм})")
        # Через калькулятор целиком: «Проверка» не просит планировку, спрашивает одно.
        стр.evaluate("() => { canvasClearAll(); }")
        стр.set_input_files("#canvasFileInput", str(ПАПКА / "два_листа.pdf"))
        for _ in range(60):
            стр.wait_for_timeout(250)
            if стр.evaluate("() => canvasItems.length"):
                break
        стр.wait_for_timeout(1500); стр.evaluate("() => calc()"); стр.wait_for_timeout(300)
        п = стр.evaluate("""() => { const п = проверкаПоЧекЛисту(); return {
          виды: [...document.querySelectorAll('#imageCanvas .canvas-img-item')].map(э => э.dataset.kind || ''),
          вопросы: п.вопросы.filter(т => /планировк|визуализац/i.test(т)) }; }""")
        факт(sorted(п["виды"]) == ["вид", "план"], f"на холсте вид и планировка: {п['виды']}")
        факт(not any(т.startswith("Добавить") and "планировк" in т for т in п["вопросы"]), f"«Проверка» не просит добавить планировку ни в каком виде: {п['вопросы']}")
        факт(any(т.startswith("Планировка картинкой — калькулятор её не читает") for т in п["вопросы"]), f"«Проверка» просит сверить с планировкой-снимком: {п['вопросы']}")

        р = стр.evaluate(РАЗБОР, list((ПАПКА / "один_лист.pdf").read_bytes()))
        факт(р["типы"] == ["вид", "план"], f"оба раздела на одном листе: сверху вид, снизу планировка: {р['типы']}")
        р = стр.evaluate(РАЗБОР, list((ПАПКА / "без_заголовков.pdf").read_bytes()))
        факт(р["типы"] == ["вид"], f"лист без заголовков с цветной фотографией — вид: {р['типы']}")
        факт(not ошибки, f"ошибок страницы нет: {ошибки[:2]}")
        бр.close()
    с.shutdown()
    for т in ОТЧЁТ:
        print("    ок ", т)
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        sys.exit(1)
    print("Чисто: картинка под «Планировкой» — планировка, под «Визуализацией» — вид, вырезка по рамке; «Проверка» не просит "
          "планировку, которая есть, а сверяет её глазами; без заголовков — по цвету, как прежде.")


if __name__ == "__main__":
    главная()
