#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Автоматика: предложения Г1–Г8 разбора автоматики клеёного бруса.

Константин 09.10.2026: «Г делай как предлагаешь, если что, потом поправим».
Проверяется поведением на экране:

  Брус
  • Г1 — у сечения 125 «утепление 200 мм с изменением конструктива» делает
    базовое утепление 200 мм и лаги 45×195; снятая — возвращает 150 и
    45×145; у сечения 160 строка закрыта, отмеченная при 125 снимается;
  • Г2 — доска 36 мм снимает базовую 27 мм и с фанерой отмечается вместе;
  • Г3 — сборка парной одного размера, липа одной строкой, за печкой одно
    из трёх;
  • Г4 — топка из парной: набор печи не ставит установку с топкой из
    комнаты отдыха и не называет её в сообщении; печь не Ферингер закрывает
    кассеты; без печи кассеты открыты;
  • Г5 — ленточный фундамент снимает выезд инженера по свайному, пробное
    бурение остаётся; наш фундамент снимает приёмку фундамента заказчика;
  • Г6 — пол под ламинат: заказчика или эконом; Г7 — лестница на террасу
    снимает временные ступени; Г8 — у террасной доски переключатель пород.

  Каркас (те же правила, Г2, Г4, Г5)
  • доска 36 мм снимает доску 27 мм жилой зоны, фанера с ней — вместе;
  • топка из парной: набор печи без топки из комнаты отдыха;
  • Grill'D закрывает кассеты Ферингера; плитный — выезд инженера.

Данные выдуманные: тестовый репозиторий открыт.

    python3 check_auto_g.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
import check_glulam_auto as а
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ЖДАТЬ = а.НАХОДКИ  # общая копилка с помощником ждать()


def таблицы():
    т = а.таблицы()
    кар = lambda ид, сек, цена: {"product": "frame", "option_id": ид, "name": "x", "section": сек,
                                 "included": False, "price": цена, "formula": None, "status": None, "sort": 1}
    брус = lambda ид, сек, имя, цена, общая=None, вкл=False, sort=1000: {
        "product": "glulam", "option_id": ид, "name": имя, "section": сек, "included": вкл,
        "price": цена, "formula": None, "status": None, "sort": sort, "shared_option": общая}
    т["pricing_options"] += [кар(ид, сек, 20000 + н) for н, (ид, сек) in enumerate([
        ("st2", "stove"), ("st25", "stove"), ("st29", "stove"), ("s32", "steam"),
        ("i5", "interior"), ("fr12", "frame"), ("f11", "foundation"), ("f5", "foundation")])]
    т["pricing_options"] += [
        брус("kb_bp_fd_2", "foundation", "Приёмка фундамента заказчика (проба)", None, вкл=True, sort=5),
        брус("kb_bp_fd_3", "foundation", "Выезд инженера по свайному (проба)", None, вкл=True, sort=6),
        брус("kb_bp_fd_4", "foundation", "Пробное бурение (проба)", None, вкл=True, sort=7),
        брус("kb_bp_fr_4", "frame", "Лаги пола (проба)", None, вкл=True, sort=100),
        брус("kb_bp_in_2", "insulation", "Утепление потолка (проба)", None, вкл=True, sort=200),
        брус("kb_bp_in_3", "insulation", "Утепление пола (проба)", None, вкл=True, sort=201),
        брус("kb_in1", "insulation", "Утепление 200 мм с изменением конструктива (проба)", 40000, sort=202),
        брус("kb_i5", "interior", "Доска 36 мм (проба)", 16000, sort=702),
        брус("kb_i6", "interior", "Ламинат заказчика (проба)", 7000, sort=703),
        брус("kb_i7", "interior", "Ламинат эконом (проба)", 9000, sort=704),
    ] + [брус("kb_s" + str(н), "steam", "Парная " + str(н) + " (проба)", 100000 + н, sort=800 + н) for н in range(1, 12)] + [
        брус("kb_s25", "steam", "Фиброцемент прямой (проба)", 34000, sort=825),
        брус("kb_s26", "steam", "Фиброцемент угловой (проба)", 53000, sort=826),
        брус("kb_s32", "steam", "Талькохлорит (проба)", None, "s32", sort=832),
        брус("kb_st2", "stove", "Топка из парной (проба)", None, "st2", sort=899),
        брус("kb_st42", "stove", "Печь Grill'D (проба)", None, "st25", sort=908),
        брус("kb_st34", "stove", "Кассеты Ферингер (проба)", None, "st29", sort=909),
        брус("kb_bp_xt_5", "extra", "Ступени временные (проба)", None, вкл=True, sort=1500),
        брус("kb_e6", "extra", "Лестница на террасу (проба)", 30000, sort=1501),
    ]
    return т


