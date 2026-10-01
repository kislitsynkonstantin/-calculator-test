#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договор подряда (КАР) — в оформлении «Бланк», во всех цветовых схемах.

Константин 01.10.2026, снимками окна печати: «переработай договор в теме
оформления Бланк — во всех цветовых схемах. Сейчас там залит только основной
договор на каркас (-КАР)». Договор стал родней Приложению № 2: те же
переменные палитры, шрифты, шапка с логотипом, разделы с крупным номером и
чертой, таблицы на линейках без коробок.

Проба в каждой схеме из ТОНЫ_ПОДПИСИ, на 390, 768 и 1440, с настоящими
шрифтами, держит:
  • Geologica и Unbounded легли (ширина строки не совпадает с подменной);
    вшитой Helvetica в документе нет;
  • ничего не вылезает за лист, горизонтальной прокрутки нет;
  • черта раздела — цветом схемы (--br-28 этой схемы), и у разных схем она
    разная; у «Зелёного-графита» заголовок раздела графитовый;
  • утверждённые блоки (01.10.2026, макет contract-final-v1: «макет
    утверждаю, внедряй в калькулятор»): стороны и реквизиты — строками
    «подпись — значение», «Подрядчик» и «Заказчик» в одном ряду шире 600 px
    и столбиком уже; участок и объект — четырьмя ячейками; платежи —
    «Платёж № 1 | сумма | срок», итог равен сумме строк; часы работы и
    адреса почты — ячейками; гарантия — шкалой; подписи сторон внизу;
    прежних таблиц нет, надписи «Каркасный дом / Баня» нет;
  • участок и объект, платежи, часы, адреса почты и шкала гарантии стоят
    левой границей по кромке текста пунктов, а не по номерам (01.10.2026:
    «границу слева от линии поставь, синхронно сделай»);
  • отметки шкалы гарантии стоят центром на начале и конце дорожки
    (у шкалы был свой кегль, и её колонки уезжали от колонок строк);
  • у подписей сторон нет заливки — в «Бланке» заливка только по исключению;
  • Safari не раздувает текст сам (text-size-adjust 100%);
  • буквенный список — русскими буквами «а) б) в)»;
  • на узком экране текст пунктов по левому краю, в печати — по ширине;
  • печать: в PDF шрифты Geologica и Unbounded, страниц не больше 13;
  • «Печать / PDF»: печать зовётся, когда в кадре уже легли Geologica и
    Unbounded (шрифты теперь с Google Fonts, а не вшиты). Задержку сети проба
    не изображает — задержанный ответ в синхронном Playwright держит и саму
    пробу, — поэтому ожидание здесь проверено на присутствие, а не на время.

    python3 check_contract_blank.py
