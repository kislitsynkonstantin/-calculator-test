#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мини-окно в настоящих шрифтах: плашка журнала не теряет стрелку.

Константин 29.09.2026, снимком с телефона: «тут стрелочка не появляется» —
в плашке «209 действий · Открыть в журнале действий →» стрелка уходила за
правый край. Пробы мини-окна этого не видели: калькулятор берёт Geologica и
Unbounded с Google Fonts, а Chromium в контейнере туда не ходит и молча
рисует подменным шрифтом — другой ширины. Всё, что меряли пробы, было
измерено не тем шрифтом, которым это видит менеджер.

Эта проба отдаёт браузеру настоящие начертания (`шрифты_google.css` рядом —
те же Geologica и Unbounded, вшитые в base64) вместо запроса к Google Fonts,
убеждается, что они легли (ширина строки в фирменном шрифте не равна ширине
в подменном), и на 320, 360, 390 и 1440 px, днём и ночью, при 9, 209 и 300+
действиях держит:
  • стрелка и вся надпись «В журнал действий» внутри плашки, с полем
    не меньше её собственного отступа;
  • число действий видно целиком — всегда, при любом числе и на любой ширине
    (30.09.2026: «в журнале тут пропало» — прежде проба пропускала число,
    ушедшее за край плашки целиком, и оно пропадало при трёхзначном счёте);
  • ни одна подпись в шапке и вкладках мини-окна не обрезана.

    python3 check_preset_card_fonts.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ШРИФТЫ = (pathlib.Path(__file__).parent / "шрифты_google.css").read_text(encoding="utf-8")


