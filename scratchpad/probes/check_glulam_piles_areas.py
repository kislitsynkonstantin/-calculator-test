#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Клеёный брус, блок 1: сваи и вальмовая кровля из каркаса, пустые площади.

Константин 09.10.2026: «берём из каркаса цены и написание» и «подсвечивай,
что эти поля нужно заполнить». У бруса сваи считаются так же, как у каркаса,
— (тёплый контур + открытая + крытая терраса) × ставка по ступеням площади;
вальмовая кровля — 3 % цены средней толщины (160х185). Пустая площадь фасада
или кровли у открытого проекта помечена, опция, которой площади не хватает,
вместо прочерка пишет «укажите площадь» и ведёт к пустому полю.

Цены и площади здесь выдуманные: настоящие в публичный репозиторий не кладутся.
Проба нажимает и смотрит на цену и фокус, а не на разметку:

  • винтовые и забивные сваи бруса — по площадям проекта и ступеням каркаса;
    число из прайса правило не берёт; у проекта без площадей цены нет — поле
    «введите сумму»;
  • вальмовая кровля — 3 % цены 160х185 при любой толщине;
  • пустые поля площадей помечены, под ними подсказка; заполнили одно —
    пометка ушла с него, заполнили оба — ушла и подсказка;
  • покраска без площади фасада пишет «укажите площадь»; нажатие ставит
    фокус в поле фасада и галочку не ставит; вписали площадь — у опции цена;
    опция кровли ведёт к полю кровли;
  • у каркаса пометок нет, а опция без площади по-прежнему пишет прочерк;
  • вид: подсказка не касается полей, ссылка не вылезает за строку, площадь
    нажатия ссылки не меньше 32 px, переполнения нет — на 390, 768 и 1440.

    python3 check_glulam_piles_areas.py
"""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
КАДРЫ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp/kb_block1")
КАДРЫ.mkdir(parents=True, exist_ok=True)
БАЗА = г.БАЗА                      # цена 160х185 у пробного проекта
ТЁПЛЫЙ, ОТКР, КРЫТ = 50, 10, 20    # 80 м² — ступень «до 80»: 3300 и 3800
ЖДЁМ = {"kb_f1": 80 * 3300, "kb_f5": 80 * 3800, "kb_r20": round(БАЗА * 0.03)}


def опция(ид, раздел, имя, formula=None, status=None):
    return {"product": "glulam", "option_id": ид, "name": имя, "section": раздел, "included": False,
            "price": None, "formula": formula, "status": status, "sort": 300}


def таблицы():
    т = г.таблицы()
    for п in т["pricing_projects"]:
        if п["product"] == "glulam":
            п.update(warm=ТЁПЛЫЙ, open_area=ОТКР, closed_area=КРЫТ)
    т["pricing_projects"].append(dict(т["pricing_projects"][-1], slug="Брус без площадей", name="Брус без площадей",
                                      warm=None, open_area=None, closed_area=None, sort=2))
    покраска = {"coef": 2000, "mult": 1.1, "areaSrc": "paint", "areaMult": 1.25, "addonInside": 10000,
                "defaultMargin": 0.3}
    кровля = {"coef": 1500, "areaSrc": "roof", "defaultMargin": 0.3}
    т["pricing_options"] += [
        опция("kb_f1", "foundation", "Свайно-винтовой фундамент без обвязки"),
        опция("kb_f5", "foundation", "Забивные сваи"),
        опция("kb_r20", "roof", "Вальмовая кровля"),
        опция("kb_p17", "paint", "Покраска клеёного бруса", покраска, "formula"),
        опция("kb_rf", "roof", "Проба кровли по площади", кровля, "formula"),
    ]
    # Число в прайсе нарочно другое: правило должно его перекрыть.
    т["pricing_matrix"] += [{"product": "glulam", "project_slug": "Брус проба 6×6", "option_id": о, "price": 1}
                            for о in ("kb_f1", "kb_f5", "kb_r20")]
    # Каркасу — опция покраски с формулой без площадей: прочерк остаётся.
    т["pricing_options"].append({"product": "frame", "option_id": "p_proba", "name": "Покраска каркаса проба",
                                 "section": "paint", "included": False, "price": None, "status": "formula",
                                 "formula": покраска, "sort": 300})
    return т


ЦЕНЫ = """() => { const ц = id => { const э = document.getElementById('optprice_' + id);
    return э ? э.textContent.trim() : null; };
  return { f1: getOptPrice(getOpt('kb_f1')), f5: getOptPrice(getOpt('kb_f5')), r20: getOptPrice(getOpt('kb_r20')),
           тf1: ц('kb_f1'), тp17: ц('kb_p17'), тrf: ц('kb_rf'),
           пор: !!document.getElementById('por_kb_f1') }; }"""

ПОМЕТКИ = """() => { const п = ид => { const э = document.getElementById(ид); return !!(э && э.closest('.field').classList.contains('kb-area-need')); };
  const х = document.querySelector('#kbAreasWrap .kb-areas-hint > div');
  return { фасад: п('kbAreaFasad'), кровля: п('kbAreaRoof'), подсказка: !!(х && х.getClientRects().length) }; }"""

ВИД = """() => { const н = []; const ш = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth > ш + 1) н.push('прокрутка вбок ' + document.documentElement.scrollWidth + ' > ' + ш);
  const х = document.querySelector('#kbAreasWrap .kb-areas-hint > div');
  const поля = [...document.querySelectorAll('#kbAreasWrap input')].map(и => и.getBoundingClientRect());
  if (х && х.getClientRects().length) {
    const р = х.getBoundingClientRect();
    const над = Math.max(...поля.map(п => п.bottom));
    if (р.top - над < 4) н.push('подсказка касается полей: зазор ' + Math.round(р.top - над) + ' px');
    if (р.right > ш) н.push('подсказка за краем');
    // Подсказка не прилипает к тому, что ниже.
    const ниже = [...document.querySelectorAll('#kbAreasWrap ~ *')].find(э => э.getClientRects().length);
    if (ниже && ниже.getBoundingClientRect().top - р.bottom < 4) н.push('подсказка касается блока ниже: ' + Math.round(ниже.getBoundingClientRect().top - р.bottom) + ' px');
  }
  document.querySelectorAll('.kb-need-area').forEach(к => {
    if (!к.getClientRects().length) return;
    const р = к.getBoundingClientRect(); const стр = к.closest('.opt-item').getBoundingClientRect();
    if (р.right > стр.right + 0.5 || р.left < стр.left - 0.5) н.push('ссылка вылезает за строку');
    const до = getComputedStyle(к, '::before');
    const выс = р.height - parseFloat(до.top) - parseFloat(до.bottom);
    if (выс < 32) н.push('площадь нажатия ссылки ' + Math.round(выс) + ' px');
  });
  return н; }"""


def открыть(бр, порт, ш, тема=None):
    к = бр.new_context(viewport={"width": ш, "height": 900})
    стр = к.new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async (тема) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      if (тема === 'dark') document.body.classList.add('dark');
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400)); }""", тема)
    return к, стр, ош


