#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Заданная подпись скидки — на подложке цвета темы (вариант Б макета
discount-mode-v1).

Константин 17.10.2026, снимком варианта «Б — плашка»: «Тут ставь такое
выделение, по цвету темы только». Прежде главное поле отмечала одна жирность
серой подписи, и выбор «Спец. цена» или «Скидка» читался плохо.

Держит, во всех девяти палитрах днём и ночью, в обоих режимах:
  • у заданной подписи подложка — ровно токен листа --bl-tint, чернила —
    акцент темы: ночью --bl-acc, днём он же, притемнённый чернилами листа
    (color-mix 55 %), вес не меньше 500; у второй подписи подложки нет,
    чернила — --bl-ink3; цвета берутся из темы, а не вписаны;
  • чернила на подложке читаются: контраст не меньше 4,5 : 1;
  • обе подписи одного вида — прописными, одного кегля;
  • посчитанное поле тише заданного: --bl-ink2 против --bl-ink;
  • текст подписей стоит на одной вертикали, подложка не выходит за поле
    блока и не касается поля ввода справа (390 и 1440 px).

    python3 check_discount_plaque.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
ТОНЫ = ["", "bmsk", "sky", "blue", "amber", "plum", "indigo", "graphite", "titan"]

МЕРА = r"""(режим) => {
  переключитьГлавноеПолеСкидки(режим);
  const цвет = в => { const э = document.createElement('span'); э.style.color = в.startsWith('--') ? 'var(' + в + ')' : в; document.body.appendChild(э); const c = getComputedStyle(э).color; э.remove(); return c; };
  const п = document.getElementById('discPctLab'), с = document.getElementById('discSumLab');
  const гл = режим === 'процент' ? п : с, вт = режим === 'процент' ? с : п;
  const текст = э => { const д = document.createRange(); д.selectNodeContents(э); const r = [...д.getClientRects()].filter(x => x.width)[0]; return r ? r.left : null; };
  const кс = getComputedStyle, блок = document.querySelector('.result-discount').getBoundingClientRect();
  const пв = document.getElementById('discountPctInput'), св = document.getElementById('discountSavedInput');
  const главноеПоле = режим === 'процент' ? пв : св, считаемоеПоле = режим === 'процент' ? св : пв;
  const правыйЗазор = э => { const r = э.getBoundingClientRect(); const сосед = э === п ? пв : св; return сосед.getBoundingClientRect().left - r.right; };
  return {
    tint: цвет('--bl-tint'), acc: document.body.classList.contains('dark') ? цвет('--bl-acc') : цвет('color-mix(in srgb, var(--bl-acc) 55%, var(--bl-ink))'), ink: цвет('--bl-ink'), ink2: цвет('--bl-ink2'), ink3: цвет('--bl-ink3'),
    глФон: кс(гл).backgroundColor, глЦвет: кс(гл).color, глВес: +кс(гл).fontWeight,
    втФон: кс(вт).backgroundColor, втЦвет: кс(вт).color,
    регистр: [кс(п).textTransform, кс(с).textTransform], кегль: [кс(п).fontSize, кс(с).fontSize],
    текстЛево: [текст(п), текст(с)], подложкаЛево: Math.min(п.getBoundingClientRect().left, с.getBoundingClientRect().left),
    блокЛево: блок.left + parseFloat(кс(document.querySelector('.result-discount')).borderLeftWidth || 0),
    зазор: [правыйЗазор(п), правыйЗазор(с)],
    главноеПоле: кс(главноеПоле).color, считаемоеПоле: кс(считаемоеПоле).color,
  };
}"""


def rgb(с):
    # color-mix браузер отдаёт как color(srgb r g b) в долях единицы.
    if с.startswith("color(srgb"):
        return [float(x) * 255 for x in с[с.index("srgb") + 4:с.index(")")].split()[:3]]
    return [float(x) for x in с[с.index("(") + 1:с.index(")")].split(",")[:3]]


