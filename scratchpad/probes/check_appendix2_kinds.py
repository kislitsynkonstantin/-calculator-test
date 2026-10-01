#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приложение № 2: виды не уходят в планировку.

Константин 01.10.2026, снимком Приложения № 2 с телефона: «тут смотри косяк:
определил как планировку визуализацию». В пресете три фото-вида, а лист
визуализации пустой и все три — на листах планировки. Safari на iPhone даёт
onload раньше, чем снимок расшифрован; drawImage рисует пустоту, и белый
бесцветный холст правило по пикселям читало как планировку.

Проба держит:
  • «Safari»: снимок рисуется только после decode() — три фото-вида, все три в
    визуализации, листа планировки со снимком нет;
  • «пустой холст»: снимок не рисуется вовсе — такие снимки «не прочитаны», а
    не «планировка»: виды на первом листе есть (два), последний — планировкой,
    как велит правило для непрочитанных;
  • вид из разбора PDF (data-kind) главнее пикселей: снимок визуализации,
    помеченный «план», идёт планировкой, и наоборот; пометка переживает
    collectState() → restoreState() и выгрузку в хранилище;
  • в собранном документе на первом листе столько видов, сколько ждали.

    python3 check_appendix2_kinds.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ПЛАН = "/scratchpad/probes/образцы_приложения2/планировка.png"
ФОТО = "/scratchpad/probes/образцы_приложения2/фото_4x3.jpg"

ОЧИСТИТЬ = """() => { canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
  if (typeof _видыКартинок !== 'undefined') _видыКартинок.clear(); }"""

SAFARI = """(всегдаПусто) => {
  window.__расшифровано = new WeakSet();
  if (!window.__былDraw) window.__былDraw = CanvasRenderingContext2D.prototype.drawImage;
  if (!window.__былDecode) window.__былDecode = HTMLImageElement.prototype.decode;
  HTMLImageElement.prototype.decode = function () { const я = this; return new Promise(r => setTimeout(() => { window.__расшифровано.add(я); r(); }, 40)); };
  CanvasRenderingContext2D.prototype.drawImage = function (img, ...а) {
    if (img instanceof HTMLImageElement && (всегдаПусто || !window.__расшифровано.has(img))) return;
    return window.__былDraw.call(this, img, ...а); }; }"""

ВЕРНУТЬ = """() => { if (window.__былDraw) CanvasRenderingContext2D.prototype.drawImage = window.__былDraw;
  if (window.__былDecode) HTMLImageElement.prototype.decode = window.__былDecode; }"""

РАЗЛОЖИТЬ = """async (снимки) => {
  for (const [src, вид] of снимки) { const ид = canvasAddImage(src); if (вид) document.getElementById(ид).dataset.kind = вид; }
  await new Promise(r => setTimeout(r, 500));
  const { виз, план } = await разложитьСнимки();
  const html = await собратьПриложение2();
  const первый = html.split('<section').filter(Boolean)[1] || '';
  return { виз, план, видовНаПервом: (первый.match(/class="fig fig--view"/g) || []).length, планов: (html.match(/class="fig fig--plan"/g) || []).length }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    # 1. Safari: рисует только расшифрованное.
    стр.evaluate(ОЧИСТИТЬ); стр.evaluate(SAFARI, False)
    р = стр.evaluate(РАЗЛОЖИТЬ, [[ВИЗ, ""], [ФОТО, ""], [ВИЗ + "?2", ""]])
    if len(р["виз"]) != 3 or р["план"] or р["видовНаПервом"] != 2 or р["планов"]:
        НАХОДКИ.append(f"{н} «Safari»: три фото-вида разложены не в визуализацию — виз {len(р['виз'])}, план {len(р['план'])}, "
                       f"видов на первом листе {р['видовНаПервом']}, снимков планировки {р['планов']}")
    # 2. Холст не рисуется вовсе — «не прочитано», а не «планировка».
    стр.evaluate(ОЧИСТИТЬ); стр.evaluate(SAFARI, True)
    р = стр.evaluate(РАЗЛОЖИТЬ, [[ВИЗ, ""], [ФОТО, ""], [ВИЗ + "?3", ""]])
    if len(р["виз"]) != 2 or len(р["план"]) != 1 or р["видовНаПервом"] != 2:
        НАХОДКИ.append(f"{н} «пустой холст»: ждали два вида и одну планировку, пришло виз {len(р['виз'])}, план {len(р['план'])}, "
                       f"видов на первом листе {р['видовНаПервом']}")
    стр.evaluate(ВЕРНУТЬ)
    # 3. Вид из разбора PDF главнее пикселей и переживает сохранение.
    стр.evaluate(ОЧИСТИТЬ)
    р = стр.evaluate(РАЗЛОЖИТЬ, [[ВИЗ, "план"], [ПЛАН, "вид"]])
    if not (р["виз"] and р["виз"][0].endswith("планировка.png") and р["план"] and р["план"][0].endswith("визуализация.jpg")):
        НАХОДКИ.append(f"{н} пометка из разбора PDF не главнее пикселей: виз {р['виз']}, план {р['план']}")
    сох = стр.evaluate("""async () => { const ст = collectState(); const виды = (ст.canvasImages || []).map(с => с.kind || '');
      canvasClearAll(); await new Promise(r => setTimeout(r, 100));
      await restoreCanvasFromUrls(ст.canvasImages.map(с => ({ url: с.src, left: с.left, top: с.top, width: с.width, height: с.height, kind: с.kind })));
      const после = [...document.querySelectorAll('#imageCanvas .canvas-img-item')].map(э => э.dataset.kind || '');
      const выгр = await uploadCanvasToStorage('проба', [{ src: 'https://example.ru/a.jpg', left: 0, top: 0, width: 1, height: 1, kind: 'план' }]);
      return { виды, после, выгр: (выгр[0] || {}).kind || '' }; }""")
    if сох["виды"] != ["план", "вид"] or сох["после"] != ["план", "вид"] or сох["выгр"] != "план":
        НАХОДКИ.append(f"{н} пометка вида не переживает сохранение: {сох}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                прогон(бр, порт, ш, в)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: снимок меряется после расшифровки — три фото-вида остаются визуализацией и в Safari; непрочитанный "
          "снимок не выдаётся за планировку; вид из разбора PDF главнее пикселей и переживает сохранение и выгрузку — "
          "на 390 и 1440.")


if __name__ == "__main__":
    главная()
