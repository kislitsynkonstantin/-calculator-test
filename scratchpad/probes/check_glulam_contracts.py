#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договоры клеёного бруса: основной (-КБ), отделка (-ОТД), покраска (-ПОК).

Константин 22.10.2026, с шаблонами договоров бруса и снимком пресета «Техас»:
«Давай сделаем договоры на клеёный брус… Сделай их в том же стиле, как у нас
сделан каркас. Базовый текст бери из каркаса… основной, отделка, покраска
отдельно (3 договора) сразу делай».

Проба на 390 и 1440 держит:
  • у бруса по умолчанию три договора: «Основной договор» с кодом КБ,
    «Договор на отделку» (ОТД) и «Покраска» (ПОК) с разделом покраски;
  • этапы основного — задаток 35 %, доставка бруса 24 % и заезд бригады 16 %
    (60/40), сборка домокомплекта 20 %, кровля 4 %, окончательная приёмка —
    от 45 000 до 50 000 ₽ (22.10.2026); суммы этапов каждого договора сходятся
    с его ценой, этапы кратны 5 000 ₽, кроме собирающего остаток; то же на
    ценах от 600 тысяч до 9 миллионов, с фундаментом и без; в графике договора
    срок «в день доставки домокомплекта на участок»;
  • все три договора открываются документом, а не заглушкой: номер с кодом
    -КБ, -ОТД, -ПОК, в основном — домокомплект, его сборка и гарантия
    «Домокомплект и конструктив», ни слова «каркас»; в покраске — предмет
    «покраске», этап «покрасочные работы» и гарантия 12 месяцев;
  • в меню документа есть «Договор на покраску», в «Печатать всё» — тоже;
  • правила эксплуатации бруса открываются документом (версия 1.0): строение
    из клеёного бруса, венцы, усадка, ни слова «каркас»; номера всех трёх
    договоров; с парной — раздел «Парное отделение и печь», без неё — нет;
  • у каркаса состав прежний — два договора, и текст основного договора,
    договора на отделку и правил слово в слово тот же, что до правки (сравнение с
    `git show HEAD:index.html` или с BM_BASE).

    python3 check_glulam_contracts.py
