#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Платёжный план по чек-листу договора (С-ДЗ 5, 7, 8) и покраска бруса
отдельным договором (П-ПС-7-10).

Константин 17.10.2026, снимком строк разбора проверок «Покраска бруса
отдельным договором» и «Платежи договора»: «Это все делай». Чек-лист: этапы
оплаты в сумме — цена договора; авансовые этапы кратны 5 000 ₽ с округлением
вверх; финальный платёж не больше 50 000 ₽ и собирает остатки округления,
поэтому бывает некруглым; у клеёного бруса покраска — отдельным договором.

Держит:
  • план по правилу при ценах от 180 000 до 4 000 000: этапы кратны 5 000,
    кроме последнего этапа основного договора (он собирает остатки);
    финальный договора на отделку — от 45 000 до 50 000; сумма этапов равна
    цене; «Проверка» о плане молчит;
  • платёж за фундамент — смета фундамента вниз до 5 000 (23.10.2026; прежде вверх,
    Константин,
    17.10.2026, снимком плана с платежом 207 900 ₽: «чтобы в платежном плане
    платежи стояли кратно 5 тыс., а остаток копейки уходил на финальный
    платёж»): при смете, не кратной 5 000, этап кратен, не меньше сметы и
    больше её меньше чем на 5 000, остаток — в последнем этапе, сумма — цена;
    правленный руками план с некруглым фундаментом — пункт;
  • правка руками на некратную сумму — пункт «округлить вверх до 5 000»
    (у основного договора разница — в последний этап, финального у него нет);
    финальный больше 55 000 — пункт, до 55 000 — допуск, молчит (Константин,
    17.10.2026: «не больше 50 тыс., допускается +5 тыс.»); этапы не сходятся
    с ценой — пункт; у пунктов раздел «Платёжный план», нажатие открывает
    окно плана;
  • автоматика (Константин, 17.10.2026: «чтобы сразу платежный план
    правильно ставился. А правку писать, только если вручную поправили»):
    план по правилу, сложенный прежним правилом (до тысяч), после calc()
    собран по действующему, и «Проверка» о нём молчит ещё до пересчёта; план
    без пометки с этапами по умолчанию — так же; без пометки с добавленным
    этапом — не тронут, пункты есть; правленный руками — не тронут, пункты
    есть; набор суммы в поле помечает план правкой сразу, и пересчёт посреди
    набора его не пересобирает;
  • своя схема договора («Аванс — Финальный платёж»), распределённая заново,
    — финальный собирает остаток, сумма равна цене (прежде он пропадал);
  • брус: отмеченная покраска в общем договоре — «Вынести покраску в
    отдельный договор»; покраска своим договором — молчит; у каркаса пункта
    нет.

    python3 check_pp_checklist.py
