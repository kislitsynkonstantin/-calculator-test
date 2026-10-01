#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Метка вида на снимке блока «Визуализация и планировка».

Константин 01.10.2026, снимком блока с тремя снимками: «тут поставь метки
автоопределения „Визуализация“ и „Планировка“. И если вдруг система ошибётся,
чтобы можно было поменять менеджеру вручную».

Проба на 390 и 1440, в «Бланке» и «Модерне», днём и ночью, держит:
  • на каждом снимке бейдж: два фото — «Вид», чертёж — «План» (01.10.2026,
    вариант 01 макета canvas-kind-label-v1: залитое слово и стрелки рядом),
    ровно как их разложит Приложение № 2;
  • метка в пределах снимка, не налезает на крестик, высотой 26 px, текст
    читается на подложке не хуже 4,5:1;
  • нажатие по метке меняет вид («Вид» → «План»), снимок при
    этом не сдвинулся и не удалился; Приложение № 2 кладёт его по метке;
    нажатие ещё раз — обратно;
  • выбор менеджера живёт в расчёте: kind в collectState().canvasImages;
  • в печати метки нет.

    python3 check_canvas_kind_label.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ФОТО = "/scratchpad/probes/образцы_приложения2/фото_4x3.jpg"
ПЛАН = "/scratchpad/probes/образцы_приложения2/планировка.png"

МЕТКИ = """() => [...document.querySelectorAll('#imageCanvas .canvas-img-item')].map(э => {
  const м = э.querySelector('.img-kind'), х = э.querySelector('.img-delete'), r = э.getBoundingClientRect();
  if (!м) return { нет: true };
  const q = м.getBoundingClientRect(), д = х.getBoundingClientRect(), ст = getComputedStyle(м);
  const цв = s => s.match(/[\d.]+/g).map(Number);
  const я = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= .03928 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  // Слово стоит в залитой плашке (.img-kind-t), если она есть, — контраст меряется в ней.
  const сл = м.querySelector('.img-kind-t'), сс = сл && getComputedStyle(сл).backgroundColor !== 'rgba(0, 0, 0, 0)' ? getComputedStyle(сл) : ст;
  const ф = цв(сс.backgroundColor), а = ф[3] == null ? 1 : ф[3], под = document.body.classList.contains('dark') ? 0 : 255;
  const фон = ф.slice(0, 3).map(x => x * а + под * (1 - а)), т = цв(сс.color);
  const L1 = я(т), L2 = я(фон), контраст = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
  return { т: (м.textContent || '').trim(), контраст: Math.round(контраст * 10) / 10, видна: ст.display !== 'none' && q.width > 0, выс: Math.round(q.height),
    внутри: q.left >= r.left - .5 && q.top >= r.top - .5 && q.right <= r.right + .5, зазор: д.width ? Math.round(д.left - q.right) : 99,
    поз: [э.style.left, э.style.top], kind: э.dataset.kind || '' }; })"""