"""
import json, os, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
КОРЕНЬ = м.КОРЕНЬ


def открыть(стр, тех):
    стр.evaluate("""async (тех) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      try { closePrintPreview(); } catch (e) {}
      await switchTech(тех); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0] === (тех === 'glulam' ? 'Брус проба 6×6' : 'Каркас проба 6×4')));
      setThickness(1); await new Promise(r => setTimeout(r, 300));
      // У бруса площади для формул (покраска считается от фасада) вписываются руками.
      if (тех === 'glulam' && typeof kbAreas !== 'undefined') { kbAreas.fasad = 60; kbAreas.roof = 50; }
      // Отделка и покраска в расчёте — иначе второму и третьему договору не из чего быть.
      for (const разд of ['steam', 'interior', 'paint']) {
        const о = OPTIONS.filter(o => o.section === разд && !o.included && !checkedOptions[o.id] && o.status !== 'legacy')
          .find(o => { try { return (getOptPrice ? getOptPrice(o) : 1) > 0; } catch (e) { return true; } });
        if (о) toggleOpt(о.id);
      }
      calc(); document.getElementById('contractNumber').value = '11112222';
      document.getElementById('cdContractNumKar').value = ''; document.getElementById('cdContractNumO').value = '';
      await new Promise(r => setTimeout(r, 300)); }""", тех)


ДОГОВОР = """(ид) => { const v = getContractVarsKar(ид); const html = buildContractHtmlKar(v);
  const д = new DOMParser().parseFromString(html, 'text/html');
  const текст = д.body.innerText || д.body.textContent;
  return { вид: v.kind, тех: v.tech, номер: v.contractNumKar, этапы: v.acceptanceStages, платежи: v.paymentRows,
           цена: v.contractTotal, текст: текст.replace(/\\s+/g, ' '), заголовок: д.title,
           гарантия: [...д.querySelectorAll('.bars .bar')].map(б => б.innerText.replace(/\\s+/g, ' ').trim()) }; }"""

ПРАВИЛА = """() => { const v = getContractVarsKar(естьДоговор(2) ? 2 : 1); const html = buildRulesHtml(v);
  const д = new DOMParser().parseFromString(html, 'text/html');
  return { текст: (д.body.innerText || д.body.textContent).replace(/\\s+/g, ' ') + ' ' + д.title,
           версия: ((д.querySelector('.ver') || {}).textContent || '').replace('Версия', '').trim(),
           парная: ['steam', 'stove'].some(к => !isPrintSectionEmpty(к)) }; }"""

ПЛАН = """() => getPPContracts().map(c => { const st = ppState[c.id] || (ppInitContract(c), ppState[c.id]);
  return { id: c.id, код: c.code, имя: c.name, разделы: c.sections, этапы: c.payments.map(p => p.label),
           доли: c.payments.map(p => p.pct), суммы: st.amounts, финал: st.finalAmt || 0, цена: ppGetTotal(c),
           сФиналом: !!(st.hasFinal || st.hasFinalFixed) }; })"""


def таблицы():
    # Фикстура бруса — без покраски: покраске договору не из чего быть.
    т = г.таблицы()
    т["pricing_options"] = т["pricing_options"] + [
        {"product": "glulam", "option_id": "kb_p_проба", "name": "Проба покраска бруса", "section": "paint",
         "included": False, "price": 180000, "formula": None, "status": None, "sort": 90}]
    return т


def прогон(бр, порт, ш, база):
    н = f"[{ш}]"
    к = бр.new_context(viewport={"width": ш, "height": 900})
    стр = к.new_page()
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/{база}", wait_until="load")
    стр.wait_for_timeout(2500)
    if база != "index.html":
        # Прежняя сборка — только тексты договоров каркаса для сравнения.
        открыть(стр, "frame")
        т = {ид: стр.evaluate(ДОГОВОР, ид)["текст"] for ид in (1, 2)}
        т["правила"] = стр.evaluate(ПРАВИЛА)["текст"]
        к.close()
        return т

    # ── брус ──
    открыть(стр, "glulam")
    стр.evaluate("() => сбросПлатёжногоПлана()")
    план = стр.evaluate(ПЛАН)
    коды = [(п["id"], п["код"], п["имя"]) for п in план]
    if коды != [(1, "КБ", "Основной договор"), (2, "ОТД", "Договор на отделку"), (3, "ПОК", "Покраска")]:
        НАХОДКИ.append(f"{н} брус: состав по умолчанию {коды}")
    else:
        осн = план[0]
        if осн["доли"] != [35, 0, 24, 16, 20, 4, 0]:
            НАХОДКИ.append(f"{н} брус: доли основного {осн['доли']}, ждали 35/фундамент/24/16/20/4/остаток")
        # Доставка и заезд — 60/40; окончательная приёмка — 45–50 тысяч.
        for цена, фунд in ((600000, 0), (1350000, 0), (2190000, 0), (2190000, 207900), (4870000, 350000), (9000000, 0)):
            р = стр.evaluate("""([цена, фунд]) => { const c = getPPContracts()[0]; const был = ppGetFoundationAmt;
              ppGetFoundationAmt = () => фунд; const сохр = ppState[c.id];
              try { ppInitContractТело(c, цена); return ppState[c.id].amounts.slice(); }
              finally { ppGetFoundationAmt = был; ppState[c.id] = сохр; } }""", [цена, фунд])
            if sum(р) != цена:
                НАХОДКИ.append(f"{н} брус при цене {цена}, фундамент {фунд}: этапы {р} дают {sum(р)}")
            if abs(р[2] / max(1, р[2] + р[3]) - 0.6) > 0.01:
                НАХОДКИ.append(f"{н} брус при цене {цена}: доставка {р[2]} и заезд {р[3]} не 60/40")
            if not (45000 <= р[-1] <= 50000):
                НАХОДКИ.append(f"{н} брус при цене {цена}, фундамент {фунд}: окончательная приёмка {р[-1]} — ждали 45–50 тысяч ({р})")
            if any(а % 5000 for а in р[:-1]):
                НАХОДКИ.append(f"{н} брус при цене {цена}, фундамент {фунд}: этап не кратен 5 000: {р}")
        if "paint" in осн["разделы"] or план[2]["разделы"] != ["paint"]:
            НАХОДКИ.append(f"{н} брус: покраска не отдельным договором: {осн['разделы']} / {план[2]['разделы']}")
    # Покраска: всё задатком, финальный — до 50 000 ₽ (22.10.2026).
    пок_ = next((п for п in план if п["код"] == "ПОК"), None)
    if пок_ and пок_["цена"] > 50000 and not (0 < пок_["финал"] <= 50000 and пок_["финал"] > 45000):
        НАХОДКИ.append(f"{н} брус, покраска: финальный {пок_['финал']} ₽ — ждали от 45 до 50 тысяч, задаток {пок_['суммы']}")
    for п in план:
        сумма = sum(п["суммы"]) + (п["финал"] if п["сФиналом"] else 0)
        if п["цена"] > 0 and abs(сумма - п["цена"]) > 1:
            НАХОДКИ.append(f"{н} брус, «{п['имя']}»: этапы {сумма} ₽ не сходятся с ценой {п['цена']} ₽")
        собирает = -1 if п["сФиналом"] else len(п["суммы"]) - 1
        for i, а in enumerate(п["суммы"]):
            if i != собирает and а % 5000:
                НАХОДКИ.append(f"{н} брус, «{п['имя']}»: этап «{п['этапы'][i]}» {а} ₽ не кратен 5 000")
    if any(п["цена"] <= 0 for п in план):
        НАХОДКИ.append(f"{н} брус: у договора нулевая цена — проба не проверит его этапы: {[(п['имя'], п['цена']) for п in план]}")

    # Открытие договоров бруса — как у каркаса (22.10.2026): администратору
    # и специалисту (27.10.2026) всегда, менеджеру и редактору — после согласования.
    for роль, можно in (("manager", False), ("editor", False), ("admin", True), ("specialist", True)):
        закрыты = стр.evaluate("""(р) => { const был = window._sbProfile; window._sbProfile = Object.assign({}, был, { role: р });
          try { return { доступ: договорДоступен(), комплект: документыКомплекта().filter(х => х.к.startsWith('contract')).map(х => х.можно) }; }
          finally { window._sbProfile = был; } }""", роль)
        if закрыты["доступ"] != можно or any(х != можно for х in закрыты["комплект"]) or len(закрыты["комплект"]) != 3:
            НАХОДКИ.append(f"{н} брус, роль {роль}: договоры {'открыты' if закрыты['доступ'] else 'закрыты'}, в комплекте {закрыты['комплект']} — ждали {'открыты' if можно else 'закрыты до согласования'}")
    ждём = {1: ("kar", "-КБ"), 2: ("otd", "-ОТД"), 3: ("pok", "-ПОК")}
    д = {}
    for ид, (вид, код) in ждём.items():
        в = стр.evaluate(ДОГОВОР, ид)
        д[ид] = в
        if в["вид"] != вид or not str(в["номер"]).endswith(код):
            НАХОДКИ.append(f"{н} брус, договор {ид}: вид {в['вид']}, номер {в['номер']} — ждали {вид}, {код}")
        if not в["платежи"]:
            НАХОДКИ.append(f"{н} брус, договор {ид}: в графике платежей пусто")
    т1 = д[1]["текст"]
    for нужно in ("изготовлению домокомплекта из клеёного бруса", "работы по сборке домокомплекта",
                  "готовность домокомплекта к отгрузке", "завоз на Строительную площадку домокомплекта"):
        if нужно not in т1:
            НАХОДКИ.append(f"{н} брус, основной: нет «{нужно}»")
    if re.search(r"каркас", т1, re.I):
        НАХОДКИ.append(f"{н} брус, основной: в тексте осталось «каркас»: …{т1[max(0, т1.lower().find('каркас') - 60):т1.lower().find('каркас') + 40]}…")
    if not any(г_.startswith("Домокомплект и конструктив") for г_ in д[1]["гарантия"]):
        НАХОДКИ.append(f"{н} брус, основной: гарантия {д[1]['гарантия']}")
    if "КБ" not in д[1]["заголовок"]:
        НАХОДКИ.append(f"{н} брус, основной: заголовок «{д[1]['заголовок']}»")
    # Доставка домокомплекта — в цене договора, словами (22.10.2026).
    if "Доставка домокомплекта до участка Заказчика входит в цену Договора" not in т1:
        НАХОДКИ.append(f"{н} брус, основной: нет пункта о доставке в цене договора")
    сроки1 = " | ".join(р["term"] for р in д[1]["платежи"])
    if "сборки домокомплекта" not in сроки1 or "доставки домокомплекта на участок" not in сроки1 or "каркас" in сроки1:
        НАХОДКИ.append(f"{н} брус, основной: сроки платежей «{сроки1}»")
    т3 = д[3]["текст"]
    for нужно in ("работы по покраске объекта", "покрасочные работы", "передача Объекта для покраски",
                  "На лакокрасочные материалы — гарантия производителя"):
        if нужно not in т3:
            НАХОДКИ.append(f"{н} брус, покраска: нет «{нужно}»")
    if "фундамент" in т3.lower() or "Акт приема-передачи строительной площадки" in т3:
        НАХОДКИ.append(f"{н} брус, покраска: в тексте фундамент или акт площадки")
    if д[3]["гарантия"] != ["Покрасочные работы 12мес."] and not (len(д[3]["гарантия"]) == 1 and "12" in д[3]["гарантия"][0]):
        НАХОДКИ.append(f"{н} брус, покраска: гарантия {д[3]['гарантия']}")

    # Окно печати: три договора — документом, правила — заглушкой.
    стр.evaluate("async () => { openPrintPreview(); await new Promise(r => setTimeout(r, 500)); }")
    for ид in (1, 2, 3):
        в = стр.evaluate(f"""async () => {{ выбратьДоговорОкна({ид}); await new Promise(r => setTimeout(r, 900));
          const вид = id => {{ const э = document.getElementById(id); return !!э && getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().width > 0; }};
          const п = document.querySelector('#previewEntityMenu [data-contract="{ид}"]');
          return {{ заглушка: вид('contractPreviewStub'), документ: вид('contractPreviewDoc'), метка: document.getElementById('previewEntityLabel').textContent.trim(),
                   пункт: !!п && getComputedStyle(п).display !== 'none', печатьВыкл: document.getElementById('printDocBtn').disabled,
                   шир: document.documentElement.scrollWidth, экран: innerWidth }}; }}""")
        if в["заглушка"] or not в["документ"] or в["печатьВыкл"] or not в["пункт"]:
            НАХОДКИ.append(f"{н} брус, окно печати, договор {ид}: {в}")
        if в["шир"] > в["экран"]:
            НАХОДКИ.append(f"{н} брус, договор {ид}: страница шире экрана")
        if ид == 3:
            if в["метка"] != "Договор на покраску":
                НАХОДКИ.append(f"{н} брус: в меню документа «{в['метка']}», ждали «Договор на покраску»")
            стр.screenshot(path=str(м.СНИМКИ / f"glulam-contract-pok-{ш}.png"))
        if ид == 1:
            стр.screenshot(path=str(м.СНИМКИ / f"glulam-contract-kb-{ш}.png"))
    п = стр.evaluate("""async () => { выбратьПравила(); await new Promise(r => setTimeout(r, 900));
      const вид = id => { const э = document.getElementById(id); return !!э && getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().width > 0; };
      return { заглушка: вид('contractPreviewStub'), документ: вид('contractPreviewDoc'), печатьВыкл: document.getElementById('printDocBtn').disabled }; }""")
    if п["заглушка"] or not п["документ"] or п["печатьВыкл"]:
        НАХОДКИ.append(f"{н} брус: правила эксплуатации не открылись документом: {п}")
    else:
        стр.screenshot(path=str(м.СНИМКИ / f"glulam-rules-{ш}.png"))
    # Правила: с парной — раздел «Парное отделение и печь», без неё — нет.
    пр = стр.evaluate(ПРАВИЛА)
    т = пр["текст"]
    for нужно in ("Правила эксплуатации строения из клеёного бруса с парным отделением (бани)", "Парное отделение и печь",
                  "венцы бруса", "даёт усадку", "волосяные трещины на поверхности ламелей", "-ПОК"):
        if нужно not in т:
            НАХОДКИ.append(f"{н} брус, правила с парной: нет «{нужно}»")
    if re.search(r"каркас", т, re.I):
        НАХОДКИ.append(f"{н} брус, правила: в тексте «каркас»: …{т[max(0, т.lower().find('каркас') - 60):т.lower().find('каркас') + 40]}…")
    if пр["версия"] != "1.0":
        НАХОДКИ.append(f"{н} брус, правила: версия «{пр['версия']}», ждали 1.0")
    стр.evaluate("""() => { ['steam', 'stove'].forEach(р => OPTIONS.filter(o => o.section === р && checkedOptions[o.id] && !o.included).forEach(o => toggleOpt(o.id)));
      (customOptions.steam || []).forEach(co => co.checked = false); (customOptions.stove || []).forEach(co => co.checked = false); calc(); return 1; }""")
    стр.wait_for_timeout(300)
    пр = стр.evaluate(ПРАВИЛА)
    if пр["парная"]:
        НАХОДКИ.append(f"{н} брус: снять парную в фикстуре не вышло — правила без парной не проверены")
    elif "Парное отделение и печь" in пр["текст"] or "с парным отделением" in пр["текст"]:
        НАХОДКИ.append(f"{н} брус, правила без парной: раздел о парной остался")
    elif "Правила эксплуатации строения из клеёного бруса" not in пр["текст"]:
        НАХОДКИ.append(f"{н} брус, правила без парной: заголовок не тот")
    комплект = стр.evaluate("() => документыКомплекта().map(х => х.к + ':' + (х.можно ? 'да' : х.почему))")
    for нужно in ("contract-1:да", "contract-2:да", "contract-3:да"):
        if нужно not in комплект:
            НАХОДКИ.append(f"{н} брус: в «Печатать всё» нет {нужно}: {комплект}")

    # ── каркас ──
    открыть(стр, "frame")
    стр.evaluate("() => сбросПлатёжногоПлана()")
    коды = стр.evaluate("() => contractsConfig.map(c => c.code)")
    if коды != ["КАР", "ОТД"]:
        НАХОДКИ.append(f"{н} каркас: состав по умолчанию {коды}, ждали КАР, ОТД")
    тк = {ид: стр.evaluate(ДОГОВОР, ид) for ид in (1, 2)}
    if тк[1]["вид"] != "kar" or not str(тк[1]["номер"]).endswith("-КАР") or "КАР" not in тк[1]["заголовок"]:
        НАХОДКИ.append(f"{н} каркас: основной {тк[1]['вид']} {тк[1]['номер']} «{тк[1]['заголовок']}»")
    итог = {ид: тк[ид]["текст"] for ид in (1, 2)}
    итог["правила"] = стр.evaluate(ПРАВИЛА)["текст"]
    for о in [о for о in ош if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    к.close()
    print(f"  {н} проверено: брус — три договора, правила с парной и без, этапы, тексты, окно печати и комплект; каркас — состав и номер")
    return итог


def главная():
    # Прежняя сборка рядом с нынешней — для сравнения текстов каркаса.
    база = os.environ.get("BM_BASE")
    старый = КОРЕНЬ / "_старый_probe.html"
    try:
        текст = pathlib.Path(база).read_text(encoding="utf-8") if база else subprocess.run(
            ["git", "-C", str(КОРЕНЬ), "show", "HEAD:index.html"], capture_output=True, text=True, check=True).stdout
        старый.write_text(текст, encoding="utf-8")
    except Exception as е:
        старый = None
        НАХОДКИ.append(f"прежней сборки для сравнения нет: {е}")
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            было = прогон(бр, порт, 1440, старый.name) if старый else None
            for ш in (390, 1440):
                стало = прогон(бр, порт, ш, "index.html")
                if было and ш == 1440:
                    # Строки гарантии с 22.10.2026 следуют спецификации договора —
                    # их держит check_contract_warranty.py; здесь сравнивается
                    # остальной текст.
                    # С 23.10.2026 к покраске внутри основного договора добавлены
                    # оговорки договора на покраску — их тоже держит та проба.
                    без = lambda т: re.sub(r" ?На лакокрасочные материалы — гарантия производителя\.| ?выцветание, потемнение и износ покрытия, если защитное покрытие не обновлялось в сроки, указанные производителем покрасочного материала\.?", "",
                        re.sub(r"на результат работ: .*?(?= На оборудование| На лакокрасочные| 7\.3\.)", "на результат работ: [гарантия]", т))
                    for ид in (1, 2, "правила"):
                        if без(было[ид]) != без(стало[ид]):
                            а, б = без(было[ид]), без(стало[ид])
                            и = next((i for i in range(min(len(а), len(б))) if а[i] != б[i]), min(len(а), len(б)))
                            НАХОДКИ.append(f"каркас, {ид}: текст изменился: было «…{а[max(0, и - 60):и + 60]}…», стало «…{б[max(0, и - 60):и + 60]}…»")
            бр.close()
    finally:
        с.shutdown()
        if старый and старый.exists():
            старый.unlink()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: у бруса три договора — основной -КБ, отделка -ОТД и покраска -ПОК — со своими этапами и текстом, "
          "открываются документом и идут в комплект; правила бруса свои, с парной и без; договоры и правила каркаса слово в слово прежние — на 390 и 1440.")


if __name__ == "__main__":
    главная()
