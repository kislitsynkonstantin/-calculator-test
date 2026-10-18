#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Паспорт заказчика в «Данных для договора», снимки — копией в чат, журнал состава договоров.

Константин 18.10.2026, снимком окна «Данные для договора»: «Добавь ещё
куда-нибудь сюда кнопку загрузить паспорт заказчика (чтобы автоматически
распознать и заполнить разделы тут). Паспорт когда загружаем тут, дублируй
его в чат пресета. И также визуализации когда загружаем, дублируй их в чат
пресета. Также проверь, изменения платежного плана пишутся ли в журнал
событий».

Проба держит, на заглушке базы и с tesseract.js из пакетов npm вместо
jsDelivr, на учебном паспорте (данные выдуманы, страница нарисована
пробой — с настоящей машиночитаемой зоной и контрольными цифрами):
  • разбор машиночитаемой зоны: ФИО кириллицей, серия и номер, даты
    рождения и выдачи, код подразделения, контрольные цифры сходятся;
  • в окне — кнопка «Загрузить паспорт»; снимок заполняет ФИО в реквизитах,
    дату рождения, серию и номер, дату выдачи, код подразделения;
  • снимок паспорта уходит в чат пресета сообщением «Паспорт заказчика…»;
  • снимки, добавленные в «Визуализацию и планировку», — сообщением в чат;
  • перенос раздела в другой договор, снятие раздела, новый и удалённый
    договор и стандартный состав в окне платёжного плана пишутся в журнал.

    python3 check_passport_upload.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_approval_report as з
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
ЛИБЫ = pathlib.Path(os.environ.get("BM_LIBS") or "/tmp/claude-0/-home-user-vscode-workspace/0db66daf-36ea-5fb3-b079-395424f89a35/scratchpad/либы") / "ocr"
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def контроль(т):
    в = [7, 3, 1]; с = 0
    for i, ч in enumerate(т):
        з_ = int(ч) if ч.isdigit() else (ord(ч) - 55 if ч.isalpha() else 0)
        с += з_ * в[i % 3]
    return str(с % 10)


# Учебный заказчик — данные выдуманы.
ЧЕЛОВЕК = {"фио": "Заказчиков Иван Иванович", "рождение": "1989-10-01", "серия": "4510", "номер": "123456", "выдан": "2008-10-03", "код": "770-001"}
СТРОКА1 = ("PNRUS" + "ZAKAZ3IKOV<<IVAN<IVANOVI3").ljust(44, "<")
_н9 = "451" + "123456"
_с2 = _н9 + контроль(_н9) + "RUS" + "891001" + контроль("891001") + "M" + "<" * 7 + "0" + "081003" + "770001" + "<<"
СТРОКА2 = _с2 + контроль(_с2)
assert len(СТРОКА1) == 44 and len(СТРОКА2) == 44, (len(СТРОКА1), len(СТРОКА2))