"""
import pathlib, re, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []

МЕРА = """() => {
  const стр = document.querySelector('.page'); const r = стр.getBoundingClientRect();
  const вылез = [...стр.querySelectorAll('*')].filter(э => { const q = э.getBoundingClientRect(); return q.width && (q.right > r.right + 1 || q.left < r.left - 1); })
    .map(э => (э.className || э.tagName) + '').slice(0, 4);
  const ш = s => { const e = document.createElement('span'); e.style.cssText = 'font:16px ' + s + ';position:absolute;visibility:hidden;white-space:nowrap';
    e.textContent = 'Договор подряда 0123'; document.body.appendChild(e); const w = e.offsetWidth; e.remove(); return w; };
  const h2 = document.querySelector('h2.section'), hs = getComputedStyle(h2);
  const п = document.querySelectorAll('.v1-two')[0] ? document.querySelectorAll('.v1-two')[0].querySelectorAll('.v1-party') : [];
  const рекв = [...document.querySelectorAll('.v1-party > .ey')].map(э => getComputedStyle(э).backgroundColor);
  const число = т => parseInt(String(т).replace(/\D/g, ''), 10) || 0;
  const суммы = [...document.querySelectorAll('.g1 .am .amt')].map(э => число(э.firstChild ? э.firstChild.textContent : э.textContent));
  const итог = document.querySelector('.g1 .ta .amt');
  const блоки = { стороны: document.querySelectorAll('.v1-two').length, объект: document.querySelectorAll('.o2 .c').length, платежи: document.querySelectorAll('.g1').length,
    ячейки: document.querySelectorAll('.cells').length, шкала: document.querySelectorAll('.bars .bar').length, подписи: document.querySelectorAll('.v1-sign .line').length,
    старые: document.querySelectorAll('.parties,.requisites,.emails,.pay-table,.warranty-table,.hours-table,.obj-table').length,
    надзаголовок: document.body.textContent.includes('Каркасный дом / Баня') };
  const буквы = [...document.querySelectorAll('ol.lettered > li')].slice(0, 3).map(э => getComputedStyle(э, '::before').content);
  const пункт = getComputedStyle(document.querySelector('.clause')).textAlign;
  // Кромка текста пункта: левый край пункта плюс его отступ слева.
  const пн = [...document.querySelectorAll('p.clause:not(.sub)')].find(э => э.querySelector('.clause-num'));
  const кромка = пн.getBoundingClientRect().left + parseFloat(getComputedStyle(пн).paddingLeft);
  // Шкала гарантии: отметка «0» — центром на начале дорожки, последняя — на её конце.
  const дор = document.querySelector('.bar .tr').getBoundingClientRect(), от = [...document.querySelectorAll('.scale .ticks span')].map(э => { const q = э.getBoundingClientRect(); return (q.left + q.right) / 2; });
  const шкала = [Math.round(от[0] - дор.left), Math.round(от[от.length - 1] - дор.right)];
  const сдвиг = [...document.querySelectorAll('.o2,.g1,.cells,.bars')].map(э => Math.round(э.getBoundingClientRect().left - кромка));
  const пал = document.createElement('span'); пал.style.color = 'var(--br-28)'; document.body.appendChild(пал); const br28 = getComputedStyle(пал).color; пал.remove();
  return { скролл: document.documentElement.scrollWidth > innerWidth + 1, вылез, гео: ш('Geologica') !== ш('serif'), анб: ш('Unbounded') !== ш('serif'),
    helvetica: document.documentElement.outerHTML.includes('Helvetica Neue Embedded'),
    черта: hs.borderBottomColor, заголовок: hs.color, br28,
    рядом: п.length === 2 && Math.abs(п[0].getBoundingClientRect().top - п[1].getBoundingClientRect().top) < 2,
    столбиком: п.length === 2 && п[1].getBoundingClientRect().top >= п[0].getBoundingClientRect().bottom - 1,
    рекв, буквы, пункт, сдвиг, шкала, блоки, суммы, итог: итог ? число(итог.firstChild.textContent) : null,
    размер: getComputedStyle(document.documentElement).webkitTextSizeAdjust || getComputedStyle(document.documentElement).textSizeAdjust };
}"""


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            кт = СоШрифтами(бр)
            стр, ошибки = к.начать(кт, порт, 1440, 900, False)
            тоны = стр.evaluate("() => Object.keys(ТОНЫ_ПОДПИСИ)")
            черты = {}
            for тон in тоны:
                html = стр.evaluate("(т) => { applyTone(т, false); return сПалитрой(buildContractHtmlKar(getContractVarsKar())); }", тон)
                for ш in (390, 768, 1440):
                    н = f"[{тон} {ш}]"
                    д = кт.new_page(viewport={"width": ш, "height": 900})
                    д.set_content(html, wait_until="load"); д.wait_for_timeout(700)
                    р = д.evaluate(МЕРА)
                    if not р["гео"] or not р["анб"]:
                        НАХОДКИ.append(f"{н} шрифты не легли: Geologica {р['гео']}, Unbounded {р['анб']}")
                    if р["helvetica"]:
                        НАХОДКИ.append(f"{н} в документе осталась вшитая Helvetica")
                    if р["скролл"] or р["вылез"]:
                        НАХОДКИ.append(f"{н} вылезает за лист: прокрутка {р['скролл']}, {р['вылез']}")
                    if р["черта"] != р["br28"]:
                        НАХОДКИ.append(f"{н} черта раздела {р['черта']} не цветом схемы {р['br28']}")
                    if тон == "bmsk" and р["заголовок"] not in ("rgb(36, 39, 31)",):
                        НАХОДКИ.append(f"{н} у «Зелёного-графита» заголовок раздела не графитовый: {р['заголовок']}")
                    if ш > 600 and not р["рядом"] or ш <= 600 and not р["столбиком"]:
                        НАХОДКИ.append(f"{н} «Подрядчик» и «Заказчик»: на {ш} px ждали {'в один ряд' if ш > 600 else 'столбиком'}")
                    б_ = р["блоки"]
                    if б_ != {"стороны": 2, "объект": 4, "платежи": 1, "ячейки": 2, "шкала": 3, "подписи": 2, "старые": 0, "надзаголовок": False}:
                        НАХОДКИ.append(f"{н} блоки договора не те: {б_}")
                    if р["суммы"] and р["итог"] != sum(р["суммы"]):
                        НАХОДКИ.append(f"{н} итог платежей {р['итог']} не равен сумме строк {sum(р['суммы'])}")
                    if any(abs(х) > 1 for х in р["сдвиг"]):
                        НАХОДКИ.append(f"{н} блоки внутри разделов не по кромке текста пунктов, сдвиг: {р['сдвиг']}")
                    if any(abs(х) > 2 for х in р["шкала"]):
                        НАХОДКИ.append(f"{н} отметки шкалы гарантии не на дорожке: «0» и последняя смещены на {р['шкала']} px")
                    if р["размер"] != "100%":
                        НАХОДКИ.append(f"{н} text-size-adjust не 100%: {р['размер']}")
                    if any(ц not in ("rgba(0, 0, 0, 0)", "transparent") for ц in р["рекв"]):
                        НАХОДКИ.append(f"{н} у шапок реквизитов заливка: {р['рекв']}")
                    if р["буквы"][:3] != ['"а)"', '"б)"', '"в)"']:
                        НАХОДКИ.append(f"{н} буквенный список не русскими буквами: {р['буквы']}")
                    if ш == 390 and р["пункт"] != "left":
                        НАХОДКИ.append(f"{н} на узком экране пункты выключены «{р['пункт']}», ждали по левому краю")
                    черты[тон] = р["черта"]
                    if ш == 1440 and тон in ("teal", "bmsk", "plum"):
                        д.screenshot(path=str(м.СНИМКИ / f"contract-{тон}-{ш}.png"))
                    д.close()
                if тон in ("teal", "bmsk"):
                    д = кт.new_page(); д.set_content(html, wait_until="load"); д.wait_for_timeout(700)
                    д.emulate_media(media="print")
                    if д.evaluate("() => getComputedStyle(document.querySelector('.clause')).textAlign") != "justify":
                        НАХОДКИ.append(f"[{тон} печать] пункты не по ширине")
                    with tempfile.NamedTemporaryFile(suffix=".pdf") as ф:
                        д.pdf(path=ф.name, format="A4", prefer_css_page_size=True, print_background=True)
                        сырьё = pathlib.Path(ф.name).read_bytes()
                    шрифты = set(x.decode() for x in re.findall(rb"/FontName\s*/[A-Z]{6}\+([A-Za-z0-9\-_]+)", сырьё))
                    страниц = len(re.findall(rb"/Type\s*/Page[^s]", сырьё))
                    if not any("Geologica" in x for x in шрифты) or not any("Unbounded" in x for x in шрифты):
                        НАХОДКИ.append(f"[{тон} печать] в PDF не те шрифты: {sorted(шрифты)}")
                    if страниц > 13 or страниц < 8:
                        НАХОДКИ.append(f"[{тон} печать] страниц {страниц}, ждали 8–13")
                    д.close()
            # Печать договора — после шрифтов.
            стр.evaluate("""() => { window.__печать = null;
              new MutationObserver((сп, н) => { const ф = document.getElementById('contractPrintFrame'); if (!ф || ф.__пойман) return; ф.__пойман = true;
                ф.contentWindow.print = () => { const д = ф.contentDocument;
                  const ш = s => { const e = д.createElement('span'); e.style.cssText = 'font:16px ' + s + ';position:absolute;visibility:hidden;white-space:nowrap';
                    e.textContent = 'Договор подряда 0123'; д.body.appendChild(e); const w = e.offsetWidth; e.remove(); return w; };
                  window.__печать = { гео: ш('Geologica') !== ш('serif'), анб: ш('Unbounded') !== ш('serif') }; };
              }).observe(document.body, { childList: true });
              printContractKar(); }""")
            for _ in range(40):
                стр.wait_for_timeout(200)
                if стр.evaluate("() => window.__печать"): break
            п = стр.evaluate("() => window.__печать")
            if not п or not п["гео"] or not п["анб"]:
                НАХОДКИ.append(f"печать договора: зовётся без шрифтов или не зовётся вовсе: {п}")
            if len(set(черты.values())) < max(3, len(тоны) - 2):
                НАХОДКИ.append(f"черта раздела почти одна на все схемы: {черты}")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                НАХОДКИ.append(f"ошибка страницы: {о[:160]}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: договор подряда — в «Бланке» во всех схемах: шрифты легли, вшитой Helvetica нет, ничего не вылезает, черта "
          "раздела цветом схемы, утверждённые блоки на месте, итог платежей сходится, стороны в один ряд (на телефоне столбиком), подписи сторон без заливки, буквы русские, на узком экране по левому краю, "
          "в печати по ширине; PDF с Geologica и Unbounded, печать — после шрифтов — на 390, 768 и 1440.")


if __name__ == "__main__":
    главная()
