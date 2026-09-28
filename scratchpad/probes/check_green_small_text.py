#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: мелкий зелёный текст «Зелёного-графита» днём читается.

Светлый фирменный зелёный #70ad34 по белому — 2,7:1 при норме 4,5. По снимкам
Константина 28.09.2026 днём в «Зелёном-графите»:
  • в строках опций «Включено в базу», цена и знак ₽ — графит;
  • текст кнопок «Посмотреть» и «Сохранить пресет» — графит;
  • в окне «Комплектация» названия разделов и «Итоговая стоимость» — графит,
    вкладка вида и «Комфорт» (карточка, цена, шапка колонки) — тёмный
    фирменный зелёный #4f7d26.
Черта под разделом остаётся светло-зелёной, ночь и другие цвета оформления
не меняются. Мерится вычисленный цвет и контраст по фону, а не правило CSS.
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

ГРАФИТ = "rgb(36, 39, 31)"
ТЁМНО_ЗЕЛЁНЫЙ = "rgb(79, 125, 38)"
СВЕТЛО_ЗЕЛЁНЫЙ = "rgb(112, 173, 52)"
НАХОДКИ = []

ЗАМЕР = """() => {
  const цв = (э) => э ? getComputedStyle(э).color : null;
  const первый = (с) => [...document.querySelectorAll(с)].find(э => э.getClientRects().length);
  const kp = document.getElementById('kpill_comfort');
  const th = [...document.querySelectorAll('#komplOverlay th')].find(т => т.textContent.trim() === 'Комфорт');
  const итог = [...document.querySelectorAll('#komplTableBody td')].find(т => т.textContent.trim() === 'Итоговая стоимость');
  const раздел = первый('#komplTableBody .ks-name');
  const строка = раздел ? раздел.closest('td') : null;
  return {
    included: цв(первый('.opt-included')),
    price: цв(первый('.opt-price')),
    rub: цв(первый('.por-rub')),
    view: цв(document.getElementById('btnProjectEdit')),
    save: цв(первый('.btn-save-preset')),
    ks_name: цв(раздел),
    ks_rule: строка ? getComputedStyle(строка).borderBottomColor : null,
    total_label: цв(итог),
    tab: цв(document.getElementById('kvtab_all')),
    pill_name: kp ? цв(kp.firstElementChild) : null,
    pill_price: цв(document.getElementById('kpill_comfort_price')),
    th_comfort: цв(th),
  };
}"""

ЖДЁМ_ДЕНЬ = {
    "included": ГРАФИТ, "price": ГРАФИТ, "rub": ГРАФИТ, "view": ГРАФИТ, "save": ГРАФИТ,
    "ks_name": ГРАФИТ, "total_label": ГРАФИТ, "ks_rule": СВЕТЛО_ЗЕЛЁНЫЙ,
    "tab": ТЁМНО_ЗЕЛЁНЫЙ, "pill_name": ТЁМНО_ЗЕЛЁНЫЙ, "pill_price": ТЁМНО_ЗЕЛЁНЫЙ,
    "th_comfort": ТЁМНО_ЗЕЛЁНЫЙ,
}


def замер(стр, тон, ночь):
    стр.evaluate("async ([т, н]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';"
                 " applyTone(т, false); document.body.classList.toggle('dark', н); selectProjectOption(0);"
                 " await new Promise(r => setTimeout(r, 900)); openKompl(); await new Promise(r => setTimeout(r, 1000)); }",
                 [тон, ночь])
    стр.mouse.move(5, 5)
    стр.wait_for_timeout(200)
    р = стр.evaluate(ЗАМЕР)
    стр.evaluate("() => { try { closeKompl(); } catch (e) { document.getElementById('komplOverlay').style.display = 'none'; } }")
    return р


def main():
    с, порт = м.сервер()
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=м.хром(), args=['--no-sandbox'])
        for ширина in (390, 1440):
            стр = бр.new_page(viewport={"width": ширина, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
            день = замер(стр, "bmsk", False)
            print(f"[{ширина} bmsk день]", день)
            for ключ, ждём in ЖДЁМ_ДЕНЬ.items():
                if день.get(ключ) != ждём:
                    НАХОДКИ.append(f"[{ширина}] bmsk днём {ключ}: {день.get(ключ)}, ждали {ждём}")
            ночь = замер(стр, "bmsk", True)
            print(f"[{ширина} bmsk ночь]", ночь)
            for ключ, цвет in ночь.items():
                if цвет in (ГРАФИТ, ТЁМНО_ЗЕЛЁНЫЙ):
                    НАХОДКИ.append(f"[{ширина}] bmsk ночью {ключ} стал {цвет} — на тёмном фоне его не видно")
            бирюза = замер(стр, "teal", False)
            for ключ, цвет in бирюза.items():
                if цвет in (ГРАФИТ, ТЁМНО_ЗЕЛЁНЫЙ):
                    НАХОДКИ.append(f"[{ширина}] бирюза днём {ключ} стал {цвет} — правка протекла в другой цвет")
            if ошибки:
                НАХОДКИ.append(f"[{ширина}] ошибки скрипта: {ошибки}")
            стр.close()
        бр.close()
    с.shutdown()
    if НАХОДКИ:
        print("\nНАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("\nЧисто: днём в «Зелёном-графите» мелкий текст опций, кнопок и окна комплектаций — графит "
          "или тёмный зелёный, черта раздела светлая; ночь и бирюза не тронуты — на 390 и 1440.")


if __name__ == "__main__":
    main()
