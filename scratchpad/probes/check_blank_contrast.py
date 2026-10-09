#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Бланк» в «Зелёном-графите»: текст листа спецификации читается.

Константин 09.10.2026, снимком листа с телефона: «Тут ещё проверь на
читаемость, мне кажется много зелени». Светлый зелёный тона (#70ad34) на
белом даёт 2,7:1, второй (#83c445) — 2,1:1 при норме 4,5. На экране этот тон
уже переведён на графит (25 и 28.09.2026), лист — нет.

Проба на 390 и 1440 открывает лист спецификации в тоне «Зелёный-графит» и
меряет отношение яркостей у каждого текста, который был зелёным: «Входит»,
сумма раздела, подпись и сумма спец. цены, вторая часть названия, метка «В
подарок», текст примечания на его заливке. Всё — не ниже 4,5:1. Бледные номера
разделов и черты — украшение, их проба не меряет.

Вторая сторона: в другом тоне (синем) «Входит» и сумма раздела остаются цветом
акцента — правило не расползлось на тоны, где акцент и так читается (5:1 и
выше).

    python3 check_blank_contrast.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_glulam_sections as г
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
# Вторая часть названия (зелёная) появляется, только когда в названии есть «…».
ПРОЕКТ = "Баня из клееного бруса «Проба» 6×6"


def таблицы():
    т = г.таблицы()
    for п in т["pricing_projects"]:
        if п["product"] == "glulam":
            п["slug"] = п["name"] = ПРОЕКТ
    return т

МЕРА = """() => {
  const rgb = s => (s.match(/[\\d.]+/g) || []).slice(0, 4).map(Number);
  const лин = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = ([r, g, b]) => 0.2126 * лин(r) + 0.7152 * лин(g) + 0.0722 * лин(b);
  const фон = э => { for (let x = э; x; x = x.parentElement) { const c = rgb(getComputedStyle(x).backgroundColor);
      if (c.length === 3 || (c.length === 4 && c[3] > 0)) return c.slice(0, 3); } return [255, 255, 255]; };
  const к = (сел) => { const э = document.querySelector('#printDoc ' + сел); if (!э) return null;
    const a = L(rgb(getComputedStyle(э).color)), b = L(фон(э));
    return { цвет: getComputedStyle(э).color, к: Math.round((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) * 100) / 100 }; };
  return { 'Входит': к('.bl-v-inc'), 'сумма раздела': к('.bl-sec td.bl-ssum'), 'подпись спец. цены': к('.bl-disc-k'),
           'спец. цена': к('.bl-disc-v'), 'название, вторая часть': к('.bl-title .bl-em'), 'В подарок': к('.bl-gift'),
           'примечание': к('.bl-note td:not(.bl-n)'), акцент: getComputedStyle(document.querySelector('#printDoc .bl-doc')).getPropertyValue('--acc').trim() }; }"""


def открыть(бр, порт, ш, тон):
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
    стр.evaluate("""async (тон) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyTone(тон, false);
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 400));
      selectProjectOption(PROJECTS.findIndex(p => p[0].includes('«Проба»'))); setThickness(1);
      const доп = OPTIONS.find(o => !o.included && o.price);
      if (доп) { if (!checkedOptions[доп.id]) toggleOpt(доп.id); toggleGift(доп.id, { stopPropagation() {}, preventDefault() {} }); }
      const п = document.getElementById('discountPctInput'); if (п) { п.value = '3'; п.dispatchEvent(new Event('input', {bubbles: true})); }
      calc(); await new Promise(r => setTimeout(r, 300)); openPrintPreview(); await new Promise(r => setTimeout(r, 1200)); }""", тон)
    return к, стр, ош


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                к, стр, ош = открыть(бр, порт, ш, "bmsk")
                м_ = стр.evaluate(МЕРА)
                for что, з in м_.items():
                    if что == "акцент":
                        continue
                    if з is None:
                        НАХОДКИ.append(f"{н} на листе нет «{что}» — мерить нечего, проба смотрит мимо")
                    elif з["к"] < 4.5:
                        НАХОДКИ.append(f"{н} «{что}» {з['цвет']}: {з['к']}:1, ждали не ниже 4,5:1")
                print(f"  {н} зелёный-графит: " + ", ".join(f"{что} {з['к']}" for что, з in м_.items() if что != "акцент" and з))
                for о in [о for о in ош if "supabase.co" not in о][:3]:
                    НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
                к.close()
                к, стр, ош = открыть(бр, порт, ш, "blue")
                с_ = стр.evaluate("""() => { const ц = с => getComputedStyle(document.querySelector('#printDoc ' + с)).color;
                  const a = document.createElement('i'); a.style.color = getComputedStyle(document.querySelector('#printDoc .bl-doc')).getPropertyValue('--acc');
                  document.body.appendChild(a); const акц = getComputedStyle(a).color; a.remove();
                  return { акцент: акц, входит: ц('.bl-v-inc'), сумма: ц('.bl-sec td.bl-ssum') }; }""")
                if с_["входит"] != с_["акцент"] or с_["сумма"] != с_["акцент"]:
                    НАХОДКИ.append(f"{н} синий тон: «Входит» и сумма раздела не цветом акцента: {с_}")
                к.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в «Зелёном-графите» каждый бывший зелёный текст листа «Бланк» читается не ниже 4,5:1; "
          "в синем тоне «Входит» и суммы разделов по-прежнему цветом акцента — на 390 и 1440.")


if __name__ == "__main__":
    главная()
