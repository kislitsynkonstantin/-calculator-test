#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Скопировать» у кода пресета — со ссылкой, которая сразу открывает пресет.

Константин 19.10.2026, снимком карточки в «Моих» и скопированной строкой
«Константин Кислицын | Хай-тек баня «Виго» 7,7х8,2 | 19 окт. 2026 г., 21:44 |
Код: 321 910»: «Вот тут по копированию к этому сообщению добавляй ссылку на
пресет, чтобы по нажатию сразу мог человек его загрузить».

Проба держит, на заглушке базы:
  • «Скопировать» в «Моих» кладёт в буфер прежнюю строку «… | Код: 123 456» и
    второй строкой ссылку «<адрес калькулятора>/123456»; у общего пресета —
    так же; без кода ссылки нет;
  • ссылка работает: калькулятор, открытый по ней (?code=, куда переводит
    404.html), открывает окно «Пресеты» на общем пресете с этим кодом — его
    карточка с «Открыть» на виду.

    python3 check_preset_copy_link.py
"""
import json, os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
КОД = "482916"


def плохо(т):
    НАХОДКИ.append(т)


def копия(бр, порт):
    н = "[копия]"
    стр, ошибки = ч.начать(бр, порт, 390, 844, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate("""() => { window.__буфер = []; navigator.clipboard.writeText = т => { window.__буфер.push(т); return Promise.resolve(); };
      openPresetPanel(); switchPresetTab('my'); }""")
    стр.wait_for_timeout(600)
    стр.locator("#presetList .btn-copy-link, .pcard .btn-copy-link").first.click()
    стр.wait_for_timeout(200)
    б = стр.evaluate("() => window.__буфер.slice()")
    адрес = стр.evaluate("() => location.origin")
    if not б:
        плохо(f"{н} «Скопировать» ничего не положило в буфер")
    else:
        строки = б[-1].split("\n")
        if len(строки) != 2 or not re.search(r"\| Код: \d{3} \d{3}$", строки[0]) or строки[1] != f"{адрес}/{код}":
            плохо(f"{н} в «Моих»: ждали строку с кодом и второй строкой {адрес}/{код}: {б[-1]!r}")
    общ = стр.evaluate("""(к) => { _sharedPresets.push({ short_code: к, name: 'Проба общая', author_name: 'Ольга Проверкина', is_public: true,
        created_at: new Date().toISOString(), state: { project: { name: 'Проба дом 8×8' } } });
      return buildSharedPresetCopyText(к); }""", КОД)
    if not общ.endswith(f"\n{адрес}/{КОД}") or "Ольга Проверкина" not in общ:
        плохо(f"{н} у общего пресета: {общ!r}")
    без = стр.evaluate("() => buildMyPresetCopyText(activePresetId, '')")
    if "\n" in без or "/" in без.split("|")[-1]:
        плохо(f"{н} без кода появилась ссылка: {без!r}")
    for о in ошибки[:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def по_ссылке(бр, порт):
    н = "[по ссылке]"
    стр = бр.new_page(viewport={"width": 390, "height": 844})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ч.ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    ряд = {"short_code": КОД, "name": "Проба по ссылке", "author_name": "Ольга Проверкина", "author_id": "u-коллега",
           "is_public": True, "locked": False, "created_at": "2026-10-19T18:00:00Z", "updated_at": "2026-10-19T18:00:00Z",
           "state": {"project": {"name": "Проба дом 8×8"}}}
    стр.add_init_script("(() => { const т = window.__ТАБЛИЦЫ; т.preset_links = (т.preset_links || []).concat([" + json.dumps(ряд, ensure_ascii=False) + "]); })();")
    стр.goto(f"http://127.0.0.1:{порт}/index.html?code={КОД}", wait_until="load")
    стр.wait_for_timeout(4000)
    с = стр.evaluate("""(к) => { const п = document.getElementById('sharedSearchInput'), кар = document.querySelector('#sharedPresetList .shared-pcard[data-scode="' + к + '"]');
      const вид = э => !!(э && э.getBoundingClientRect().width && getComputedStyle(э).visibility !== 'hidden');
      return { вкладка: typeof _presetTab !== 'undefined' ? _presetTab : '', поиск: п ? п.value : null, карточка: вид(кар),
        открыть: !!(кар && кар.querySelector('button')) }; }""", КОД)
    стр.screenshot(path=str(СНИМКИ / "preset-by-link-390.png"))
    if с["вкладка"] != "shared" or с["поиск"] != КОД or not с["карточка"] or not с["открыть"]:
        плохо(f"{н} калькулятор по ссылке не показал пресет {КОД}: {с}")
    for о in ошибки[:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                копия(бр, порт)
                по_ссылке(бр, порт)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Скопировать» кладёт строку с кодом и второй строкой ссылку на пресет — в «Моих» и у общего; "
          "без кода ссылки нет; калькулятор по ссылке открывает «Пресеты» на этом пресете.")


if __name__ == "__main__":
    главная()
