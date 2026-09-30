#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF проекта: окно выбора перед холстом, а не стопка из двадцати снимков.

Константин 30.09.2026, снимком холста с 21 снимком стопкой: «когда много
прилетает, чтобы память не забивали. Потом удаляю. Ещё неудобно выбирать,
когда нужно в стороны отложить». Всё найденное в PDF ложилось на холст со
сдвигом 20 px и уходило в хранилище, лишнее он растаскивал и удалял.

Проба на 1440 и 390 (день и ночь, настоящие шрифты) подменяет разбор PDF:
три вида и четыре листа планировок («План фундамента», «План 1 этажа»,
«План 2 этажа», «План кровли») — и держит:
  • открывается окно выбора; отмечены два первых вида и «План 1 этажа»,
    на кнопке «Добавить · 3»;
  • окно в пределах экрана, без прокрутки вбок, кнопки внизу видны и не
    меньше 40 px, плитки не налезают друг на друга; на 390 — две колонки;
  • нажатие ставит и снимает отметку, счёт на кнопке следует за ней; ничего
    не отмечено — кнопка выключена;
  • «Добавить» кладёт на холст ровно отмеченное (виды, затем планировки), и
    снимки стоят рядами, не налезая друг на друга;
  • «Отмена», Esc и нажатие мимо окна ничего не кладут;
  • на холсте уже был снимок — он не сдвигается, новые встают под ним;
  • два вида и одна планировка — окна нет, всё ложится сразу.

    python3 check_pdf_pick.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ШРИФТЫ = (pathlib.Path(__file__).parent / "шрифты_google.css").read_text(encoding="utf-8")
ВИЗ = "/scratchpad/probes/образцы_приложения2/визуализация.jpg"
ПЛАН = "/scratchpad/probes/образцы_приложения2/планировка.png"
ФОТО = "/scratchpad/probes/образцы_приложения2/фото_4x3.jpg"


class СоШрифтами:
    """Страница с настоящими Geologica и Unbounded вместо системного шрифта."""
    def __init__(self, бр):
        self.бр = бр

    def new_page(self, **кв):
        стр = self.бр.new_page(**кв)
        стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
        стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
        return стр


ПОДМЕНА = """([виз, план, фото, много]) => {
  canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
  const б = document.getElementById('btnCollapseImageCard'); if (б && б.classList.contains('collapsed')) toggleImageCard();
  window.canvasCompress = async (s) => s;
  const виды = (много ? [виз + '?1', фото + '?2', виз + '?3'] : [виз + '?1', фото + '?2']).map((src, и) => ({ src, тип: 'вид', подпись: 'Лист ' + (и + 2) }));
  const планы = (много ? ['План фундамента', 'План 1 этажа', 'План 2 этажа', 'План кровли'] : ['План 1 этажа'])
    .map((п, и) => ({ src: план + '?п' + и, тип: 'план', подпись: п }));
  window.разобратьPdf = async () => ({ виды, планы });
}"""
ОТКРЫТЬ = "() => { window.__пдф = canvasLoadPdf(new File(['%PDF'], 'проект.pdf', { type: 'application/pdf' })); }"
ОКНО = """() => { const о = document.getElementById('pdfPick'); if (!о) return null;
  const б = о.querySelector('.pdfp-box').getBoundingClientRect(), тело = о.querySelector('.pdfp-body');
  const пл = [...о.querySelectorAll('.pdfp-tile')].map(п => { const р = п.getBoundingClientRect(); return { x: р.x, y: р.y, ш: р.width, в: р.height,
    да: п.getAttribute('aria-pressed') === 'true', подпись: п.querySelector('.pdfp-cap').textContent }; });
  const кн = [...о.querySelectorAll('.pdfp-foot button')].map(к => { const р = к.getBoundingClientRect(); return { т: к.textContent.trim(), выкл: к.disabled, x: р.x, y: р.y, ш: р.width, в: р.height }; });
  return { коробка: { x: б.x, y: б.y, ш: б.width, в: б.height }, вбок: тело.scrollWidth > тело.clientWidth + 1 || document.documentElement.scrollWidth > innerWidth + 1,
    пл, кн, экран: { ш: innerWidth, в: innerHeight } }; }"""