def проект(стр, имя):
    стр.evaluate("""async (имя) => { selectProjectOption(PROJECTS.findIndex(p => p[0] === имя));
      setThickness(1); calc(); await new Promise(r => setTimeout(r, 300)); }""", имя)


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    к, стр, ош = открыть(бр, порт, ш)
    проект(стр, "Брус проба 6×6")

    # Сваи и вальмовая кровля
    ц = стр.evaluate(ЦЕНЫ)
    for ключ, ид in (("f1", "kb_f1"), ("f5", "kb_f5"), ("r20", "kb_r20")):
        if ц[ключ] != ЖДЁМ[ид]:
            НАХОДКИ.append(f"{н} {ид}: цена {ц[ключ]}, ждали {ЖДЁМ[ид]}")
    for т in (0, 2):
        стр.evaluate(f"() => {{ setThickness({т}); calc(); }}")
        р = стр.evaluate("() => getOptPrice(getOpt('kb_r20'))")
        if р != ЖДЁМ["kb_r20"]:
            НАХОДКИ.append(f"{н} вальмовая кровля при толщине {т}: {р}, ждали {ЖДЁМ['kb_r20']}")
    стр.evaluate("() => { setThickness(1); calc(); }")

    # Пометка пустых площадей
    п = стр.evaluate(ПОМЕТКИ)
    if not (п["фасад"] and п["кровля"] and п["подсказка"]):
        НАХОДКИ.append(f"{н} открыт проект, площади пусты: пометки {п}")
    стр.screenshot(path=str(КАДРЫ / f"пусто_{ш}.png"), full_page=False,
                   clip={"x": 0, "y": max(0, стр.evaluate("() => document.getElementById('kbAreasWrap').getBoundingClientRect().top + scrollY") - 140),
                         "width": ш, "height": 420})
    for в in стр.evaluate(ВИД):
        НАХОДКИ.append(f"{н} вид, площади пусты: {в}")

    # «Укажите площадь»
    if ц["тp17"] != "укажите площадь":
        НАХОДКИ.append(f"{н} покраска без площади фасада пишет «{ц['тp17']}»")
    if ц["тrf"] != "укажите площадь":
        НАХОДКИ.append(f"{н} опция кровли без площади пишет «{ц['тrf']}»")
    for ид, поле in (("kb_p17", "kbAreaFasad"), ("kb_rf", "kbAreaRoof")):
        ссылка = стр.locator(f"#optprice_{ид} .kb-need-area")
        if not ссылка.count():
            continue            # прочерк вместо ссылки уже записан выше
        ссылка.scroll_into_view_if_needed()
        ссылка.click()
        стр.wait_for_timeout(700)
        ф = стр.evaluate(f"() => ({{ фокус: document.activeElement && document.activeElement.id, отм: !!checkedOptions.{ид} }})")
        if ф["фокус"] != поле or ф["отм"]:
            НАХОДКИ.append(f"{н} нажатие «укажите площадь» у {ид}: фокус {ф['фокус']}, галочка {ф['отм']}")

    # Вписали фасад — пометка с него ушла, подсказка осталась, у покраски цена
    стр.locator("#kbAreaFasad").fill("120")
    стр.wait_for_timeout(300)
    п = стр.evaluate(ПОМЕТКИ)
    if п["фасад"] or not п["кровля"] or not п["подсказка"]:
        НАХОДКИ.append(f"{н} фасад вписан: пометки {п}")
    т = стр.evaluate("() => document.getElementById('optprice_kb_p17').textContent.trim()")
    if not any(с.isdigit() for с in т):
        НАХОДКИ.append(f"{н} фасад вписан, а покраска пишет «{т}»")
    стр.locator("#kbAreaRoof").fill("90")
    стр.wait_for_timeout(300)
    п = стр.evaluate(ПОМЕТКИ)
    if п["фасад"] or п["кровля"] or п["подсказка"]:
        НАХОДКИ.append(f"{н} обе площади вписаны: пометки {п}")
    стр.screenshot(path=str(КАДРЫ / f"заполнено_{ш}.png"), full_page=False,
                   clip={"x": 0, "y": max(0, стр.evaluate("() => document.getElementById('kbAreasWrap').getBoundingClientRect().top + scrollY") - 140),
                         "width": ш, "height": 420})

    # Проект без площадей: свай нет — поле «введите сумму»
    стр.evaluate("() => { kbSetArea('fasad', ''); kbSetArea('roof', ''); }")
    проект(стр, "Брус без площадей")
    ц = стр.evaluate(ЦЕНЫ)
    if ц["f1"] not in (None, 0) or not ц["пор"]:
        НАХОДКИ.append(f"{н} проект без площадей: свая {ц['f1']}, поле ввода {ц['пор']}")

    # Каркас: пометок нет, прочерк остаётся
    стр.evaluate("async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 400)); selectProjectOption(0); calc(); }")
    п = стр.evaluate(ПОМЕТКИ)
    if п["фасад"] or п["кровля"] or п["подсказка"]:
        НАХОДКИ.append(f"{н} каркас: пометки площадей {п}")
    т = стр.evaluate("() => { const э = document.getElementById('optprice_p_proba'); return э ? э.textContent.trim() : null; }")
    if т not in ("—", None):
        НАХОДКИ.append(f"{н} каркас: опция без площади пишет «{т}»")
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    к.close()

    # Ночь: пометка тоже видна и вид чистый
    к, стр, ош = открыть(бр, порт, ш, "dark")
    проект(стр, "Брус проба 6×6")
    п = стр.evaluate(ПОМЕТКИ)
    if not (п["фасад"] and п["кровля"] and п["подсказка"]):
        НАХОДКИ.append(f"{н} ночь: пометки {п}")
    for в in стр.evaluate(ВИД):
        НАХОДКИ.append(f"{н} ночь, вид: {в}")
    стр.screenshot(path=str(КАДРЫ / f"ночь_{ш}.png"), full_page=False,
                   clip={"x": 0, "y": max(0, стр.evaluate("() => document.getElementById('kbAreasWrap').getBoundingClientRect().top + scrollY") - 140),
                         "width": ш, "height": 420})
    к.close()
    print(f"  {н} сваи {ц['f1']}, пометки и «укажите площадь» проверены")


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 768, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: сваи и вальмовая кровля бруса считаются правилами каркаса, пустые площади помечены, "
          "«укажите площадь» ведёт к полю; у каркаса пометок нет — на 390, 768 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
