#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вертикальная планировка рядом с визуализацией — целиком, в своих пропорциях.

Константин 30.09.2026, снимками Приложения № 2 и спецификации: «в файле
„Визуализация и планировка“ планировку отлично вырезал с PDF, а в
спецификации криво — добавь возможность вертикальную планировку туда
вырезать, чтобы хорошо сочеталась с визуалкой».

Печать спецификации повторяет холст, а холст клал любой снимок в коробку
340×220 и в «Авто-расстановке» — в одинаковые коробки 0,65: вертикальная
планировка обрезалась сверху и снизу. Проба на 1440 и 390 держит:
  • добавленный снимок встаёт в своих пропорциях (коробка ≈ картинка, ±3 %);
  • «Авто-расстановка» ставит визуализацию и планировку в один ряд общей
    высоты, ширины — по пропорциям, ряд в пределах холста;
  • в печати спецификации у обоих снимков коробка той же пропорции, что
    картинка: ничего не срезано; снимок ряда на 1440 и 390.

    python3 check_plan_layout.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ПЛАН = "/scratchpad/probes/образцы_приложения2/планировка.png"
КОРОБКИ = """() => [...document.querySelectorAll('#imageCanvas .canvas-img-item')].map(э => { const к = э.querySelector('img');
  return { л: э.offsetLeft, в: э.offsetTop, ш: э.offsetWidth, вы: э.offsetHeight, д: к.naturalWidth / к.naturalHeight }; })"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.evaluate("""async ([виз, план]) => { canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
      const б = document.getElementById('btnCollapseImageCard'); if (б && б.classList.contains('collapsed')) toggleImageCard();
      canvasAddImage(виз); canvasAddImage(план); await new Promise(r => setTimeout(r, 900)); }""", [ВИЗ, ПЛАН])
    for и, к_ in enumerate(стр.evaluate(КОРОБКИ)):
        if abs(к_["ш"] / к_["вы"] - к_["д"]) / к_["д"] > 0.03:
            НАХОДКИ.append(f"{н} добавленный снимок {и + 1} не в своих пропорциях: коробка {к_['ш']}×{к_['вы']}, картинка {к_['д']:.2f}")
    стр.evaluate("() => canvasAutoCenter()"); стр.wait_for_timeout(300)
    кор = стр.evaluate(КОРОБКИ)
    холст = стр.evaluate("() => document.getElementById('imageCanvas').offsetWidth")
    if len(кор) != 2 or кор[0]["в"] != кор[1]["в"] or abs(кор[0]["вы"] - кор[1]["вы"]) > 1:
        НАХОДКИ.append(f"{н} после расстановки не один ряд общей высоты: {кор}")
    for и, к_ in enumerate(кор):
        if abs(к_["ш"] / к_["вы"] - к_["д"]) / к_["д"] > 0.03:
            НАХОДКИ.append(f"{н} после расстановки снимок {и + 1} обрезан: коробка {к_['ш']}×{к_['вы']}, картинка {к_['д']:.2f}")
    if кор and max(к_["л"] + к_["ш"] for к_ in кор) > холст + 1:
        НАХОДКИ.append(f"{н} ряд вылезает за холст: {кор}, холст {холст}")
    # Печать спецификации.
    стр.evaluate("async () => { openPrintPreview(); await new Promise(r => setTimeout(r, 900)); }")
    печать = стр.evaluate("""() => [...document.querySelectorAll('#printDoc img')].filter(к => /образцы_приложения2/.test(decodeURIComponent(к.getAttribute('src') || '')))
      .map(к => { const q = к.getBoundingClientRect(); return { ш: q.width, вы: q.height, д: к.naturalWidth / к.naturalHeight }; })""")
    if len(печать) != 2:
        НАХОДКИ.append(f"{н} в печати снимков {len(печать)}, ждали два")
    for и, к_ in enumerate(печать):
        if к_["вы"] and abs(к_["ш"] / к_["вы"] - к_["д"]) / к_["д"] > 0.04:
            НАХОДКИ.append(f"{н} в печати снимок {и + 1} обрезан: {к_['ш']:.0f}×{к_['вы']:.0f}, картинка {к_['д']:.2f}")
    q = стр.evaluate("""() => { const к = [...document.querySelectorAll('#printDoc img')].find(к => /образцы_приложения2/.test(decodeURIComponent(к.getAttribute('src') || '')));
      if (!к) return null; к.parentElement.scrollIntoView({ block: 'center' }); const р = к.parentElement.getBoundingClientRect(); return { x: р.x, y: р.y, w: р.width, h: р.height }; }""")
    if q:
        стр.wait_for_timeout(300)
        q = стр.evaluate("""() => { const к = [...document.querySelectorAll('#printDoc img')].find(к => /образцы_приложения2/.test(decodeURIComponent(к.getAttribute('src') || ''))); const р = к.parentElement.getBoundingClientRect(); return { x: р.x, y: р.y, w: р.width, h: р.height }; }""")
        стр.screenshot(path=str(м.СНИМКИ / f"plan-layout-{ш}.png"),
                       clip={"x": max(0, q["x"] - 16), "y": max(0, q["y"] - 16), "width": min(ш, q["w"] + 32), "height": min(в, q["h"] + 32)})
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
    print("Чисто: снимки встают в своих пропорциях; «Авто-расстановка» ставит визуализацию и вертикальную "
          "планировку в один ряд общей высоты, ничего не обрезая; печать спецификации повторяет это — на 1440 и 390.")


if __name__ == "__main__":
    главная()