ХОЛСТ = """() => [...document.querySelectorAll('#imageCanvas .canvas-img-item')].map(э => ({ src: decodeURIComponent(э.querySelector('img').getAttribute('src')).replace(/^.*образцы_приложения2\\//, ''),
  x: э.offsetLeft, y: э.offsetTop, ш: э.offsetWidth, в: э.offsetHeight }))"""


def налезают(коробки):
    for и, а in enumerate(коробки):
        for б in коробки[и + 1:]:
            if а["x"] < б["x"] + б["ш"] - 1 and б["x"] < а["x"] + а["ш"] - 1 and а["y"] < б["y"] + б["в"] - 1 and б["y"] < а["y"] + а["в"] - 1:
                return (а, б)
    return None


def ждать_окно(стр):
    for _ in range(40):
        if стр.evaluate("() => !!document.getElementById('pdfPick')"):
            break
        стр.wait_for_timeout(100)
    стр.wait_for_timeout(400)


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = к.начать(СоШрифтами(бр), порт, ш, в, ночь)
    шрифт = стр.evaluate("""async () => { await document.fonts.ready; const с = document.createElement('span'); с.textContent = 'Что взять из PDF';
      document.body.appendChild(с); с.style.font = '700 20px Unbounded'; const а = с.offsetWidth; с.style.font = '700 20px monospace'; const б = с.offsetWidth; с.remove(); return а !== б; }""")
    if not шрифт:
        НАХОДКИ.append(f"{н} настоящий шрифт не лёг — ширины надписей мерены подменным")

    # 1. Много всего — окно выбора с отметками по умолчанию.
    стр.evaluate(ПОДМЕНА, [ВИЗ, ПЛАН, ФОТО, True])
    стр.evaluate(ОТКРЫТЬ); ждать_окно(стр)
    о = стр.evaluate(ОКНО)
    if not о:
        НАХОДКИ.append(f"{н} окно выбора не открылось")
        стр.close(); return
    отмечены = [п["подпись"] for п in о["пл"] if п["да"]]
    if len(о["пл"]) != 7 or отмечены != ["Лист 2", "Лист 3", "План 1 этажа"]:
        НАХОДКИ.append(f"{н} ждали 7 плиток и отмеченные два первых вида и «План 1 этажа», есть {len(о['пл'])}: {отмечены}")
    ок = next((к_ for к_ in о["кн"] if "Добавить" in к_["т"] or "Ничего" in к_["т"]), None)
    if not ок or ок["т"] != "Добавить · 3":
        НАХОДКИ.append(f"{н} на кнопке ждали «Добавить · 3», есть {ок and ок['т']}")
    б, э = о["коробка"], о["экран"]
    if б["x"] < 0 or б["y"] < 0 or б["x"] + б["ш"] > э["ш"] + 1 or б["y"] + б["в"] > э["в"] + 1:
        НАХОДКИ.append(f"{н} окно выходит за экран: {б}, экран {э}")
    if о["вбок"]:
        НАХОДКИ.append(f"{н} в окне прокрутка вбок")
    for к_ in о["кн"]:
        if к_["в"] < 40 or к_["y"] + к_["в"] > э["в"] + 1:
            НАХОДКИ.append(f"{н} кнопка «{к_['т']}» мала или за краем: {к_}")
    п = налезают(о["пл"])
    if п:
        НАХОДКИ.append(f"{н} плитки налезают: {п}")
    колонки = len({round(п_["x"]) for п_ in о["пл"]})
    if ш == 390 and колонки != 2:
        НАХОДКИ.append(f"{н} на телефоне ждали две колонки плиток, есть {колонки}")
    стр.screenshot(path=str(м.СНИМКИ / f"pdf-pick-{ш}{'-ночь' if ночь else ''}.png"))

    # 2. Отметки: снять первый вид, отметить «План кровли»; снять всё — кнопка выключена.
    плитки = стр.locator("#pdfPick .pdfp-tile")
    плитки.nth(0).click(); плитки.nth(6).click(); стр.wait_for_timeout(150)
    о = стр.evaluate(ОКНО)
    if [п_["подпись"] for п_ in о["пл"] if п_["да"]] != ["Лист 3", "План 1 этажа", "План кровли"]:
        НАХОДКИ.append(f"{н} нажатие не переставило отметку: {[п_['подпись'] for п_ in о['пл'] if п_['да']]}")
    for и in (1, 4, 6):
        плитки.nth(и).click()
    стр.wait_for_timeout(150)
    о = стр.evaluate(ОКНО)
    ок = next(к_ for к_ in о["кн"] if "Отмена" not in к_["т"])
    if not ок["выкл"]:
        НАХОДКИ.append(f"{н} ничего не отмечено, а кнопка добавления нажимается: {ок}")
    for и in (1, 4, 6):
        плитки.nth(и).click()
    стр.wait_for_timeout(150)

    # 3. «Добавить» — ровно отмеченное, рядами.
    стр.locator("#pdfPick .pdfp-ok").click()
    стр.evaluate("async () => { await window.__пдф; await new Promise(r => setTimeout(r, 400)); }")
    х = стр.evaluate(ХОЛСТ)
    if [с["src"] for с in х] != ["фото_4x3.jpg?2", "планировка.png?п1", "планировка.png?п3"]:
        НАХОДКИ.append(f"{н} на холст легло не отмеченное: {[с['src'] for с in х]}")
    п = налезают(х)
    if п:
        НАХОДКИ.append(f"{н} снимки на холсте налезают: {п}")
    if стр.evaluate("() => !!document.getElementById('pdfPick')"):
        НАХОДКИ.append(f"{н} окно не закрылось после «Добавить»")

    # 4. Уже есть снимок — он на месте, новые под ним; «Отмена», Esc, мимо окна — ничего.
    стр.evaluate(ПОДМЕНА, [ВИЗ, ПЛАН, ФОТО, True])
    стр.evaluate("(s) => { const и = canvasAddImageAt(s, 30, 20, 300, 200); }", ФОТО)
    стр.wait_for_timeout(300)
    for как in ("отмена", "esc", "мимо"):
        стр.evaluate(ОТКРЫТЬ); ждать_окно(стр)
        if как == "отмена":
            стр.locator("#pdfPick .pdfp-no").click()
        elif как == "esc":
            стр.keyboard.press("Escape")
        else:
            стр.mouse.click(3, 3)
        стр.evaluate("async () => { await window.__пдф; }")
        if стр.evaluate("() => !!document.getElementById('pdfPick')") or len(стр.evaluate(ХОЛСТ)) != 1:
            НАХОДКИ.append(f"{н} {как}: окно не закрылось или что-то легло на холст: {стр.evaluate(ХОЛСТ)}")
    стр.evaluate(ОТКРЫТЬ); ждать_окно(стр)
    стр.locator("#pdfPick .pdfp-ok").click()
    стр.evaluate("async () => { await window.__пдф; await new Promise(r => setTimeout(r, 400)); }")
    х = стр.evaluate(ХОЛСТ)
    if not х or (х[0]["x"], х[0]["y"], х[0]["ш"], х[0]["в"]) != (30, 20, 300, 200):
        НАХОДКИ.append(f"{н} прежний снимок сдвинулся: {х[:1]}")
    if len(х) != 4 or any(с["y"] < 20 + 200 for с in х[1:]) or налезают(х):
        НАХОДКИ.append(f"{н} новые снимки не встали под прежним рядами: {х}")

    # 5. Два вида и одна планировка — окна нет, всё сразу.
    стр.evaluate(ПОДМЕНА, [ВИЗ, ПЛАН, ФОТО, False])
    стр.evaluate(ОТКРЫТЬ)
    стр.evaluate("async () => { await window.__пдф; await new Promise(r => setTimeout(r, 400)); }")
    х = стр.evaluate(ХОЛСТ)
    if стр.evaluate("() => !!document.getElementById('pdfPick')") or len(х) != 3 or налезают(х):
        НАХОДКИ.append(f"{н} без выбора ждали три снимка сразу рядами и без окна: {х}")
    for о_ in [о_ for о_ in ошибки if "supabase.co" not in о_][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о_[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 1440, 900, False)
            прогон(бр, порт, 390, 844, False)
            прогон(бр, порт, 1440, 900, True)
            прогон(бр, порт, 390, 844, True)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: из PDF с выбором — окно с плитками, отмечены два вида и план 1 этажа; отметки ставятся и снимаются; "
          "на холст ложится ровно отмеченное и рядами; отмена, Esc и нажатие мимо ничего не кладут; прежний снимок на месте; "
          "без выбора окна нет — на 1440 и 390, день и ночь.")


if __name__ == "__main__":
    главная()
