#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба макета стекла glass-v2.html — настоящими нажатиями, на 390 / 768 / 1440.

Держит: шрифты — фирменные, а не подменные (ширина строки против запасного);
нет ошибок страницы и прокрутки вбок; переключатели меняют признаки на body;
галочка «Стекло» в «Настройках» есть и работает; каждое из пяти окон
открывается кнопкой макета и кнопкой панели калькулятора, лежит в пределах
экрана и закрывается крестиком; при прокрутке панель кнопок прилипает, а
полоска итога выезжает; кнопки макета не меньше 32 px.
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import harness

ФАЙЛ = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "glass-v2.html").resolve()
СНИМКИ = pathlib.Path(__file__).parent / "mk-shots"; СНИМКИ.mkdir(exist_ok=True)
НАХОДКИ = []
ОКНА = {"presets": ("presetPanel", "#presetsBtn"), "plan": ("paymentPlanOverlay", "#paymentPlanBtn"),
        "settings": ("settingsPanel", "#settingsBtn"), "log": ("actionLogOverlay", "#actionLogBtn"),
        "print": ("printOverlay", "#printPreviewWrap")}
ПАНЕЛЬ_ОКНА = {"presets": "#presetBox", "plan": "#ppPanel", "settings": "#settingsBox", "log": "#actionLogPanel",
               "print": "#printOverlay > div"}


def плохо(т):
    НАХОДКИ.append(т)


