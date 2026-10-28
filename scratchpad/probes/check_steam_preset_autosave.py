#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет парной сохраняется сам, как у каркаса и бруса; «Проверка» парной — своя.

Константин 28.10.2026: «Проверь пресеты парной, чтобы все сохранялось
автоматически, как в каркасе/брусе» и, снимком «Проверки» парной с пробным
бурением и бытовкой, «Автоматическую проверку подстрой под парную».

Проба держит:
  • открытый пресет парной сам себя не переписывает: после открытия он не
    помечен изменённым, время записи прежнее;
  • каждая правка парной — размер, тип помещения, печь из списка, опция,
    счётчик, снятая строка базы, снятая база раздела, подарок на строке,
    реквизит заказчика — ложится в пресет сама, без кнопки, за паузу
    автосохранения: снимок парной в пресете равен снимку на экране;
  • пресет, открытый заново, — тот же расчёт до рубля;
  • в «Проверке» парной нет пунктов каркаса и бруса (пробное бурение,
    бытовка, этажность и кровля, окна, договор), есть пункты печи: не
    выбрана, мала или велика по объёму, камней меньше нужного, у Ферингера
    без кассет и ПИФ, печь в металле при портале в камне; печь впору — молчит.

    python3 check_steam_preset_autosave.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_steam_tab as п
from playwright.sync_api import sync_playwright

НАХОДКИ = []
def плохо(т): НАХОДКИ.append(т)

СНИМОК = "() => JSON.stringify(парнаяСнимок())"
В_ПРЕСЕТЕ = "ид => JSON.stringify((loadAllPresets()[ид].state || {}).steam)"
ПУНКТЫ = """() => { const р = проверкаПоЧекЛисту(); return { з: р.замечания.map(з => з.т), р: р.замечания.map(з => з.раздел), в: р.вопросы }; }"""


