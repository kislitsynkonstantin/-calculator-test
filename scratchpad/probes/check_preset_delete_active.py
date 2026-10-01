#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Удалили открытый пресет — калькулятор это показывает.

Константин 29.09.2026, снимком шапки: «пресет удалил, а тут продолжает
висеть — нет обратной связи». Открытый пресет удалили из окна «Пресеты», а
точка у кнопки «Пресеты» горела, на кнопке стояло облако, и значок мини-окна
молча пропадал.

Проба на 390 и 1440 держит:
  • после удаления открытого пресета он больше не открыт: на кнопке
    «Пресеты» дискета (есть проект, сохранять есть что);
  • значок мини-окна — «Не сохранён», и раскрывается с «Сохранить»;
  • сообщение говорит, что расчёт остался, но больше не сохраняется;
  • удаление другого, не открытого пресета открытый не трогает.

    python3 check_preset_delete_active.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

СОСТОЯНИЕ = """() => { const з = document.getElementById('presetChip');
  const ико = document.getElementById('presetsIco');
  return { открыт: activePresetId, надпись: (з.querySelector('.pc-lbl') || {}).textContent || '',
           класс: з.className, дискета: !!ико && ико.innerHTML.includes('17 21 17 13'), облако: !!ико && ико.innerHTML.includes('M9.3 13.6'),
           тосты: (window.__тосты || []).slice(-2) }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    ид = стр.evaluate("() => activePresetId")
    if not ид:
        НАХОДКИ.append(f"{н} пресет не открылся"); стр.close(); return
    # второй пресет — чужой для этой проверки: его удаление открытый не трогает
    стр.evaluate("""() => { const все = loadAllPresets(); все['preset_другой'] = { id: 'preset_другой', name: 'Другой', savedAt: new Date().toISOString(), state: {} };
      saveAllPresets(все); }""")
    стр.evaluate("() => deletePreset('preset_другой')"); стр.wait_for_timeout(300)
    стр.locator("#confirmDialogOk").click(); стр.wait_for_timeout(600)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["открыт"] != ид or с["надпись"] != "Мой пресет":
        НАХОДКИ.append(f"{н} удаление другого пресета сбило открытый: {с}")
    # удаляем открытый
    стр.evaluate("(ид) => deletePreset(ид)", ид); стр.wait_for_timeout(300)
    стр.locator("#confirmDialogOk").click(); стр.wait_for_timeout(900)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["открыт"] or not с["дискета"] or с["облако"]:
        НАХОДКИ.append(f"{н} удалённый пресет остался открытым: {с}")
    if "Не сохранён" not in с["надпись"]:
        НАХОДКИ.append(f"{н} значок мини-окна не стал «Не сохранён»: «{с['надпись']}» {с['класс']}")
    if not any("больше не сохраняется" in т for т in с["тосты"]):
        НАХОДКИ.append(f"{н} сообщение не говорит, что расчёт больше не сохраняется: {с['тосты']}")
    # Значка может не быть вовсе (так было до правки) — тогда нажимать нечего.
    стр.evaluate("() => { const з = document.getElementById('presetChip'); const т = з && !з.classList.contains('pc-hide') && з.querySelector('.pc-body'); if (т) т.click(); }")
    стр.wait_for_timeout(350)
    if not стр.evaluate("() => !!document.querySelector('#presetChipCard.show [data-act=\"save\"]')"):
        НАХОДКИ.append(f"{н} мини-окно после удаления не предлагает «Сохранить»")
    стр.screenshot(path=str(м.СНИМКИ / f"delete-active-{ш}.png"))
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
    print("Чисто: удалённый открытый пресет перестаёт быть открытым — на «Пресетах» дискета, значок "
          "«Не сохранён» с «Сохранить», сообщение об этом говорит; удаление другого пресета открытый не трогает — на 390 и 1440.")


if __name__ == "__main__":
    главная()