def главная():
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=harness.хром(), args=harness.АРГИ)
        for ш in (390, 768, 1440):
            н = f"[{ш}]"
            стр = бр.new_page(viewport={"width": ш, "height": 844 if ш < 500 else 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.goto(ФАЙЛ.as_uri()); стр.wait_for_timeout(900)
            # шрифты: ширина в фирменном против запасного
            ш_ = стр.evaluate("""() => { const м = (ф) => { const s = document.createElement('span'); s.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font-size:40px;font-family:' + ф; s.textContent = 'Спецификация 4 675 119 ₽'; document.body.appendChild(s); const w = s.getBoundingClientRect().width; s.remove(); return w; };
              return { geo: м("'Geologica', monospace"), geoFb: м('monospace'), unb: м("'Unbounded', monospace"), unbFb: м('monospace'), fontsOk: document.fonts.status }; }""")
            if abs(ш_["geo"] - ш_["geoFb"]) < 1 or abs(ш_["unb"] - ш_["unbFb"]) < 1:
                плохо(f"{н} шрифт подменён: {ш_}")
            if ш == 390:
                стр.screenshot(path=str(СНИМКИ / f"{ш}-intro.png"))
            # кнопки макета
            мелкие = стр.evaluate("""() => [...document.querySelectorAll('.mk button, .mk-sw')].map(b => [b.textContent.trim(), Math.round(b.getBoundingClientRect().height)]).filter(([т, h]) => h < 32)""")
            if мелкие:
                плохо(f"{н} кнопки макета ниже 32 px: {мелкие}")
            ширина = стр.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            if ширина > 1:
                плохо(f"{н} страница шире окна на {ширина} px")
            # переключатели
            for сел, признак, ждём in [(".mk-seg[data-k=dark] button[data-v='1']", "dark", True), (".mk-seg[data-k=ui] button[data-v='light']", "ui-light", True),
                                       (".mk-seg[data-k=ui] button[data-v='blank']", "ui-blank", True), (".mk-seg[data-k=dark] button[data-v='0']", "dark", False)]:
                стр.click(сел); стр.wait_for_timeout(150)
                if стр.evaluate(f"() => document.body.classList.contains('{признак}')") != ждём:
                    плохо(f"{н} {сел} не поставил {признак}={ждём}")
            стр.click(".mk-seg[data-k=tone] button[data-v='bmsk']"); стр.wait_for_timeout(150)
            if стр.evaluate("() => document.documentElement.dataset.tone") != "bmsk":
                плохо(f"{н} цвет не переключился")
            стр.click(".mk-seg[data-k=tone] button[data-v='teal']")
            стр.click(".mk-sw"); стр.wait_for_timeout(150)
            if стр.evaluate("() => document.body.classList.contains('ui-glass')"):
                плохо(f"{н} галочка «Стекло» в шапке макета не выключила стекло")
            стр.click(".mk-sw"); стр.wait_for_timeout(150)
            # окна
            for имя, (ид, кнопка) in ОКНА.items():
                for путь in ("макет", "панель"):
                    стр.evaluate("() => window.scrollTo(0, 0)"); стр.wait_for_timeout(150)
                    if путь == "макет":
                        стр.click(f".mk-wins button[data-w={имя}]")
                    else:
                        стр.locator(кнопка).first.click()
                    стр.wait_for_timeout(350)
                    р = стр.evaluate(f"""() => {{ const o = document.getElementById('{ид}'); const p = document.querySelector('{ПАНЕЛЬ_ОКНА[имя]}');
                      const r = p ? p.getBoundingClientRect() : null;
                      return {{ видно: getComputedStyle(o).display !== 'none', л: r && Math.round(r.left), п: r && Math.round(r.right), в: r && Math.round(r.top), ширина: innerWidth,
                               вбок: document.documentElement.scrollWidth - innerWidth }}; }}""")
                    if not р["видно"]:
                        плохо(f"{н} окно «{имя}» не открылось ({путь})"); continue
                    if р["л"] is not None and (р["л"] < -1 or р["п"] > р["ширина"] + 1):
                        плохо(f"{н} окно «{имя}» за краем экрана: {р}")
                    if путь == "макет":
                        стр.screenshot(path=str(СНИМКИ / f"{ш}-{имя}.png"))
                    if имя == "settings" and путь == "макет":
                        есть = стр.evaluate("() => !!document.getElementById('mkGlassToggle')")
                        if not есть:
                            плохо(f"{н} в «Настройках» нет галочки «Стекло»")
                        else:
                            стр.locator("#mkGlassRow .st-toggle").click(); стр.wait_for_timeout(150)
                            if стр.evaluate("() => document.body.classList.contains('ui-glass')"):
                                плохо(f"{н} галочка «Стекло» в «Настройках» не выключила стекло")
                            стр.screenshot(path=str(СНИМКИ / f"{ш}-settings-off.png"))
                            стр.locator("#mkGlassRow .st-toggle").click(); стр.wait_for_timeout(150)
                    # закрыть крестиком
                    х = стр.locator(f"#{ид} .ovl-x, #{ид} [aria-label='Закрыть']").first
                    if х.count():
                        х.click()
                    else:
                        стр.keyboard.press("Escape")
                    стр.wait_for_timeout(200)
                    if стр.evaluate(f"() => getComputedStyle(document.getElementById('{ид}')).display !== 'none'"):
                        плохо(f"{н} окно «{имя}» не закрылось крестиком")
                        стр.keyboard.press("Escape")
            # прокрутка
            стр.evaluate("() => { document.getElementById('optionSections').scrollIntoView(); window.scrollBy(0, 400); }"); стр.wait_for_timeout(400)
            пр = стр.evaluate("() => ({ липко: document.getElementById('headerBtns').classList.contains('sticky'), полоска: document.getElementById('totalStrip').classList.contains('on'), fab: document.getElementById('mkFab').classList.contains('on') })")
            if not all(пр.values()):
                плохо(f"{н} при прокрутке: {пр}")
            стр.screenshot(path=str(СНИМКИ / f"{ш}-spec.png"))
            if ошибки:
                плохо(f"{н} ошибки страницы: {ошибки[:3]}")
            print(н, "шрифты", {к: round(в) for к, в in ш_.items() if isinstance(в, float)}, "прокрутка", пр)
            стр.close()
        бр.close()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: шрифты свои, переключатели и галочка «Стекло» работают, пять окон открываются из макета и с панели, "
          "в пределах экрана, закрываются; панель прилипает, полоска итога выезжает; на 390, 768 и 1440.")


if __name__ == "__main__":
    главная()
