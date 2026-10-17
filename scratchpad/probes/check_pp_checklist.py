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
    кроме фундамента (по смете) и последнего этапа основного договора (он
    собирает остатки); финальный договора на отделку — от 45 000 до 50 000;
    сумма этапов равна цене; «Проверка» о плане молчит;
  • правка руками на некратную сумму — пункт «округлить вверх до 5 000»;
    финальный больше 50 000 — пункт; этапы не сходятся с ценой — пункт;
    у пунктов раздел «Платёжный план», нажатие открывает окно плана;
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
            некратные = [а for и_, а in enumerate(д["amounts"]) if и_ != последний and not д["фундамент"][и_] and а % 5000]
            факт(not некратные, f"{и} этапы кратны 5 000, кроме фундамента и собирающего остатки: {д['amounts']}")
            if д["id"] == 2:
                факт(0 <= д["final"] <= 50000 and (д["т"] < 100000 or д["final"] > 45000), f"{и} финальный {д['final']} — от 45 000 до 50 000")
    стр.evaluate(ЗАНОВО); стр.evaluate("() => calc()")
    факт(not стр.evaluate(ПУНКТЫ), f"план по правилу — «Проверка» о плане молчит: {стр.evaluate(ПУНКТЫ)}")

    # ── Правки руками ──
    стр.evaluate("() => { ppState[1].amounts[0] += 1234; ppState[1].amounts[ppState[1].amounts.length - 1] -= 1234; }")
    п = стр.evaluate(ПУНКТЫ)
    факт(any(х["т"] == "Этап «Аванс по договору» договора «Основной договор» — округлить вверх до 5 000 ₽, разницу — в финальный платёж" for х in п),
         f"аванс некратный — пункт «округлить вверх до 5 000»: {п}")
    факт(all(х["имя"] == "Платёжный план" for х in п) and п, f"раздел пунктов — «Платёжный план»: {[х['имя'] for х in п]}")
    факт(not any("не сходятся" in х["т"] for х in п), "сумма та же — о несходимости молчит")
    стр.evaluate(ЗАНОВО)
    if стр.evaluate("() => !!ppState[2] && ppGetTotal(getPPContracts().find(c => c.id === 2)) > 0"):
        стр.evaluate("() => { const st = ppState[2]; st.amounts[0] -= 30000; st.finalAmt += 30000; }")
        п = стр.evaluate(ПУНКТЫ)
        факт(any(х["т"].startswith("Финальный платёж договора «") and "не больше 50 000 ₽" in х["т"] for х in п),
             f"финальный больше 50 000 — пункт: {п}")
        стр.evaluate(ЗАНОВО)
    else:
        НАХОДКИ.append("договор на отделку без цены — проверить финальный не на чем")
    стр.evaluate("() => { ppState[1].amounts[0] += 5000; }")
    п = стр.evaluate(ПУНКТЫ)
    факт(any("не сходятся с ценой" in х["т"] for х in п), f"этапы не сходятся с ценой — пункт: {п}")
    # Нажатие на пункт открывает окно плана.
    стр.evaluate("() => { кРазделуИзПроверки('pp', ''); }"); стр.wait_for_timeout(500)
    факт(стр.evaluate("() => getComputedStyle(document.getElementById('paymentPlanOverlay')).display !== 'none'"), "нажатие на пункт открывает окно платёжного плана")
    стр.evaluate("() => { if (typeof closePaymentPlan === 'function') closePaymentPlan(); else document.getElementById('paymentPlanOverlay').classList.remove('open'); }")
    стр.evaluate(ЗАНОВО)

    # ── Своя схема договора ──
    д = стр.evaluate("""() => { contractsConfig.push({ id: 3, name: 'Покраска', code: 'ПОК', color: '#0891b2', sections: [] });
      const осн = contractsConfig.find(c => c.id === 1); осн.sections = осн.sections.filter(к => к !== 'paint');
      contractsConfig.find(c => c.id === 3).sections.push('paint');
      customOptions.paint = (customOptions.paint || []).concat([{ id: 'пок1', name: 'Покраска фасада (учебная)', price: 431234, checked: true }]); calc();
      ppDistribute(3); const st = ppState[3], c = getPPContracts().find(x => x.id === 3);
      return { st: st && { amounts: st.amounts, final: st.finalAmt, hasFinal: st.hasFinal }, т: ppGetTotal(c) }; }""")
    if д["т"] > 0 and д["st"]:
        факт(д["st"]["hasFinal"] and abs(sum(д["st"]["amounts"]) + д["st"]["final"] - д["т"]) <= 1,
             f"своя схема, распределённая заново: финальный собирает остаток, сумма — цена: {д}")
    else:
        НАХОДКИ.append(f"своя схема: у договора покраски нет цены — нечего распределять: {д}")
    факт(not any("покраску в отдельный" in х for х in стр.evaluate("() => проверкаПоЧекЛисту().замечания.map(з => з.т)")),
         "каркас: пункта про отдельный договор покраски нет")

    # ── Брус: покраска отдельным договором ──
    стр.evaluate("async () => { contractsConfig = contractsConfig.filter(c => c.id !== 3); contractsConfig.find(c => c.id === 1).sections.push('paint'); await switchTech('glulam'); await new Promise(r => setTimeout(r, 700)); selectProjectOption(0); calc(); }")
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
print("Чисто: этапы кратны 5 000 вверх, финальный до 50 000, сумма — цена; правки руками ловит «Проверка»; покраска бруса — отдельным договором.")
