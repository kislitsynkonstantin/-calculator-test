#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF архитектора в блоке «Визуализация и планировка» — на холст ложится планировка.

Константин 30.09.2026: «добавь возможность прикреплять файл — просто сразу
обрабатывается файл и вытаскивается из него планировка… только в само окно
должен уже лечь скриншот, не сам файл».

Проба на 1440 и 390 прикрепляет учебный PDF (образцы_приложения2/
план_учебный.pdf — вымышленный лист того же вида, что у архитектора: первым
идёт лист «Визуализация» с вклеенной картинкой, вторым «План 1 этажа. Обмеры»,
третьим «План 1 этажа» с рамкой, экспликацией справа, примечаниями и штампом) через поле «Добавить изображение» — как менеджер — и держит:
  • поле выбора принимает PDF;
  • на холст легли картинки (data:image/…), а не файл: визуализация с листа
    «Визуализация» и планировка с листа «План 1 этажа», не «Обмеры»
    (Константин, 30.09.2026: «также с визуализациями давай сделаем»);
  • у планировки срезаны экспликация, штамп и «Примечания»: снимок вытянут
    вверх (ширина к высоте меньше 0,75);
  • рамки листа на планировке нет: в крайних 6 % нет столбца или ряда, тёмного
    больше чем на 60 % («вот такие линии только убирай с планировки»);
  • тост называет добавленное; ошибок нет;
  • второй учебный лист (образцы_приложения2/план_таблица.pdf): экспликация
    справа таблицей, её первая колонка «№ пом.» левее заголовка — на
    планировке от таблицы не остаётся ничего: у правого края снимка нет ни
    одного тёмного пикселя (Константин, 30.09.2026, снимком полосы таблицы у
    края плана: «лишние рамки нужно с планировки убирать»).
pdf.js в контейнере с cdnjs не грузится — проба отдаёт ту же сборку 3.11.174
из npm (ставит её сама в pdfjs/, в репозиторий она не идёт).

    python3 check_pdf_plan.py