def прогон(бр, порт, ш, в, ночь, тема):
    н = f"[{ш} {тема}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(бр, порт, ш, в, ночь)
    if тема == "modern":
        стр.evaluate("() => applyUiStyle('modern', false)")
    стр.evaluate("""async (s) => { canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
      const б = document.getElementById('btnCollapseImageCard'); if (б && б.classList.contains('collapsed')) toggleImageCard();
      for (const src of s) canvasAddImage(src); await new Promise(r => setTimeout(r, 900)); canvasAutoCenter(); await new Promise(r => setTimeout(r, 300));
      try { закрытьКарточкуЗначка(); } catch (e) {}
      document.getElementById('imageCanvas').scrollIntoView({ block: 'center' }); }""", [ВИЗ, ФОТО, ПЛАН])
    стр.wait_for_timeout(600)
    м_ = стр.evaluate(МЕТКИ)
    # На компьютере крестик виден при наведении — проверить зазор и в этот миг.
    if ш == 1440:
        стр.locator("#imageCanvas .canvas-img-item").nth(0).hover(); стр.wait_for_timeout(200)
        х = стр.evaluate(МЕТКИ)[0]
        if х.get("зазор", 99) < 4:
            НАХОДКИ.append(f"{н} при наведении метка налезает на крестик: {х}")
    # Контраст слова в бейдже — во всех цветовых схемах.
    if ш == 1440 and тема == "blank":
        плохие = стр.evaluate("""(М) => { const was = текущийТон(); const о = [];
          for (const т of Object.keys(ТОНЫ_ПОДПИСИ)) { applyTone(т, false); const к = (eval(М)())[0]; if (к && к.контраст < 4.5) о.push(т + ' ' + к.контраст); }
          applyTone(was || 'bmsk', false); return о; }""", МЕТКИ)
        if плохие:
            НАХОДКИ.append(f"{н} контраст слова в бейдже ниже 4,5:1 в схемах: {плохие}")
    тексты = [x.get("т") for x in м_]
    if тексты != ["Вид", "Вид", "План"]:
        НАХОДКИ.append(f"{н} метки {тексты}, ждали «Вид, Вид, План»")
    for i, x in enumerate(м_):
        if x.get("нет") or not x["видна"] or not x["внутри"] or x["выс"] != 26 or x["зазор"] < 4 or x["контраст"] < 4.5:
            НАХОДКИ.append(f"{н} метка снимка {i + 1}: {x}")
    if ш == 1440 and not ночь and тема == "blank":
        стр.screenshot(path=str(м.СНИМКИ / "canvas-kind-1440.png"))
    if ш == 390 and ночь and тема == "blank":
        стр.screenshot(path=str(м.СНИМКИ / "canvas-kind-390.png"))
    if тексты and тексты[0] == "Вид":
        стр.locator("#imageCanvas .canvas-img-item").nth(0).locator(".img-kind").click(); стр.wait_for_timeout(500)
        после = стр.evaluate(МЕТКИ)
        р = стр.evaluate("async () => { const { виз, план } = await разложитьСнимки(); return { виз: виз.length, план: план.map(s => s.split('/').pop()) }; }")
        if после[0]["т"] != "План" or после[0]["kind"] != "план" or после[0]["поз"] != м_[0]["поз"] or len(после) != 3:
            НАХОДКИ.append(f"{н} нажатие по метке: {после[0]}, снимков {len(после)}")
        if "визуализация.jpg" not in р["план"]:
            НАХОДКИ.append(f"{н} Приложение № 2 не идёт за меткой: {р}")
        вид = стр.evaluate("() => (collectState().canvasImages || []).map(с => с.kind || '')")
        if вид[:1] != ["план"]:
            НАХОДКИ.append(f"{н} выбор не в расчёте: {вид}")
        стр.locator("#imageCanvas .canvas-img-item").nth(0).locator(".img-kind").click(); стр.wait_for_timeout(500)
        if стр.evaluate(МЕТКИ)[0]["т"] != "Вид":
            НАХОДКИ.append(f"{н} второе нажатие не вернуло «Вид»")
    стр.emulate_media(media="print")
    if стр.evaluate("() => [...document.querySelectorAll('.img-kind')].some(м => getComputedStyle(м).display !== 'none')"):
        НАХОДКИ.append(f"{н} метка видна в печати")
    стр.emulate_media(media="screen")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                for ночь in (False, True):
                    for тема in ("blank", "modern"):
                        прогон(СоШрифтами(бр), порт, ш, в, ночь, тема)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: на снимках бейджи «Вид» и «План» со стрелками — как их разложит Приложение № 2; нажатие меняет вид, "
          "снимок не сдвигается, приложение идёт за меткой, выбор живёт в расчёте, в печати меток нет — на 390 и 1440, "
          "в «Бланке» и «Модерне», днём и ночью.")


if __name__ == "__main__":
    главная()