ПАСПОРТ_HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#e9e3d6}} #p{{width:1000px;height:1400px;background:#f4ead8;font-family:'DejaVu Serif',serif;color:#2b2b2b;position:relative}}
.top{{position:absolute;left:60px;top:70px;right:60px;font-size:26px;line-height:1.35}}
.top b{{font-family:'DejaVu Sans',sans-serif}} .bot{{position:absolute;left:60px;top:740px;right:60px;font-size:28px;line-height:1.5}}
.ph{{position:absolute;left:60px;top:760px;width:250px;height:320px;background:#cfc6b5}} .f{{margin-left:300px}}
.mrz{{position:absolute;left:40px;right:40px;bottom:60px;font-family:'DejaVu Sans Mono',monospace;font-size:35px;letter-spacing:2.2px;line-height:1.6}}
.fold{{position:absolute;left:0;right:0;top:700px;border-top:2px dashed #b9ad97}}
</style></head><body><div id="p">
<div class="top">Паспорт выдан<br><b>ОТДЕЛОМ УФМС РОССИИ ПО ГОРОДУ ПРОБНОМУ<br>В УЧЕБНОМ РАЙОНЕ</b><br>Дата выдачи 03.10.2008 &nbsp;&nbsp; Код подразделения 770-001</div>
<div class="fold"></div><div class="ph"></div>
<div class="bot"><div class="f">Фамилия <b>ЗАКАЗЧИКОВ</b><br>Имя <b>ИВАН</b><br>Отчество <b>ИВАНОВИЧ</b><br>Пол <b>МУЖ.</b> Дата рождения <b>01.10.1989</b></div></div>
<div class="mrz">{СТРОКА1.replace('<', '&lt;')}<br>{СТРОКА2.replace('<', '&lt;')}</div>
</div></body></html>"""


def маршруты_ocr(контекст):
    def отдать(путь, тип):
        return lambda r: r.fulfill(status=200, content_type=тип, body=путь.read_bytes()) if путь.exists() else r.fulfill(status=404, body=b"")
    контекст.route("**/npm/tesseract.js@5.1.1/dist/tesseract.min.js", отдать(ЛИБЫ / "tesseract.js-5.1.1/package/dist/tesseract.min.js", "text/javascript"))
    контекст.route("**/npm/tesseract.js@5.1.1/dist/worker.min.js", отдать(ЛИБЫ / "tesseract.js-5.1.1/package/dist/worker.min.js", "text/javascript"))
    def ядро(r):
        имя = r.request.url.rsplit("/", 1)[-1]
        п = ЛИБЫ / "tesseract.js-core-5.1.1/package" / имя
        r.fulfill(status=200 if п.exists() else 404, content_type="application/wasm" if имя.endswith(".wasm") else "text/javascript", body=п.read_bytes() if п.exists() else b"")
    контекст.route("**/npm/tesseract.js-core@5.1.1/**", ядро)
    for яз in ("eng", "rus"):
        контекст.route(f"**/npm/@tesseract.js-data/{яз}@1.0.0/4.0.0_best_int/**",
                       отдать(ЛИБЫ / f"tesseract.js-data-{яз}-1.0.0/package/4.0.0_best_int/{яз}.traineddata.gz", "application/gzip"))


def прогон(бр, порт):
    н = "[1440]"
    # Учебный паспорт — картинкой.
    рис = бр.new_page(viewport={"width": 1000, "height": 1400})
    рис.set_content(ПАСПОРТ_HTML); рис.wait_for_timeout(300)
    файл = СНИМКИ / "passport-sample.png"
    рис.locator("#p").screenshot(path=str(файл))
    рис.close()

    стр, ошибки = з.начать(бр, порт, 1440, 900)
    маршруты_ocr(стр.context)
    стр.on("console", lambda с: ошибки.append(с.text) if "[паспорт]" in с.text else None)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(з.ХРАНИЛИЩЕ)
    if not стр.evaluate("() => typeof разобратьМЧЗ === 'function'"):
        плохо(f"{н} в калькуляторе нет распознавания паспорта"); стр.close(); return

    # ── разбор зоны ──
    р = стр.evaluate("(т) => разобратьМЧЗ(т)", СТРОКА1 + "\n" + СТРОКА2)
    ждём = {"фио": ЧЕЛОВЕК["фио"], "рождение": ЧЕЛОВЕК["рождение"], "серия": ЧЕЛОВЕК["серия"], "номер": ЧЕЛОВЕК["номер"],
            "выдан": ЧЕЛОВЕК["выдан"], "код": ЧЕЛОВЕК["код"], "надёжно": True}
    if not р or any(р.get(к) != в for к, в in ждём.items()):
        плохо(f"{н} разбор машиночитаемой зоны: {р}")
    # Распознавание путает 0 и O в цифровых местах — разбор это прощает.
    р2 = стр.evaluate("(т) => разобратьМЧЗ(т)", СТРОКА1 + "\n" + СТРОКА2.replace("0", "O", 3))
    if not р2 or р2.get("номер") != ЧЕЛОВЕК["номер"] or р2.get("серия") != ЧЕЛОВЕК["серия"]:
        плохо(f"{н} разбор не прощает O вместо 0: {р2}")
    # Распознавание теряет и добавляет знаки в хвосте строки: лишний заполнитель,
    # лишняя буква перед датой выдачи, срезанные «<<» с контрольной цифрой.
    for имя_, с2 in (("лишний «<»", СТРОКА2.replace("<" * 7, "<" * 8)),
                     ("лишняя буква и срезанный конец", СТРОКА2.replace("<" * 7 + "0", "<" * 7 + "0Q")[:-3]),
                     ("потерянный «<»", СТРОКА2.replace("<" * 7, "<" * 5))):
        р3 = стр.evaluate("(т) => разобратьМЧЗ(т)", СТРОКА1 + "\n" + с2)
        if not р3 or (р3.get("выдан"), р3.get("код"), р3.get("серия")) != (ЧЕЛОВЕК["выдан"], ЧЕЛОВЕК["код"], ЧЕЛОВЕК["серия"]):
            плохо(f"{н} разбор хвоста зоны ({имя_}): {р3}")

    # ── кнопка и распознавание ──
    стр.evaluate("() => openContractDataModal()"); стр.wait_for_timeout(500)
    кн = стр.locator("#cdPassportBtn")
    if not кн.count() or not кн.is_visible():
        плохо(f"{н} в «Данных для договора» нет кнопки «Загрузить паспорт»")
    else:
        стр.screenshot(path=str(СНИМКИ / "passport-btn-1440.png"))
    стр.set_input_files("#cdPassportFile", str(файл))
    for _ in range(120):
        стр.wait_for_timeout(1000)
        if стр.evaluate("() => !document.getElementById('cdPassportBtn').disabled && !!document.getElementById('cdPassport').value"):
            break
    поля = стр.evaluate("""() => ({ фио: document.getElementById('clientName').value, рождение: document.getElementById('cdBirthDate').value,
      паспорт: document.getElementById('cdPassport').value, выдан: document.getElementById('cdPassportDate').value,
      код: document.getElementById('cdPassportCode').value, кем: document.getElementById('cdPassportIssuer').value, тосты: (window.__тосты || []).slice(-3) })""")
    ждём_поля = {"фио": ЧЕЛОВЕК["фио"], "рождение": ЧЕЛОВЕК["рождение"], "паспорт": ЧЕЛОВЕК["серия"] + " " + ЧЕЛОВЕК["номер"], "выдан": ЧЕЛОВЕК["выдан"], "код": ЧЕЛОВЕК["код"]}
    for к, в in ждём_поля.items():
        if поля[к] != в:
            плохо(f"{н} после распознавания поле «{к}»: {поля[к]!r}, ждали {в!r}; {ошибки[:2]}")
    if "ПРОБНОМУ" not in поля["кем"].upper():
        # «Кем выдан» читается русским распознаванием — не всегда; пустое поле
        # законно, но подсказка тогда обязана попросить вписать.
        if not any("Кем выдан" in т for т in поля["тосты"]):
            плохо(f"{н} «Кем выдан» не прочитан, и подсказка об этом молчит: {поля}")
    стр.screenshot(path=str(СНИМКИ / "passport-filled-1440.png"))

    # ── копия в чат ──
    стр.wait_for_timeout(1500)
    чат = стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.filter(с => (с.attachments || []).length).map(с => ({ т: с.body, в: с.attachments.map(в => в.name) }))")
    if not any("Паспорт заказчика" in с["т"] and any("passport" in в for в in с["в"]) for с in чат):
        плохо(f"{н} снимок паспорта не ушёл в чат пресета: {чат}")
    стр.evaluate("() => closeContractDataModal()")
    стр.set_input_files("#canvasFileInput", str(pathlib.Path(__file__).parent / "образцы_приложения2" / "визуализация.jpg"))
    стр.wait_for_timeout(2500)
    чат = стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.filter(с => (с.attachments || []).length).map(с => ({ т: с.body, в: с.attachments.map(в => в.name) }))")
    if not any("Визуализации" in с["т"] and any("визуализация" in в for в in с["в"]) for с in чат):
        плохо(f"{н} снимок визуализации не ушёл в чат пресета: {чат}")

    # ── журнал состава договоров ──
    стр.evaluate("() => { window.__ТАБЛИЦЫ.events = (window.__ТАБЛИЦЫ.events || []).filter(е => !/section_moved|payment_plan_changed/.test(е.event_type)); }")
    стр.evaluate("""() => { ppCmDidDrag = false; ppCmTapUnassign('roof'); ppCmAdd(); ppCmDelete(contractsConfig[contractsConfig.length - 1].id); ppCmResetToDefaults(); }""")
    стр.wait_for_timeout(800)
    ж = стр.evaluate("() => (window.__ТАБЛИЦЫ.events || []).filter(е => /section_moved|payment_plan_changed/.test(е.event_type)).map(е => [е.event_type, (е.details || {}).obj, ((е.details || {}).rows || []).map(р => р.k + ': ' + р.a + ' → ' + р.b).join('; ')])")
    текст = " | ".join(" ".join(map(str, е)) for е in ж)
    for что in ["section_moved", "Кровля", "добавлен", "удалён", "стандартный"]:
        if что not in текст:
            плохо(f"{н} журнал состава договоров: нет «{что}» — {ж}")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def узкий(бр, порт):
    # Кнопка стоит в строке заголовка «Заказчик»: на телефоне она не должна
    # вылезать за окно, липнуть к заголовку или к черте под ним.
    for ш in (390, 768):
        н = f"[{ш}]"
        стр, ошибки = з.начать(бр, порт, ш, 844)
        стр.evaluate("() => openContractDataModal()"); стр.wait_for_timeout(500)
        м_ = стр.evaluate("""() => { const к = document.getElementById('cdPassportBtn'); if (!к) return null;
          const р = к.closest('.cd-grp-h'), з_ = р && р.firstElementChild !== к ? р.firstElementChild : null;
          const rк = к.getBoundingClientRect(), rр = р.getBoundingClientRect(), rз = з_ ? з_.getBoundingClientRect() : null;
          const окно = к.closest('div[style*="overflow-y:auto"]') || document.body, rо = окно.getBoundingClientRect();
          return { выс: rк.height, вправо: rо.right - rк.right, влево: rк.left - rо.left, отЗаг: rз ? rк.left - rз.right : 99,
                   отЧерты: rр.bottom - rк.bottom, перенос: rз ? rз.top >= rк.bottom - 2 : false }; }""")
        if not м_:
            плохо(f"{н} нет кнопки «Загрузить паспорт»"); стр.close(); continue
        if м_["вправо"] < 0 or м_["влево"] < 0:
            плохо(f"{н} кнопка паспорта выходит за окно: {м_}")
        if м_["отЗаг"] < 8 and not м_["перенос"]:
            плохо(f"{н} кнопка паспорта прилипла к заголовку: {м_}")
        if м_["отЧерты"] < 4:
            плохо(f"{н} кнопка паспорта касается черты под заголовком: {м_}")
        стр.locator("#cdPassportBtn").scroll_into_view_if_needed()
        стр.screenshot(path=str(СНИМКИ / f"passport-btn-{ш}.png"))
        стр.close()


def главная():
    if not (ЛИБЫ / "tesseract.js-5.1.1").exists():
        print(f"нет tesseract.js в {ЛИБЫ}: распакуйте пакеты npm"); sys.exit(2)
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт)
                узкий(бр, порт)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: машиночитаемая зона паспорта разбирается с контрольными цифрами, кнопка «Загрузить паспорт» заполняет ФИО, даты, "
          "серию и номер, код подразделения; паспорт и снимки визуализации уходят в чат пресета; состав договоров пишется в журнал.")


if __name__ == "__main__":
    главная()
