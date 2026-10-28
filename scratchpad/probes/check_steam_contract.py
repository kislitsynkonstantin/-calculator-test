#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Договор подряда парной (-ПАР) и правила эксплуатации парного отделения.

Константин 28.10.2026: «Сделай договор на парную. Возьми за основу договор на
отделку. Кучу вопросов не задавай, сам решим. Срок гарантии и тд. Также добавь
правила эксплуатации отдельные на парную… Сделай привязку к опциям. Заложи в
правила требования ключевые по печам, базовые»; «В парных подпиши „Договор
подряда“, так как там один всего договор»; снимком окна данных договора:
«Когда парная, тут подставляй шифр парной. Пусть будет -ПАР».

Проба держит:
  • номер договора парной — с кодом -ПАР, и в данных договора, и в окне
    «Данные для договора» (поле одно, отделки нет); у каркаса — снова -КАР;
  • в меню документа и в «Печатать всё» первый договор парной — «Договор
    подряда»; у каркаса — «Основной договор»;
  • договор: предмет — устройство парного отделения в доме Заказчика, объект —
    помещение с размерами и объёмом, пункты о месте печи и проходе дымохода,
    этапы парной, гарантия 24 / 12 / 12 месяцев, без фундамента, участка и
    строительной площадки; версия 1.0;
  • правила: «парного отделения», свой раздел «Эксплуатация парной» и «Печь и
    дымоход»; пункты опций есть ровно тогда, когда опция в расчёте (подсветка,
    окно, масло, бак, Ферингер, каменный портал); печь по объёму — с моделью и
    её диапазоном; ни строения, ни кровли, ни костров;
  • окно печати: договор и правила парной — не заглушка, кнопка печати
    доступна, на 390 и 1440 px лист не шире экрана.

    python3 check_steam_contract.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_steam_tab as п
from playwright.sync_api import sync_playwright

НАХОДКИ = []
def плохо(т): НАХОДКИ.append(т)

ТЕКСТ = """(html) => { const д = new DOMParser().parseFromString(html, 'text/html'); return д.body.innerText.replace(/\\s+/g, ' '); }"""


def тексты(стр):
    return стр.evaluate(f"""() => {{ const т = {ТЕКСТ};
      const v = getContractVarsKar(1);
      return {{ вид: v.kind, тех: v.tech, номер: v.contractNumKar, объект: v.projectName, размер: v.projectSize,
        договор: т(buildContractHtmlKar(v)), правила: т(buildRulesHtml(v)) }}; }}""")


