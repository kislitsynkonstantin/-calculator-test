#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF архитектора в блоке «Визуализация и планировка» — на холст ложится планировка.

Константин 30.09.2026: «добавь возможность прикреплять файл — просто сразу
обрабатывается файл и вытаскивается из него планировка… только в само окно
должен уже лечь скриншот, не сам файл».

Проба на 1440 и 390 прикрепляет учебный PDF (образцы_приложения2/
план_учебный.pdf — вымышленный лист того же вида, что у архитектора: первым
идёт «План 1 этажа. Обмеры», вторым «План 1 этажа» с экспликацией справа и
штампом внизу) через поле «Добавить изображение» — как менеджер — и держит:
  • поле выбора принимает PDF;
  • на холст лёг ровно один снимок, и это картинка (data:image/…), а не файл;
  • взят лист «План 1 этажа», а не «Обмеры»: снимок распознан планировкой;
  • экспликация и штамп срезаны: снимок вытянут вверх, как сам план
    (ширина к высоте меньше 0,75; с колонкой справа было бы шире высоты);
  • тост сообщает, что планировка добавлена; ошибок нет.
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
    стр.evaluate("() => { window.__тосты = window.__тосты || []; canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove()); }")
    принимает = стр.evaluate("() => document.getElementById('canvasFileInput').accept")
    if "pdf" not in принимает:
        НАХОДКИ.append(f"{н} поле выбора не принимает PDF: {принимает}")
    стр.set_input_files("#canvasFileInput", str(ФАЙЛ))
    for _ in range(40):
        стр.wait_for_timeout(250)
        if стр.evaluate("() => canvasItems.length"): break
    стр.wait_for_timeout(600)
    р = стр.evaluate("""async () => { const сн = снимкиХолста(); if (!сн.length) return { n: 0 };
      const к = new Image(); await new Promise(r => { к.onload = к.onerror = r; к.src = сн[0]; });
      return { n: сн.length, картинка: /^data:image\\//.test(сн[0]), вид: await видКартинки(сн[0]), ш: к.naturalWidth, в: к.naturalHeight,
               тосты: (window.__тосты || []).join(' | ') }; }""")
    if р["n"] != 1:
        НАХОДКИ.append(f"{н} на холсте снимков {р['n']}, ждали один")
    else:
        if not р["картинка"]:
            НАХОДКИ.append(f"{н} на холст лёг не снимок: {р}")
        if р["вид"] != "планировка":
            НАХОДКИ.append(f"{н} снимок из PDF не распознан планировкой (взят не тот лист?): {р}")
        if р["ш"] / max(1, р["в"]) >= 0.75:
            НАХОДКИ.append(f"{н} экспликация или штамп не срезаны: {р['ш']}×{р['в']}")
        if "Планировка из PDF добавлена" not in р["тосты"]:
            НАХОДКИ.append(f"{н} тоста нет: {р['тосты']}")
    стр.screenshot(path=str(м.СНИМКИ / f"pdf-plan-{ш}.png"))
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
    print("Чисто: PDF принимается полем «Добавить изображение»; из листа «План 1 этажа» (не «Обмеры») на холст "
          "ложится одна картинка планировки без экспликации и штампа, тост сообщает о ней — на 1440 и 390.")


if __name__ == "__main__":
    главная()