"""
import functools, http.server, os, pathlib, socketserver, sys, threading
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


ПЛАН = """(цены) => цены.map(т => getPPContracts().filter(c => c.id === 1 || c.id === 2).map(c => {
  ppInitContract(c, т); const st = ppState[c.id]; const этапы = c.payments.filter(p => !p.final && !p.finalFixed);
  return { id: c.id, т, amounts: st.amounts.slice(), final: st.finalAmt || 0, сФиналом: !!(st.hasFinal || st.hasFinalFixed),
    фундамент: этапы.map(p => !!p.foundationFixed) }; }))"""
ПУНКТЫ = """() => { const п = проверкаПоЧекЛисту(); return п.замечания.filter(з => з.раздел === 'pp').map(з => ({ т: з.т, имя: имяРаздела(з.раздел) })); }"""
ЗАНОВО = "() => { ppState = {}; getPPContracts().forEach(c => ppInitContract(c)); }"


# Сервер и страница — как у остальных проб карточки пресета.
КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр, ошибки = к.начать(бр, с.server_address[1], 1440, 900, False)

    # ── План по правилу ──
    цены = [180000, 300000, 529440, 1234567, 2000000, 3217777, 4000000]
    for договоры in стр.evaluate(ПЛАН, цены):
        for д in договоры:
            и = f"договор {д['id']}, цена {д['т']}:"
            сумма = sum(д["amounts"]) + (д["final"] if д["сФиналом"] else 0)
            факт(abs(сумма - д["т"]) <= 1, f"{и} этапы в сумме — цена ({сумма})")
            последний = -1 if д["сФиналом"] else len(д["amounts"]) - 1
            некратные = [а for и_, а in enumerate(д["amounts"]) if и_ != последний and а % 5000]
            факт(not некратные, f"{и} этапы кратны 5 000, кроме собирающего остатки: {д['amounts']}")
            if д["id"] == 2:
                факт(0 <= д["final"] <= 50000 and (д["т"] < 100000 or д["final"] > 45000), f"{и} финальный {д['final']} — от 45 000 до 50 000")
    стр.evaluate(ЗАНОВО); стр.evaluate("() => calc()")
    факт(not стр.evaluate(ПУНКТЫ), f"план по правилу — «Проверка» о плане молчит: {стр.evaluate(ПУНКТЫ)}")

    # ── Платёж за фундамент — вниз до 5 000, остаток — финальному (23.10.2026) ──
    ф = стр.evaluate("""() => { const с = OPTIONS.filter(o => o.section === 'foundation' && !o.included && (o.price || 0) > 0);
      let смета = 0;
      for (const о of с) { checkedOptions[о.id] = true; calc(); смета = ppGetFoundationAmt(); if (смета > 0 && смета % 5000) break; checkedOptions[о.id] = false; calc(); }
      if (!(смета % 5000)) { customOptions.foundation = (customOptions.foundation || []).concat([{ id: 'фс1', name: 'Фундамент (учебный)', price: 207900, checked: true }]); calc(); смета = ppGetFoundationAmt(); }
      ppState = {}; const c = getPPContracts().find(x => x.id === 1); ppInitContract(c); const st = ppState[1];
      const и = c.payments.filter(p => !p.final && !p.finalFixed).findIndex(p => p.foundationFixed);
      return { смета, этап: st.amounts[и], amounts: st.amounts.slice(), цена: ppGetTotal(c), сумма: st.amounts.reduce((а, б) => а + б, 0) }; }""")
    факт(ф["смета"] % 5000 != 0, f"смета фундамента для проверки — не кратна 5 000: {ф['смета']}")
    факт(ф["этап"] % 5000 == 0 and ф["смета"] - 5000 < ф["этап"] <= ф["смета"], f"платёж за фундамент — смета вниз до 5 000: смета {ф['смета']}, этап {ф['этап']}")
    факт(abs(ф["сумма"] - ф["цена"]) <= 1 and all(а % 5000 == 0 for а in ф["amounts"][:-1]), f"остаток — в последнем этапе, сумма — цена: {ф}")
    п = стр.evaluate(ПУНКТЫ)
    факт(not п, f"план с фундаментом по правилу — «Проверка» молчит: {п}")
    стр.evaluate("() => { const st = ppState[1]; const и = 1; const д = 2100; st.amounts[и] -= д; st.amounts[st.amounts.length - 1] += д; ppПравкаРуками(1); }")
    п = стр.evaluate(ПУНКТЫ)
    факт(any("«Платёж за фундамент»" in х["т"] and "округлить вниз до 5 000" in х["т"] for х in п), f"правленный руками некруглый фундамент — пункт: {п}")
    стр.evaluate(ЗАНОВО)

    # ── Правки руками ──
    стр.evaluate("() => { ppState[1].amounts[0] += 1234; ppState[1].amounts[ppState[1].amounts.length - 1] -= 1234; ppПравкаРуками(1); }")
    п = стр.evaluate(ПУНКТЫ)
    факт(any(х["т"] == "Этап «Задаток по договору» договора «Основной договор» — округлить вверх до 5 000 ₽, разницу — в последний этап" for х in п),
         f"аванс некратный — пункт «округлить вверх до 5 000»: {п}")
    факт(all(х["имя"] == "Платёжный план" for х in п) and п, f"раздел пунктов — «Платёжный план»: {[х['имя'] for х in п]}")
    факт(not any("не сходятся" in х["т"] for х in п), "сумма та же — о несходимости молчит")
    стр.evaluate(ЗАНОВО)
    if стр.evaluate("() => !!ppState[2] && ppGetTotal(getPPContracts().find(c => c.id === 2)) > 0"):
        стр.evaluate("() => { const st = ppState[2]; st.amounts[0] -= 30000; st.finalAmt += 30000; ppПравкаРуками(2); }")
        п = стр.evaluate(ПУНКТЫ)
        факт(any(х["т"].startswith("Финальный платёж договора «") and "не больше 50 000 ₽ с допуском +5 000 ₽" in х["т"] for х in п),
             f"финальный больше 55 000 — пункт: {п}")
        стр.evaluate(ЗАНОВО)
        ф = стр.evaluate("() => { const st = ppState[2]; const на = 55000 - st.finalAmt; st.amounts[0] -= на; st.finalAmt += на; ppПравкаРуками(2); return st.finalAmt; }")
        п = стр.evaluate(ПУНКТЫ)
        факт(ф == 55000 and not any(х["т"].startswith("Финальный платёж") for х in п), f"финальный {ф} — в допуске +5 000, пункта о финальном нет: {п}")
        стр.evaluate("() => { const st = ppState[2]; st.amounts[0] -= 1; st.finalAmt += 1; }")
        п = стр.evaluate(ПУНКТЫ)
        факт(any(х["т"].startswith("Финальный платёж") for х in п), f"финальный 55 001 — сверх допуска, пункт есть: {п}")
        стр.evaluate(ЗАНОВО)
    else:
        НАХОДКИ.append("договор на отделку без цены — проверить финальный не на чем")
    стр.evaluate("() => { ppState[1].amounts[0] += 5000; ppState[1].руками = true; }")
    п = стр.evaluate(ПУНКТЫ)
    факт(any("не сходятся с ценой" in х["т"] for х in п), f"этапы не сходятся с ценой — пункт: {п}")
    # Нажатие на пункт открывает окно плана.
    стр.evaluate("() => { кРазделуИзПроверки('pp', ''); }"); стр.wait_for_timeout(500)
    факт(стр.evaluate("() => getComputedStyle(document.getElementById('paymentPlanOverlay')).display !== 'none'"), "нажатие на пункт открывает окно платёжного плана")
    стр.evaluate("() => { if (typeof closePaymentPlan === 'function') closePaymentPlan(); else document.getElementById('paymentPlanOverlay').classList.remove('open'); }")
    стр.evaluate(ЗАНОВО)

    # ── Автоматика: план по правилу держит правило ──
    ПО_ПРАВИЛУ = """(cid) => { const c = getPPContracts().find(x => x.id === cid); const сохр = ppState[cid];
      ppInitContractТело(c, ppGetTotal(c)); const р = ppState[cid]; ppState[cid] = сохр; return { amounts: р.amounts, final: р.finalAmt || 0 }; }"""
    СЕЙЧАС = "(cid) => { const st = ppState[cid]; return { amounts: st.amounts.slice(), final: st.finalAmt || 0, руками: st.руками === undefined ? null : st.руками }; }"
    # Прежнее правило — суммы до тысяч (так сложен план «Виго» 25.09.2026).
    ПРЕЖНЕЕ = """(cid) => { const c = getPPContracts().find(x => x.id === cid), т = ppGetTotal(c), st = ppState[cid];
      st.amounts = st.amounts.map((а, и) => c.payments.filter(p => !p.final && !p.finalFixed)[и].foundationFixed ? а : Math.round(а / 1000) * 1000 + 123);
      const с = st.amounts.reduce((а, б) => а + б, 0);
      if (st.hasFinal || st.hasFinalFixed) st.finalAmt = т - с; else st.amounts[st.amounts.length - 1] += т - с - 0; }"""
    for cid in (1, 2):
        стр.evaluate(ЗАНОВО)
        if not стр.evaluate(f"() => ppGetTotal(getPPContracts().find(c => c.id === {cid})) > 0"):
            НАХОДКИ.append(f"договор {cid} без цены — автоматику проверить не на чем"); continue
        стр.evaluate(ПРЕЖНЕЕ, cid)
        было = стр.evaluate(СЕЙЧАС, cid)
        п = стр.evaluate(ПУНКТЫ)
        факт(not п, f"договор {cid}: план по правилу, сложенный прежним правилом, — «Проверка» молчит и до пересчёта: {п}")
        стр.evaluate("() => calc()")
        стало, правило = стр.evaluate(СЕЙЧАС, cid), стр.evaluate(ПО_ПРАВИЛУ, cid)
        факт(стало["amounts"] != было["amounts"] and стало["amounts"] == правило["amounts"] and abs(стало["final"] - правило["final"]) < 1 and стало["руками"] is False,
             f"договор {cid}: прежний план по правилу собран по действующему: было {было}, стало {стало}, правило {правило}")
        # Без пометки (сохранён до 02.10.2026), этапы по умолчанию — собирается так же.
        стр.evaluate(ПРЕЖНЕЕ, cid); стр.evaluate(f"() => {{ delete ppState[{cid}].руками; }}")
        стр.evaluate("() => calc()")
        стало = стр.evaluate(СЕЙЧАС, cid)
        факт(стало["amounts"] == правило["amounts"] and стало["руками"] is False, f"договор {cid}: план без пометки с этапами по умолчанию собран по правилу: {стало}")
    # Без пометки, но с добавленным этапом — правка руками: не тронут, пункты есть.
    стр.evaluate(ЗАНОВО)
    стр.evaluate("() => { ppAddStage(2); const st = ppState[2]; st.amounts[st.amounts.length - 1] = 12345; st.amounts[0] -= 12345; delete st.руками; }")
    было = стр.evaluate(СЕЙЧАС, 2); стр.evaluate("() => calc()"); стало = стр.evaluate(СЕЙЧАС, 2)
    п = стр.evaluate(ПУНКТЫ)
    факт(было["amounts"] == стало["amounts"] and any("Договор на отделку" in х["т"] for х in п),
         f"без пометки с добавленным этапом — план не тронут, пункты есть: было {было}, стало {стало}, пункты {п}")
    стр.evaluate("() => { const cfg = contractsConfig.find(c => c.id === 2); delete cfg.payments; }"); стр.evaluate(ЗАНОВО)
    # Правленный руками — не тронут, пункты есть.
    стр.evaluate("() => { const st = ppState[1]; st.amounts[0] += 1234; st.amounts[st.amounts.length - 1] -= 1234; ppПравкаРуками(1); }")
    было = стр.evaluate(СЕЙЧАС, 1); стр.evaluate("() => calc()"); стало = стр.evaluate(СЕЙЧАС, 1)
    факт(было == стало and стр.evaluate(ПУНКТЫ), f"правленный руками — не тронут, пункты есть: было {было}, стало {стало}")
    стр.evaluate(ЗАНОВО)
    # Набор суммы в поле — уже правка: пересчёт посреди набора план не пересобирает.
    стр.evaluate("() => { ppOnAmtRaw(1, 0, String(ppState[1].amounts[0] + 777)); }")
    было = стр.evaluate(СЕЙЧАС, 1); стр.evaluate("() => calc()"); стало = стр.evaluate(СЕЙЧАС, 1)
    факт(было == стало and стало["руками"] is True, f"набор суммы помечает правку сразу, пересчёт её не стирает: было {было}, стало {стало}")
    стр.evaluate(ЗАНОВО)

    # ── Своя схема договора ──
    д = стр.evaluate("""() => { contractsConfig.push({ id: 3, name: 'Покраска', code: 'ПОК', color: '#0891b2', sections: [] });
      const осн = contractsConfig.find(c => c.id === 1); осн.sections = осн.sections.filter(к => к !== 'paint');
      contractsConfig.find(c => c.id === 3).sections.push('paint');
      customOptions.paint = (customOptions.paint || []).concat([{ id: 'пок1', name: 'Покраска фасада (учебная)', price: 431234, checked: true }]); calc();
      ppDistribute(3); const st = ppState[3], c = getPPContracts().find(x => x.id === 3);
      return { st: st && { amounts: st.amounts, final: st.finalAmt, hasFinal: st.hasFinal, hasFinalFixed: st.hasFinalFixed }, т: ppGetTotal(c) }; }""")
    # Покраска с 22.10.2026 — всё задатком, финальный до 50 000 ₽ с остатками округления.
    if д["т"] > 0 and д["st"]:
        факт(д["st"]["hasFinalFixed"] and 0 < д["st"]["final"] <= 50000 and abs(sum(д["st"]["amounts"]) + д["st"]["final"] - д["т"]) <= 1,
             f"покраска, распределённая заново: задаток — всё, финальный до 50 000 ₽, сумма — цена: {д}")
    else:
        НАХОДКИ.append(f"своя схема: у договора покраски нет цены — нечего распределять: {д}")
    факт(not any("покраску в отдельный" in х for х in стр.evaluate("() => проверкаПоЧекЛисту().замечания.map(з => з.т)")),
         "каркас: пункта про отдельный договор покраски нет")

    # ── Брус: покраска отдельным договором ──
    # С 22.10.2026 у бруса покраска по умолчанию — третьим договором, и выбор
    # проекта ставит этот состав; покраску в общий договор кладём после выбора.
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 700)); selectProjectOption(0); "
                 "contractsConfig = contractsConfig.filter(c => c.id !== 3); const о = contractsConfig.find(c => c.id === 1); if (!о.sections.includes('paint')) о.sections.push('paint'); calc(); }")
    стр.wait_for_timeout(700)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    о = стр.evaluate("() => { customOptions.paint = [{ id: 'пок2', name: 'Покраска снаружи (учебная)', price: 250000, checked: true }]; calc(); return 'пок2'; }")
    if not о:
        НАХОДКИ.append("брус: своя позиция покраски не встала")
    else:
        т = стр.evaluate("() => проверкаПоЧекЛисту().замечания.filter(з => /покраску в отдельный/.test(з.т)).map(з => ({ т: з.т, р: з.раздел }))")
        факт(т == [{"т": "Вынести покраску в отдельный договор", "р": "paint"}], f"брус: покраска в общем договоре — пункт: {т}")
        стр.evaluate("""() => { contractsConfig.forEach(c => { c.sections = c.sections.filter(к => к !== 'paint'); });
          contractsConfig.push({ id: 3, name: 'Покраска', code: 'ПОК', color: '#0891b2', sections: ['paint'] }); calc(); }""")
        т = стр.evaluate("() => проверкаПоЧекЛисту().замечания.filter(з => /покраску в отдельный/.test(з.т)).length")
        факт(т == 0, "брус: покраска своим договором — пункта нет")
        стр.evaluate(f"() => {{ customOptions.paint = []; contractsConfig = contractsConfig.filter(c => c.id !== 3); contractsConfig.find(c => c.id === 1).sections.push('paint'); calc(); }}")
        т = стр.evaluate("() => проверкаПоЧекЛисту().замечания.filter(з => /покраску в отдельный/.test(з.т)).length")
        факт(т == 0, "брус: покраски нет — пункта нет, хоть раздел и в общем договоре")
    факт(not ошибки, f"ошибок страницы нет: {ошибки[:2]}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: этапы кратны 5 000 вверх, финальный до 50 000, сумма — цена; план по правилу держит действующее правило сам; "
      "правки руками ловит «Проверка», финальный — с допуском до 55 000; покраска бруса — отдельным договором.")