def прогон(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, "
                        + json.dumps(таблицы(), ensure_ascii=False) + ");"
                        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async (п) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      await loadPricing('frame', true); await new Promise(r => setTimeout(r, 300));
      appSettings.showAutoToasts = true;
      window.__тосты = []; const _т = showToast; showToast = (m, ...а) => { __тосты.push(String(m)); return _т(m, ...а); };
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0] === п)); }""", а.П_ТЕР)
    ждать = а.ждать
    имя = lambda ид: стр.evaluate("(ид) => { const э = document.querySelector('#lbl_' + ид + ' .opt-name'); return [(getOpt(ид) || {}).name || '', э ? э.textContent.trim() : '']; }", ид)

    # Г1 — сечение 125 и утепление 200 мм
    стр.evaluate("() => setThickness(0)")
    ждать(стр, ["kb_in1"], [False, False], "Г1 сечение 125: утепление 200 мм")
    стр.evaluate("() => toggleOpt('kb_in1')")
    for ид, слово in (("kb_bp_in_2", "200 мм"), ("kb_bp_in_3", "200 мм"), ("kb_bp_fr_4", "45×195")):
        и = имя(ид)
        if not all(слово in х for х in и):
            НАХОДКИ.append(f"Г1 сечение 125, утепление 200 мм отмечено: «{и}», ждали «{слово}» в документе и на экране")
    стр.evaluate("() => toggleOpt('kb_in1')")
    for ид, слово in (("kb_bp_in_2", "150 мм"), ("kb_bp_fr_4", "45×145")):
        и = имя(ид)
        if not all(слово in х for х in и):
            НАХОДКИ.append(f"Г1 утепление 200 мм снято: «{и}», ждали «{слово}»")
    стр.evaluate("() => { toggleOpt('kb_in1'); setThickness(1); }")
    ждать(стр, ["kb_in1"], [False, True], "Г1 сечение 160 после отмеченного при 125: утепление 200 мм")
    if "45×195" not in имя("kb_bp_fr_4")[0]:
        НАХОДКИ.append(f"Г1 сечение 160: лаги «{имя('kb_bp_fr_4')[0]}», ждали 45×195 базы")

    # Г2 — доска 36 мм
    стр.evaluate("() => toggleOpt('kb_i5')")
    ждать(стр, ["kb_bp_it_1"], [False, True], "Г2 доска 36 мм: доска 27 мм")
    стр.evaluate("() => toggleOpt('kb_i4')")
    ждать(стр, ["kb_i4", "kb_i5"], [True, False], "Г2 фанера и доска 36 мм вместе")
    стр.evaluate("() => { toggleOpt('kb_i4'); toggleOpt('kb_i5'); }")

    # Г3 — парная
    стр.evaluate("() => { toggleOpt('kb_s1'); toggleOpt('kb_s4'); toggleOpt('kb_s25'); }")
    ждать(стр, ["kb_s2", "kb_s3", "kb_s5", "kb_s11", "kb_s26", "kb_s32"], [False, True], "Г3 сборка, липа, фиброцемент выбраны")
    стр.evaluate("() => { toggleOpt('kb_s1'); toggleOpt('kb_s4'); toggleOpt('kb_s25'); }")

    # Г4 — топка и принадлежности
    ждать(стр, ["kb_st34"], [False, False], "Г4 без печи: кассеты Ферингер")
    стр.evaluate("() => { toggleOpt('kb_st2'); __тосты.length = 0; toggleOpt('kb_st21'); }")
    ждать(стр, ["kb_st1"], [False, True], "Г4 топка из парной и дровяная печь: топка из комнаты отдыха")
    ждать(стр, ["kb_st2", "kb_st10"], [True, False], "Г4 топка из парной и дровяная печь: топка из парной и дымоход")
    тосты = стр.evaluate("() => __тосты.slice()")
    if any("из комнаты отдыха" in т for т in тосты):
        НАХОДКИ.append(f"Г4 сообщение набора называет топку из комнаты отдыха, которую набор не ставил: {тосты}")
    стр.evaluate("() => { toggleOpt('kb_st21'); toggleOpt('kb_st2'); toggleOpt('kb_st42'); }")
    ждать(стр, ["kb_st34"], [False, True], "Г4 печь Grill'D: кассеты Ферингер")
    стр.evaluate("() => toggleOpt('kb_st42')")

    # Г5 — фундамент
    стр.evaluate("() => toggleOpt('kb_f6')")
    ждать(стр, ["kb_bp_fd_3", "kb_bp_fd_2"], [False, True], "Г5 ленточный: выезд инженера по свайному, приёмка фундамента заказчика")
    ждать(стр, ["kb_bp_fd_4"], [True, False], "Г5 ленточный: пробное бурение")
    стр.evaluate("() => { toggleOpt('kb_f6'); toggleOpt('kb_f1'); }")
    ждать(стр, ["kb_bp_fd_3", "kb_bp_fd_4"], [True, False], "Г5 свайно-винтовой: выезд инженера и пробное бурение")
    ждать(стр, ["kb_bp_fd_2"], [False, True], "Г5 свайно-винтовой: приёмка фундамента заказчика")
    стр.evaluate("() => toggleOpt('kb_f1')")

    # Г6, Г7
    стр.evaluate("() => { toggleOpt('kb_i6'); toggleOpt('kb_e6'); }")
    ждать(стр, ["kb_i7", "kb_bp_xt_5"], [False, True], "Г6, Г7 ламинат заказчика и лестница: ламинат эконом, временные ступени")
    стр.evaluate("() => { toggleOpt('kb_i6'); toggleOpt('kb_e6'); }")
    ждать(стр, ["kb_bp_xt_5"], [True, False], "Г7 лестница снята: временные ступени")

    # Г8 — порода террасной доски
    есть = стр.evaluate("() => !!document.getElementById('ovar_kb_bp_ex_3_1')")
    if not есть:
        НАХОДКИ.append("Г8 у террасной доски бруса нет переключателя пород")
    else:
        стр.evaluate("() => setOptVariant('kb_bp_ex_3', 1)")
        и = имя("kb_bp_ex_3")
        if и != ["Террасная доска — импрегнированная доска сосна 32 мм"] * 2:
            НАХОДКИ.append(f"Г8 выбрана импрегнированная: «{и}»")
        стр.evaluate("() => setOptVariant('kb_bp_ex_3', 0)")

    # Каркас
    стр.evaluate("""async () => { await switchTech('frame'); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(0); toggleOpt('i5'); }""")
    ждать(стр, ["i1"], [False, True], "каркас, доска 36 мм: доска 27 мм жилой зоны")
    стр.evaluate("() => toggleOpt('fr12')")
    ждать(стр, ["fr12", "i5"], [True, False], "каркас, фанера и доска 36 мм вместе")
    стр.evaluate("() => { toggleOpt('fr12'); toggleOpt('i5'); toggleOpt('st2'); toggleOpt('st16'); }")
    ждать(стр, ["st1"], [False, True], "каркас, топка из парной и печь: топка из комнаты отдыха")
    ждать(стр, ["st6"], [True, False], "каркас, топка из парной и печь: дымоход")
    стр.evaluate("() => { toggleOpt('st16'); toggleOpt('st2'); toggleOpt('st25'); }")
    ждать(стр, ["st29"], [False, True], "каркас, Grill'D: кассеты Ферингер")
    стр.evaluate("() => { toggleOpt('st25'); toggleOpt('f11'); }")
    ждать(стр, ["f2"], [False, True], "каркас, плитный: выезд инженера по свайному")
    ждать(стр, ["f3"], [True, False], "каркас, плитный: пробное бурение")
    if ош:
        НАХОДКИ.append(f"ошибки страницы: {ош[:3]}")
    стр.close()


def main():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    все = НАХОДКИ + ЖДАТЬ
    if все:
        for н in все:
            print("✗", н)
        sys.exit(1)
    print("✓ Г1–Г8: утепление 200 по сечению, пол, парная, топка и Ферингер, фундамент, ламинат, ступени, порода доски; каркас — те же правила")


if __name__ == "__main__":
    main()