def main():
    с, порт = п.м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=п.м.хром())
            стр, ош = п.открыть(бр, порт, 1440)
            п.в_парную(стр)

            # «Проверка» парной: без пунктов каркаса и бруса.
            д = стр.evaluate(ПУНКТЫ)
            чужие = [т for т in д["з"] + д["в"] if any(с in т for с in ("бурени", "бытовк", "этажност", "кровл", "окн", "договор", "планировк"))]
            if чужие or any(р not in ("par_st", "par_pech", "par_log", "pp") for р in д["р"]):
                плохо(f"«Проверка» парной с пунктами каркаса и бруса: {д}")
            if "Выбрать печь — модель или «Печь заказчика»" not in д["з"]:
                плохо(f"парная без печи — нет пункта «Выбрать печь»: {д['з']}")
            # Ферингер Малютка (8–18 м³) в парной 3 × 4 × 2,3 (печь на 35,9 м³) — мала,
            # без кассет и ПИФ; камни 40 кг при 60 нужных.
            # Кассеты и ПИФ печь Ферингер ставит сама (28.10.2026) — проба их снимает,
            # чтобы увидеть пункт «Проверки».
            стр.evaluate("() => { парнаяПечь('feringer-malyutka'); ПАР.вкл.delete('st30'); ПАР.вкл.delete('st31'); ПАР.kamni = 40; calc(); }")
            д = стр.evaluate(ПУНКТЫ)
            ждём = ["Печь мала для парной: нужна на 35,9 м³, выбрана до 18 м³", "Камней 40 кг, печи нужно 60 кг",
                    "Печь Ферингер без кассет и пароиспарителя, добавить"]
            if any(з not in д["з"] for з in ждём):
                плохо(f"пункты печи Ферингер Малютка: {д['з']} — ждали {ждём}")
            # Печь в металле, портал из талькохлорита — разная облицовка.
            стр.evaluate("() => { парнаяПечь('grom-40-p2-pech-komplekt'); document.getElementById('lbl_par_talk').click(); }")
            д = стр.evaluate(ПУНКТЫ)
            if "Печь в металле, портал в камне — привести к одной облицовке" not in д["з"]:
                плохо(f"печь в металле при портале в камне — пункта нет: {д['з']}")
            стр.evaluate("() => document.getElementById('lbl_par_talk').click()")
            д = стр.evaluate(ПУНКТЫ)
            печные = [т for т in д["з"] if "Печь" in т or "Камней" in т or "печь" in т]
            if печные:
                плохо(f"ГРОМ 40 впору (25–40 м³ при 35,9) — а пункты печи есть: {печные}")
            # Маленькой парной печь велика: 2 × 2 × 2 = 8 м³ → 13 м³, ГРОМ 40 от 25.
            стр.evaluate("() => { ПАР.L = 2; ПАР.W = 2; ПАР.H = 2; calc(); }")
            if "Печь велика для парной: рассчитана от 25 м³, парной нужно 13 м³" not in стр.evaluate(ПУНКТЫ)["з"]:
                плохо(f"ГРОМ 40 в парной 8 м³ — нет пункта «велика»: {стр.evaluate(ПУНКТЫ)['з']}")
            стр.evaluate("() => { resetEverything(); }")

            # Пресет парной: сохранить, открыть заново как менеджер.
            ид = стр.evaluate("""async () => { парнаяПечь('izistim-yalta-40-2024-aisi-430'); calc();
              const st = collectState(); await сохранитьНовыйПресет('Проба автосохранения парной', 'Проба автосохранения парной', st);
              const все = loadAllPresets(); return Object.keys(все).find(к => все[к].name === 'Проба автосохранения парной'); }""")
            if not ид:
                плохо("пресет парной не сохранился"); raise SystemExit
            стр.evaluate("async () => { resetEverything(); selectTech('Каркас'); await new Promise(r => setTimeout(r, 900)); }")
            стр.evaluate("ид => loadPreset(ид)", ид)
            стр.wait_for_timeout(2600)
            в = стр.evaluate("ид => [activePresetId === ид, _presetDirty, loadAllPresets()[ид].savedAt, currentTech]", ид)
            записан = в[2]
            стр.wait_for_timeout(1800)
            if not в[0] or в[1] or в[3] != "steam" or стр.evaluate("ид => loadAllPresets()[ид].savedAt", ид) != записан:
                плохо(f"открытый пресет парной: активен {в[0]}, помечен изменённым {в[1]}, расчёт {в[3]}, перезаписан сам {стр.evaluate('ид => loadAllPresets()[ид].savedAt', ид) != записан}")

            # Правки — каждая ложится в пресет сама.
            def правка(что, действие, проверка=None):
                стр.evaluate(действие) if isinstance(действие, str) else действие(стр)
                стр.wait_for_timeout(1900)
                экран, пресет = стр.evaluate(СНИМОК), стр.evaluate(В_ПРЕСЕТЕ, ид)
                грязный = стр.evaluate("() => _presetDirty")
                доп = стр.evaluate(проверка, ид) if проверка else True
                if экран != пресет or грязный or not доп:
                    плохо(f"{что}: в пресете {'тот же' if экран == пресет else 'другой'} снимок парной, помечен изменённым {грязный}, своё условие {доп}")

            def размер(с):
                с.fill('#pardim_L', '3,4'); с.press('#pardim_L', 'Enter')
            правка("длина 3,4 м", размер, "ид => loadAllPresets()[ид].state.steam.L === 3.4")
            правка("тип помещения «Сруб или брус»", "() => { document.getElementById('steamRoomTrigger')?.click(); document.querySelector('#steamRoomDropdown [data-room=\"log\"]').click(); }",
                   "ид => loadAllPresets()[ид].state.steam.комн === 'log'")
            правка("печь из списка", "() => { парнаяПечьОткрыть(); document.querySelector('#steamStoveDropdown [data-stove=\"grom-40-p2-pech-komplekt\"]').click(); }",
                   "ид => loadAllPresets()[ид].state.steam.печь === 'grom-40-p2-pech-komplekt'")
            правка("опция «Вагонка из ольхи»", "() => document.getElementById('lbl_par_olha').click()",
                   "ид => loadAllPresets()[ид].state.steam.вкл.includes('olha')")
            правка("счётчик полков +", "() => document.querySelector('#lbl_par_polki .opt-qty-btn:last-child').click()",
                   "ид => loadAllPresets()[ид].state.steam.polki === 4")
            правка("снятая строка базы (дверь)", "() => document.getElementById('lbl_par_door').click()",
                   "ид => loadAllPresets()[ид].state.steam.снятыСтроки.includes('door')")
            правка("снятая база раздела 3", "() => document.getElementById('sec_base_par_log').click()",
                   "ид => loadAllPresets()[ид].state.steam.снятыБазы.includes('par_log')")
            правка("подарок на строке вентиляции", "() => document.querySelector('#lbl_par_vent .opt-gift-btn').click()",
                   "ид => JSON.stringify(loadAllPresets()[ид].state).includes('par_vent')")

            def заказчик(с):
                с.fill('#clientName', 'Проба Автосохранения')
            правка("реквизит заказчика", заказчик, "ид => JSON.stringify(loadAllPresets()[ид].state).includes('Проба Автосохранения')")

            # Открыть заново — тот же расчёт.
            было = стр.evaluate("() => [Math.round(_currentTotal), JSON.stringify(парнаяСнимок())]")
            стр.evaluate("async () => { resetEverything(); selectTech('Каркас'); await new Promise(r => setTimeout(r, 900)); }")
            стр.evaluate("ид => loadPreset(ид)", ид)
            стр.wait_for_timeout(2600)
            стало = стр.evaluate("() => [Math.round(_currentTotal), JSON.stringify(парнаяСнимок())]")
            if стало != было:
                плохо(f"пресет парной после правок открылся не тем: было {было[0]} ₽, стало {стало[0]} ₽, снимок {'тот же' if было[1] == стало[1] else 'другой'}")
            for е in [е for е in ош if "supabase" not in е.lower()][:3]:
                плохо(f"ошибка страницы: {е[:160]}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: пресет парной сохраняется сам — размер, тип помещения, печь, опция, счётчик, снятая строка и база раздела, "
          "подарок, реквизит; открытие его не переписывает, открытый заново — тот же расчёт; «Проверка» парной — без пунктов "
          "каркаса и бруса, с пунктами печи: не выбрана, мала, велика, камни, Ферингер, облицовка.")


if __name__ == "__main__":
    main()