"""
import pathlib, subprocess, sys, tarfile, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЗДЕСЬ = pathlib.Path(__file__).parent
PDFJS = ЗДЕСЬ / "pdfjs"
ФАЙЛ = ЗДЕСЬ / "образцы_приложения2" / "план_учебный.pdf"
ТАБЛИЦА = ЗДЕСЬ / "образцы_приложения2" / "план_таблица.pdf"


def pdfjs():
    if (PDFJS / "pdf.min.js").exists() and (PDFJS / "pdf.worker.min.js").exists():
        return
    PDFJS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as т:
        subprocess.run(["npm", "pack", "pdfjs-dist@3.11.174"], cwd=т, check=True, capture_output=True)
        with tarfile.open(next(pathlib.Path(т).glob("pdfjs-dist-*.tgz"))) as а:
            for имя in ("pdf.min.js", "pdf.worker.min.js"):
                (PDFJS / имя).write_bytes(а.extractfile("package/build/" + имя).read())


def отдать(r):
    имя = r.request.url.rsplit("/", 1)[-1]
    путь = PDFJS / имя
    if путь.exists():
        r.fulfill(status=200, content_type="application/javascript", body=путь.read_bytes())
    else:
        r.abort()


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.route("**/cdnjs.cloudflare.com/ajax/libs/pdf.js/**", отдать)
    # Заглушка хранилища подменяет выгруженные снимки логотипом — выгрузку
    # на время пробы выключаем, снимки остаются теми, что легли на холст.
    стр.evaluate("() => { window.uploadCanvasToStorage = async (_, снимки) => (снимки || []).map(с => ({ url: с.src, left: с.left, top: с.top, width: с.width, height: с.height })); }")
    стр.evaluate("() => { window.__тосты = window.__тосты || []; canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove()); }")
    принимает = стр.evaluate("() => document.getElementById('canvasFileInput').accept")
    if "pdf" not in принимает:
        НАХОДКИ.append(f"{н} поле выбора не принимает PDF: {принимает}")
    стр.set_input_files("#canvasFileInput", str(ФАЙЛ))
    for _ in range(40):
        стр.wait_for_timeout(250)
        if стр.evaluate("() => canvasItems.length"): break
    стр.wait_for_timeout(1500)
    р = стр.evaluate("""async () => { const сн = снимкиХолста(); const о = [];
      for (const s of сн) { const к = new Image(); await new Promise(r => { к.onload = к.onerror = r; к.src = s; });
        const х = document.createElement('canvas'); х.width = к.naturalWidth; х.height = к.naturalHeight; const кт = х.getContext('2d'); кт.drawImage(к, 0, 0);
        const д = кт.getImageData(0, 0, х.width, х.height).data;
        // самый длинный тёмный столбец и ряд в крайних 6 % — след рамки
        const тёмн = (x, y) => { const и = (y * х.width + x) * 4; return 255 - Math.min(д[и], д[и + 1], д[и + 2]) > 90; };
        let столбец = 0, ряд = 0;
        for (let x = 0; x < х.width * 0.06; x++) { let н = 0; for (let y = 0; y < х.height; y++) if (тёмн(x, y)) н++; столбец = Math.max(столбец, н / х.height); }
        for (let y = 0; y < х.height * 0.06; y++) { let н = 0; for (let x = 0; x < х.width; x++) if (тёмн(x, y)) н++; ряд = Math.max(ряд, н / х.width); }
        о.push({ картинка: /^data:image\//.test(s), вид: await видКартинки(s), ш: к.naturalWidth, в: к.naturalHeight, столбец, ряд }); }
      return { сн: о, тосты: (window.__тосты || []).join(' | ') }; }""")
    сн = р["сн"]
    виды = [x["вид"] for x in сн]
    if виды != ["визуализация", "планировка"]:
        НАХОДКИ.append(f"{н} из учебного проекта ждали визуализацию и планировку, пришло {виды}")
    for x in сн:
        if not x["картинка"]:
            НАХОДКИ.append(f"{н} на холст лёг не снимок: {x}")
    план = next((x for x in сн if x["вид"] == "планировка"), None)
    if план:
        if план["ш"] / max(1, план["в"]) >= 0.75:
            НАХОДКИ.append(f"{н} экспликация, штамп или примечания не срезаны: {план['ш']}×{план['в']}")
        if план["столбец"] > 0.6 or план["ряд"] > 0.6:
            НАХОДКИ.append(f"{н} рамка листа осталась на планировке: столбец {план['столбец']:.2f}, ряд {план['ряд']:.2f}")
    if "визуализация" not in р["тосты"] or "планировка" not in р["тосты"]:
        НАХОДКИ.append(f"{н} тост не называет добавленное: {р['тосты']}")
    стр.screenshot(path=str(м.СНИМКИ / f"pdf-plan-{ш}.png"))
    # Лист с таблицей-экспликацией справа.
    стр.evaluate("() => { canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove()); }")
    стр.set_input_files("#canvasFileInput", str(ТАБЛИЦА))
    for _ in range(40):
        стр.wait_for_timeout(250)
        if стр.evaluate("() => canvasItems.length"): break
    стр.wait_for_timeout(800)
    т = стр.evaluate("""async () => { const сн = снимкиХолста(); if (сн.length !== 1) return { n: сн.length };
      const к = new Image(); await new Promise(r => { к.onload = к.onerror = r; к.src = сн[0]; });
      const х = document.createElement('canvas'); х.width = к.naturalWidth; х.height = к.naturalHeight; const кт = х.getContext('2d'); кт.drawImage(к, 0, 0);
      const д = кт.getImageData(0, 0, х.width, х.height).data; let край = 0;
      for (let y = 0; y < х.height; y++) for (let x = х.width - 8; x < х.width; x++) { const и = (y * х.width + x) * 4; if (255 - Math.min(д[и], д[и + 1], д[и + 2]) > 90) край++; }
      return { n: 1, край, ш: х.width, в: х.height }; }""")
    if т["n"] != 1 or т.get("край"):
        НАХОДКИ.append(f"{н} лист с таблицей-экспликацией: у правого края планировки осталась таблица или снимков не один: {т}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    pdfjs()
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
    print("Чисто: PDF проекта принимается полем «Добавить изображение»; на холст ложатся визуализация и планировка "
          "(не «Обмеры»), у планировки срезаны экспликация (и таблицей с колонкой левее заголовка), штамп, примечания и рамка листа, тост называет добавленное — на 1440 и 390.")


if __name__ == "__main__":
    главная()