def начать(бр, порт, ш, в, ночь):
    """То же, что check_preset_card.начать, но со шрифтами Google из файла."""
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async (ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); document.body.classList.toggle('dark', ночь);
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""", ночь)
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
    if стр.locator("#pcName").count():
        стр.locator("#pcName").press("Enter")
    elif стр.locator("#presetNameDialog input").count():
        стр.locator("#presetNameDialog input").press("Enter")
    стр.wait_for_timeout(2600)
    return стр, ошибки


ШРИФТ_ЛЁГ = """() => { const шир = сем => { const e = document.createElement('span'); e.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font-size:40px;font-family:' + сем; e.textContent = 'Открыть в журнале действий 209'; document.body.appendChild(e); const w = e.getBoundingClientRect().width; e.remove(); return w; };
  return { geologica: Math.abs(шир("'Geologica',monospace") - шир('monospace')) > .5, unbounded: Math.abs(шир("'Unbounded',monospace") - шир('monospace')) > .5 }; }"""

ЛЕНТА = """(n) => { const о = пресетКарточки(), я = _sbUser && _sbUser.id, s = [];
  for (let i = 0; i < n; i++) s.push({ id: 'e' + i, created_at: new Date(Date.now() - i * 600000).toISOString(), event_type: 'print', user_id: я,
    project_name: 'Проба', details: { obj: 'Проба', rows: [{ k: 'Шаблон', a: '', b: 'blank' }], presetCode: о.код } });
  _журналПресета = { код: о.код, события: s, ошибка: '', грузится: false, когда: Date.now() };
  _пкВкладка = 'l'; заполнитьКарточкуЗначка(); }"""

ПЛАШКА = """() => { const п = document.querySelector('#presetChipCard .pc-lg-plate'); if (!п) return null;
  const r = п.getBoundingClientRect(), cs = getComputedStyle(п), пр = parseFloat(cs.paddingRight), пл = parseFloat(cs.paddingLeft);
  const внутри = (э) => { const d = document.createRange(); d.selectNodeContents(э); return [...d.getClientRects()].filter(x => x.width); };
  const ст = п.querySelector('.pc-lg-ar'), сс = п.querySelector('.pc-lg-pl'), чс = п.querySelector('.pc-lg-pn');
  const a = ст.getBoundingClientRect();
  const чr = чс && чс.getBoundingClientRect();
  const чВидно = чс && getComputedStyle(чс).display !== 'none' && чr.width > 0 && чr.top < r.bottom - 1 && чr.bottom > r.top + 1;
  const чСрезано = чВидно && (чr.top < r.top - .5 || чr.bottom > r.bottom + .5);
  return { стрелка_справа: Math.round((r.right - пр) - a.right), стрелка_видна: a.width > 0,
    ссылка_обрезана: внутри(сс).some(x => x.right > r.right - пр + .5 || x.left < r.left + пл - .5) || сс.scrollWidth > сс.clientWidth + .5,
    число: чВидно ? чс.textContent : null, число_обрезано: чВидно && (чСрезано || чс.scrollWidth > чс.clientWidth + .5 || внутри(чс).some(x => x.left < r.left + пл - .5 || x.right > a.left)),
    текст: п.innerText.replace(/\\s+/g, ' ') }; }"""

ПОДПИСИ = """() => { const н = [];
  // Текст меряется диапазоном: scrollWidth считает и невидимое поле нажатия (::before) вкладки.
  document.querySelectorAll('#presetChipCard .pc-tab, #presetChipCard .pc-k, #presetChipCard .pc-nm').forEach(э => { const b = э.getBoundingClientRect(), d = document.createRange(); d.selectNodeContents(э);
    if ([...d.getClientRects()].some(x => x.width && (x.right > b.right + .5 || x.left < b.left - .5))) н.push(э.textContent.trim().slice(0, 30)); });
  const вк = [...document.querySelectorAll('#presetChipCard .pc-tab')], ряд = document.querySelector('#presetChipCard .pc-tabs');
  if (ряд && вк.length) { const R = ряд.getBoundingClientRect().right; вк.forEach(в => { if (в.getBoundingClientRect().right > R + .5) н.push('вкладка за краем: ' + в.textContent.trim()); }); }
  return н; }"""


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = начать(бр, порт, ш, в, ночь)
    лёг = стр.evaluate(ШРИФТ_ЛЁГ)
    if not all(лёг.values()):
        НАХОДКИ.append(f"{н} настоящие шрифты не легли ({лёг}) — проба мерила бы подменным"); стр.close(); return
    if not стр.evaluate("() => activePresetId"):
        НАХОДКИ.append(f"{н} пресет не сохранился"); стр.close(); return
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    for n in (9, 209, 305):
        стр.evaluate(ЛЕНТА, n)
        # Мышь уводится с плашки: наведение сдвигает стрелку на 3 px — это движение, а не вёрстка.
        стр.mouse.move(2, 2); стр.wait_for_timeout(300)
        п = стр.evaluate(ПЛАШКА)
        if п is None:
            НАХОДКИ.append(f"{н} {n} действий: плашки «Открыть в журнале действий» нет"); continue
        if not п["стрелка_видна"] or п["стрелка_справа"] < 0:
            НАХОДКИ.append(f"{н} {n} действий: стрелка за краем плашки на {-п['стрелка_справа']} px — «{п['текст']}»")
        if п["ссылка_обрезана"]:
            НАХОДКИ.append(f"{н} {n} действий: «В журнал действий» обрезано — «{п['текст']}»")
        if not п["число"] or "действ" not in п["число"]:
            НАХОДКИ.append(f"{н} {n} действий: числа действий в плашке не видно — «{п['текст']}»")
        if п["число_обрезано"]:
            НАХОДКИ.append(f"{н} {n} действий: число действий обрезано — «{п['число']}»")
        if ш == 390 and n == 209:
            стр.screenshot(path=str(м.СНИМКИ / f"card-fonts-{ш}{'-n' if ночь else ''}.png"))
    for х in стр.evaluate(ПОДПИСИ):
        НАХОДКИ.append(f"{н} обрезана подпись мини-окна: {х}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((320, 700), (360, 780), (390, 844), (1440, 900)):
                for ночь in (False, True):
                    прогон(бр, порт, ш, в, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в настоящих Geologica и Unbounded плашка журнала держит стрелку и надпись внутри, число действий "
          "видно всегда и целиком, подписи мини-окна не обрезаны — на 320, 360, 390 и 1440, днём и ночью, при 9, 209 и 300+ действиях.")


if __name__ == "__main__":
    главная()