def яркость(ч):
    def к(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (к(x) for x in ч)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def контраст(а, б):
    я1, я2 = sorted([яркость(rgb(а)), яркость(rgb(б))], reverse=True)
    return (я1 + 0.05) / (я2 + 0.05)


def прогон(бр, порт, ш, в):
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.evaluate("() => { const п = document.getElementById('discountPctInput'); п.value = '2.9'; calc(); document.querySelector('.result-discount').scrollIntoView({ block: 'center' }); }")
    стр.wait_for_timeout(300)
    for тон in ТОНЫ:
        for ночь in (False, True):
            стр.evaluate("([т, н]) => { if (т) document.documentElement.dataset.tone = т; else delete document.documentElement.dataset.tone; document.body.classList.toggle('dark', н); }", [тон, ночь])
            стр.wait_for_timeout(80)
            for режим in ("процент", "сумма"):
                н = f"[{ш} {тон or 'эталон'}{' ночь' if ночь else ''} {режим}]"
                р = стр.evaluate(МЕРА, режим)
                стр.wait_for_timeout(200)
                р = стр.evaluate(МЕРА, режим)
                if р["глФон"] != р["tint"] or р["глЦвет"] != р["acc"] or р["глВес"] < 500:
                    НАХОДКИ.append(f"{н} заданная подпись не на подложке темы: фон {р['глФон']} (ждали {р['tint']}), цвет {р['глЦвет']} (ждали {р['acc']}), вес {р['глВес']}")
                if р["втФон"] not in ("rgba(0, 0, 0, 0)", "transparent") or р["втЦвет"] != р["ink3"]:
                    НАХОДКИ.append(f"{н} вторая подпись не тихая: фон {р['втФон']}, цвет {р['втЦвет']}")
                кт = контраст(р["глЦвет"], р["глФон"]) if р["глФон"].startswith(("rgb(", "color(")) else 0
                if кт < 4.5:
                    НАХОДКИ.append(f"{н} чернила на подложке читаются плохо: {кт:.2f} : 1")
                if р["регистр"] != ["uppercase", "uppercase"] or р["кегль"][0] != р["кегль"][1]:
                    НАХОДКИ.append(f"{н} подписи разного вида: {р['регистр']}, {р['кегль']}")
                if р["главноеПоле"] != р["ink"] or р["считаемоеПоле"] != р["ink2"]:
                    НАХОДКИ.append(f"{н} посчитанное поле не тише заданного: {р['главноеПоле']} / {р['считаемоеПоле']}")
                if тон == "" and not ночь:
                    if None in р["текстЛево"] or abs(р["текстЛево"][0] - р["текстЛево"][1]) > 1:
                        НАХОДКИ.append(f"{н} текст подписей не на одной вертикали: {р['текстЛево']}")
                    if р["подложкаЛево"] < р["блокЛево"] - 0.5:
                        НАХОДКИ.append(f"{н} подложка выходит за поле блока: {р['подложкаЛево']:.1f} < {р['блокЛево']:.1f}")
                    if min(р["зазор"]) < 4:
                        НАХОДКИ.append(f"{н} подложка касается поля ввода: зазоры {р['зазор']}")
            if тон in ("", "bmsk") and ш in (390, 1440):
                б = стр.locator('.result-discount').bounding_box()
                стр.screenshot(path=str(СНИМКИ / f"скидка-плашка-{ш}-{тон or 'эталон'}{'-ночь' if ночь else ''}.png"),
                               clip={'x': max(0, б['x'] - 8), 'y': max(0, б['y'] - 8), 'width': min(б['width'] + 16, ш - max(0, б['x'] - 8)), 'height': б['height'] + 16})
    if ошибки:
        НАХОДКИ.append(f"[{ш}] ошибки страницы: {ошибки[:2]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                for ш, в in ((390, 844), (1440, 900)):
                    прогон(бр, порт, ш, в)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ[:40]:
            print(" —", т)
        if len(НАХОДКИ) > 40:
            print(f" … и ещё {len(НАХОДКИ) - 40}")
        sys.exit(1)
    print("Чисто: заданная подпись скидки на подложке цвета темы во всех девяти палитрах днём и ночью, "
          "контраст от 4,5 : 1, подписи одного вида, посчитанное поле тише, подложка в поле блока, на 390 и 1440.")


if __name__ == "__main__":
    главная()
