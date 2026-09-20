#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цена комплектации на карточке и цена после применения — одно число.

Константин 20.09.2026, двумя снимками: карточка «Комфорт» обещает
8 212 965 ₽, а применённый расчёт даёт 7 968 425 ₽ — разница 244 540 ₽.

Проба открывает калькулятор на живых данных проекта «Хай-тек баня
«Вирджиния 3»» (выборка из базы лежит рядом в `данные.json`), для каждой
комплектации берёт цену с карточки, применяет её и сверяет с итогом расчёта.
Заодно смотрит, не гасит ли применение опции, которые в наборе стоят.
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or "/home/user/-calculator-test")
ЗДЕСЬ = pathlib.Path(__file__).parent
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []
ПРОТИВОРЕЧИЯ = []
ПРОЕКТ = "Проба дом 8×8"


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


СВЕРИТЬ = """async (ключ) => {
  const карточка = calcKomplPrice(ключ);
  const было = Object.assign({}, checkedOptions);
  const наборИды = [...(KOMPL_CONFIGS[ключ] || [])]
    .map(имя => (OPTIONS.find(o => o.name === имя) || {}).id).filter(Boolean);

  window.__вести = [];
  const прежний = window.showToast;
  window.showToast = (с) => { window.__вести.push(String(с)); };

  komplSelected = ключ;
  await applyKompl();
  await new Promise(r => setTimeout(r, 900));
  window.showToast = прежний;

  const итог = (typeof al2ИтогДо === 'function') ? al2ИтогДо() : null;
  const погасли = наборИды.filter(ид => !checkedOptions[ид]);
  Object.keys(было).forEach(и => { checkedOptions[и] = было[и]; });
  return { карточка, итог, вести: (window.__вести || []).slice(),
           погасли: погасли.map(ид => {
             const о = OPTIONS.find(x => x.id === ид) || {};
             return { ид, имя: (о.name || '').slice(0, 44), цена: getOptPrice(о) || 0 };
           }) };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
                                + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(3000)
            стр.evaluate("""async (имя) => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 1200));
              if (typeof loadKitsForCurrentProject === 'function') {
                await loadKitsForCurrentProject();
                await new Promise(r => setTimeout(r, 400));
              }
            }""", ПРОЕКТ)

            есть = стр.evaluate("() => [...(KOMPL_CONFIGS.comfort || [])].length")
            if not есть:
                плохо("набор «Комфорт» не загрузился — сверять нечего")

            for ключ, имя in (("standart", "Стандарт"), ("comfort", "Комфорт")):
                м = стр.evaluate(СВЕРИТЬ, ключ)
                карточка, итог = м.get("карточка"), м.get("итог")
                if карточка is None or итог is None:
                    плохо(f"«{имя}»: цену не удалось снять (карточка {карточка}, итог {итог})")
                    continue
                разница = round(карточка) - round(итог)
                print(f"  {имя}: карточка {round(карточка):,} ₽ · расчёт {round(итог):,} ₽ "
                      f"· разница {разница:,} ₽".replace(",", " "))
                if разница:
                    плохо(f"«{имя}»: карточка обещает {round(карточка)} ₽, "
                          f"а применённый расчёт даёт {round(итог)} ₽ — "
                          f"расхождение {разница} ₽")
                # Погасшая опция — не дефект калькулятора, а противоречие в
                # самом наборе: обе стороны взаимоисключающей пары отмечены.
                # Дефект был бы в молчании: менеджер должен это увидеть.
                погасли = м.get("погасли") or []
                вести = " ".join(м.get("вести") or [])
                for о in погасли:
                    ПРОТИВОРЕЧИЯ.append(f"«{имя}»: «{о['имя']}» — {round(о['цена'])} ₽")
                    if о["имя"][:30] not in вести:
                        плохо(f"«{имя}»: опция «{о['имя']}» выпала из расчёта, "
                              "и сообщение о ней промолчало")
                if погасли and "взаимоисключающ" not in вести:
                    плохо(f"«{имя}»: набор противоречив, а сообщение об этом "
                          "не сказало ни слова")

            # ── То же, но на расчёте, в котором уже поработали ───────────────
            # Сверка на чистом расчёте пропускала целый разряд расхождений:
            # карточка считала цену позиции своим правилом, а итог своим, и
            # расходились они ровно там, где менеджер что-то пометил.
            # Константин 20.09.2026, тремя снимками: карточка «Стандарт»
            # обещает 5 387 147 ₽, применение даёт 5 359 022 ₽, «если делаю
            # сброс и просто загружаю комплектацию, то сумма правильная».
            # Разница — цена позиции, отмеченной подарком: итог считал её
            # нулём, карточка полной ценой.
            грязь = стр.evaluate("""() => {
              const набор = KOMPL_CONFIGS.standart || new Set();
              const вНаборе = OPTIONS.filter(o => !o.included && набор.has(o.name));
              const сЦеной = вНаборе.find(o => (Number(getOptPrice(o)) || 0) > 0);
              const безЦены = вНаборе.find(o => !(Number(getOptPrice(o)) || 0));
              if (сЦеной) giftedOpts.add(сЦеной.id);
              let поле = null;
              if (безЦены) {
                поле = document.getElementById('por_' + безЦены.id);
                if (поле) поле.value = '40000';
              }
              return {
                подарок: сЦеной ? сЦеной.name.slice(0, 40) : null,
                цена: сЦеной ? Math.round(Number(getOptPrice(сЦеной)) || 0) : 0,
                ручная: (безЦены && поле) ? безЦены.name.slice(0, 40) : null,
              };
            }""")
            if not грязь["подарок"]:
                плохо("в наборе «Стандарт» не нашлось платной позиции — "
                      "подарком пометить нечего, разряд расхождений не проверен")
            else:
                хвост = f", ручная сумма у «{грязь['ручная']}»" if грязь["ручная"] else ""
                print(f"  пометки: подарок «{грязь['подарок']}» "
                      f"({грязь['цена']:,} ₽){хвост}".replace(",", " "))
            for ключ, имя in (("standart", "Стандарт"), ("comfort", "Комфорт")):
                м = стр.evaluate(СВЕРИТЬ, ключ)
                карточка, итог = м.get("карточка"), м.get("итог")
                if карточка is None or итог is None:
                    плохо(f"[с пометками] «{имя}»: цену снять не удалось")
                    continue
                разница = round(карточка) - round(итог)
                print(f"  [с пометками] {имя}: карточка {round(карточка):,} ₽ · "
                      f"расчёт {round(итог):,} ₽ · разница {разница:,} ₽"
                      .replace(",", " "))
                if разница:
                    плохо(f"[с пометками] «{имя}»: карточка обещает {round(карточка)} ₽, "
                          f"а расчёт даёт {round(итог)} ₽ — расхождение {разница} ₽: "
                          "подарок или вписанная руками сумма попадает только в "
                          "одно из двух")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if ПРОТИВОРЕЧИЯ:
        print("Противоречия в самих наборах (правятся в редакторе, не в коде):")
        for п_ in ПРОТИВОРЕЧИЯ:
            print("  ·", п_)

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: цена на карточке комплектации совпадает с итогом после её "
          "применения, а о позициях, выпавших по противоречию в наборе, "
          "сказано словами.")


if __name__ == "__main__":
    главная()
