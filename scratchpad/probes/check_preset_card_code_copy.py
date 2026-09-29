#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Код пресета в мини-окне копируется двойным нажатием — одни цифры.

Константин 29.09.2026, снимком мини-окна своего пресета: «тут тоже двойное
нажатие на код пресета сделай, чтобы копировался в буфер только цифры кода» —
как на карточке в окне «Пресеты».

Проба держит на 1440 (двойной щелчок) и на телефоне 390 (два касания):
  • у своего пресета, у чужого общего и у пресета по коду в мини-окне код
    копируется в буфер шестью цифрами — без пробела и без слова «код»;
  • после копирования приходит сообщение «Код скопирован».

    python3 check_preset_card_code_copy.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []

БУФЕР = """() => { window.__буфер = []; const был = navigator.clipboard && navigator.clipboard.writeText;
  try { navigator.clipboard.writeText = (т) => { window.__буфер.push(String(т)); return Promise.resolve(); }; } catch (e) {} }"""


def код_в_окне(стр):
    return стр.evaluate("() => { const э = document.querySelector('#presetChipCard.show .pc-code'); return э ? э.dataset.code : null; }")


def нажать_дважды(стр, касание):
    э = стр.locator("#presetChipCard.show .pc-code").first
    if касание:
        б = э.bounding_box()
        x, y = б["x"] + б["width"] / 2, б["y"] + б["height"] / 2
        стр.touchscreen.tap(x, y); стр.wait_for_timeout(120); стр.touchscreen.tap(x, y)
    else:
        э.dblclick()
    стр.wait_for_timeout(400)
    return стр.evaluate("() => (window.__буфер || []).slice(-1)[0] || null"), стр.evaluate("() => (window.__тосты || []).slice(-1)[0] || ''")


def проверить(н, что, стр, касание):
    ждём = код_в_окне(стр)
    if not ждём:
        НАХОДКИ.append(f"{н} {что}: в мини-окне нет кода, который можно скопировать"); return
    буфер, тост = нажать_дважды(стр, касание)
    if буфер != ждём or not (буфер or "").isdigit() or len(буфер) != 6:
        НАХОДКИ.append(f"{н} {что}: в буфере «{буфер}», ждали шесть цифр «{ждём}»")
    if "Код скопирован" not in тост:
        НАХОДКИ.append(f"{н} {что}: нет сообщения о копировании (последнее: «{тост}»)")


def прогон(бр, порт, ш, в, касание):
    н = f"[{ш}{' касание' if касание else ''}]"
    if касание:
        контекст = бр.new_context(viewport={"width": ш, "height": в}, has_touch=True, is_mobile=True)

        class Страница:
            def new_page(self, **_):
                return контекст.new_page()
        стр, ошибки = к.начать(Страница(), порт, ш, в, False)
    else:
        стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.evaluate(БУФЕР)
    к.открыть(стр); стр.wait_for_timeout(300)
    проверить(н, "свой пресет", стр, касание)
    for код, публ, что in (("111222", True, "чужой общий"), ("365484", False, "по коду")):
        стр.evaluate("""([код, публ]) => { закрытьКарточкуЗначка(); _sharedPresets.push({ short_code: код, id: код, name: 'Проба ' + код, author_name: 'Сергей Волков',
          author_id: 'u-другой', is_public: публ, visibility: публ ? 'public' : 'private', locked: true, created_at: '2026-09-22T13:05:00Z', updated_at: '2026-09-22T13:05:00Z', state: {} });
          openSharedPreset(код); }""", [код, публ])
        стр.wait_for_timeout(1500)
        к.открыть(стр); стр.wait_for_timeout(300)
        проверить(н, что, стр, касание)
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 1440, 900, False)
            прогон(бр, порт, 390, 844, True)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: код в мини-окне — у своего, чужого общего и пресета по коду — копируется двойным нажатием шестью "
          "цифрами и об этом говорит сообщение — щелчком на 1440 и касаниями на телефоне.")


if __name__ == "__main__":
    главная()