def main():
    с, порт = п.м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=п.м.хром())
            стр, ош = п.открыть(бр, порт, 1440)
            п.в_парную(стр)
            стр.evaluate("""() => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'admin' });
              const н = document.getElementById('contractNumber'); н.value = '45678934'; н.dispatchEvent(new Event('input'));
              ['cdContractNumKar', 'cdContractNumO'].forEach(и => { const э = document.getElementById(и); if (э) э.value = ''; });
              парнаяПечь('grom-40-p2-pech-komplekt'); calc(); }""")
            т = тексты(стр)
            if т["вид"] != "par" or т["тех"] != "steam" or т["номер"] != "45678934-ПАР":
                плохо(f"данные договора парной: вид {т['вид']}, расчёт {т['тех']}, номер {т['номер']} — ждали par / steam / 45678934-ПАР")
            if т["объект"] != "Парное отделение в каменном доме" or "3 × 4 × 2,3 м" not in т["размер"] or "м³" not in т["размер"]:
                плохо(f"объект договора парной: «{т['объект']}», «{т['размер']}»")
            д = т["договор"]
            for нужно in ["Версия 1.0", "устройству парного отделения", "в доме Заказчика", "Адрес объекта", "Размер помещения",
                          "передача помещения для монтажа парного отделения", "работы по отделке парного отделения",
                          "работы по установке печи и дымохода", "4.8.", "проход дымохода", "4.9.", "Монтаж печи и дымохода",
                          "Отделка парного отделения", "Освещение и вентиляция", "гарантия производителя",
                          "от перегрева печи и нарушения Правил эксплуатации", "оплата после уведомления о готовности начать монтаж парного отделения"]:
                if нужно not in д:
                    плохо(f"в договоре парной нет «{нужно}»")
            for нельзя in ["фундамент", "Строительную площадку (земельный участок), а также", "строительству", "Приложение № 5",
                           "Конструктив", "Кровля", "Адрес участка", "Размер строения"]:
                if нельзя in д:
                    плохо(f"в договоре парной лишнее: «{нельзя}»")
            if "24 мес." not in д.replace("24мес.", "24 мес."):
                гар = стр.evaluate("() => { const v = getContractVarsKar(1); return v.гарантия; }")
                плохо(f"гарантия монтажа печи не 24 месяца: {гар}")

            # Правила без опций — пунктов опций нет.
            р = т["правила"]
            for нужно in ["Правила эксплуатации парного отделения", "Парное отделение (далее — парная) — помещение в доме Заказчика",
                          "Эксплуатация парной", "Печь и дымоход", "ГРОМ 40", "рассчитана на 25–40 м³", "портал из минерита",
                          "притопочный лист", "пусконаладки", "Плафоны парной", "Стеклянная дверь парной", "Версия 1.0"]:
                if нужно not in р:
                    плохо(f"в правилах парной нет «{нужно}»")
            for нельзя in ["Подсветка полков", "Панорамное окно", "маслом для саун", "бака", "Пароиспаритель", "Каменный портал",
                           "Костры", "Снег с кровли", "Строение", "каркасн", "Нижняя обвязка", "В срубе"]:
                if нельзя in р:
                    плохо(f"в правилах парной без опций лишнее: «{нельзя}»")
            # Опции в расчёте — их пункты в правилах.
            # Принадлежности Ферингера живут только при печи Ферингер (автоматика 28.10.2026).
            стр.evaluate("""() => { парнаяПечь('feringer-optima'); ['podsv', 'okno', 'maslo', 'bak', 'talk', 'st31', 'st30'].forEach(к => ПАР.вкл.add(к));
              ПАР.комн = 'log'; calc(); }""")
            р = тексты(стр)["правила"]
            for нужно in ["Подсветка полков", "Панорамное окно", "маслом для саун", "бака", "Пароиспаритель Ферингера",
                          "ассеты Ферингер", "Каменный портал", "портал из талькохлорита", "В срубе", "печи нужно"]:
                if нужно not in р:
                    плохо(f"в правилах парной с опциями нет «{нужно}»")
            стр.evaluate("() => { ['podsv', 'okno', 'maslo', 'bak', 'talk', 'st31', 'st30'].forEach(к => ПАР.вкл.delete(к)); ПАР.комн = 'stone'; парнаяПечь('grom-40-p2-pech-komplekt'); }")

            # Окно «Данные для договора»: одно поле с -ПАР.
            стр.evaluate("() => openContractDataModal()")
            ок = стр.evaluate("""() => { const к = document.getElementById('cdContractNumKar'), о = document.getElementById('cdContractNumO');
              return { подпись: к.previousElementSibling.textContent, значение: к.value, отделка: getComputedStyle(о.parentElement).display,
                       шапка: к.closest('.field').parentElement.parentElement.firstElementChild.textContent }; }""")
            if ок != {"подпись": "№ Договора подряда (ПАР)", "значение": "45678934-ПАР", "отделка": "none", "шапка": "Номер договора"}:
                плохо(f"окно данных договора в парной: {ок}")
            стр.evaluate("() => closeContractDataModal()")

            # Окно печати: договор и правила — не заглушка; меню — «Договор подряда».
            стр.evaluate("() => { openPrintPreview(); }"); стр.wait_for_timeout(900)
            for сущ in ("contract", "rules"):
                стр.evaluate("e => setPreviewEntity(e)", сущ); стр.wait_for_timeout(900)
                о = стр.evaluate("""() => ({ заглушка: document.getElementById('printOverlay').classList.contains('preview-mode-stub'),
                  печать: document.getElementById('printDocBtn').disabled, метка: document.getElementById('previewEntityLabel').textContent,
                  пункт: document.querySelector('#previewEntityMenu [data-contract="1"] .ent-name > span').textContent,
                  шире: document.documentElement.scrollWidth > innerWidth + 1 })""")
                if о["заглушка"] or о["печать"] or о["пункт"] != "Договор подряда" or о["шире"] or (сущ == "contract" and о["метка"] != "Договор подряда"):
                    плохо(f"окно печати парной, «{сущ}»: {о}")
                стр.screenshot(path=f"/tmp/steam-{сущ}-1440.png")
            комплект = стр.evaluate("() => документыКомплекта().map(д => д.имя)")
            if "Договор подряда" not in комплект or "Основной договор" in комплект:
                плохо(f"«Печатать всё» в парной: {комплект}")
            стр.evaluate("() => closePrintPreview()")

            # Каркас: снова «Основной договор» и -КАР.
            стр.evaluate("async () => { selectTech('Каркас'); await new Promise(r => setTimeout(r, 900)); selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }")
            к = стр.evaluate("""() => { обновитьМенюДокумента(); openContractDataModal();
              const р = { номер: getContractVarsKar(1).contractNumKar, вид: getContractVarsKar(1).kind,
                пункт: document.querySelector('#previewEntityMenu [data-contract="1"] .ent-name > span').textContent,
                подпись: document.getElementById('cdContractNumKar').previousElementSibling.textContent,
                отделка: getComputedStyle(document.getElementById('cdContractNumO').parentElement).display };
              closeContractDataModal(); return р; }""")
            if к != {"номер": "45678934-КАР", "вид": "kar", "пункт": "Основной договор", "подпись": "№ Основного договора (КАР)", "отделка": "flex"}:
                плохо(f"каркас после парной: {к}")
            for е in [е for е in ош if "supabase" not in е.lower()][:3]:
                плохо(f"ошибка страницы: {е[:160]}")
            стр.close()

            # Телефон: договор парной в окне печати не шире экрана.
            стр, ош = п.открыть(бр, порт, 390)
            п.в_парную(стр)
            стр.evaluate("() => { window._sbProfile = Object.assign({}, window._sbProfile, { role: 'admin' }); openPrintPreview(); }")
            стр.wait_for_timeout(900)
            стр.evaluate("() => setPreviewEntity('contract')"); стр.wait_for_timeout(1200)
            if стр.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"):
                плохо("390 px: окно печати с договором парной шире экрана")
            стр.screenshot(path="/tmp/steam-contract-390.png")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: у парной свой договор подряда -ПАР (предмет, объект, место печи и проход дымохода, этапы, гарантия 24/12/12) и "
          "правила парного отделения с пунктами по опциям и печи по объёму; в меню и комплекте — «Договор подряда», в окне данных "
          "— одно поле с -ПАР; каркас после парной — снова «Основной договор» и -КАР.")


if __name__ == "__main__":
    main()
