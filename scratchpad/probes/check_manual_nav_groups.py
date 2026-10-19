#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка: разделы меню сворачиваются, есть раздел «Статьи».

Константин 19.10.2026, снимками меню базы знаний: «1. В Справке и руководстве
сделай как в базе знаний развернуть/свернуть и птички к разделам. 2. По Справке
все вместе сгруппируй. 3. Добавь новый раздел „Статьи“ — туда будем писать
статьи по разным фичам калькулятора пояснительные. 4. Сейчас напиши
пояснительную статью со скриншотами, как печатать документы».

Проба держит, через калькулятор (тест), на 390 и 1440:
  • в меню шесть разделов, у каждого заголовок-кнопка со стрелкой, не ниже
    34 px (на телефоне 44); главы — в разделах, «Прочего» нет;
  • нажатие на заголовок сворачивает раздел (главы не видны, стрелка
    повёрнута, aria-expanded=false) и разворачивает обратно;
  • «Свернуть» в строке «Главная» сворачивает все разделы и становится
    «Развернуть», повторное нажатие разворачивает все;
  • свёрнутое помнится при новом открытии справки;
  • глава, открытая из оглавления, раскрывает свой свёрнутый раздел;
  • оглавление на главной — те же шесть разделов;
  • статья «Как печатать документы»: шесть снимков загружаются, не шире
    своей половинной (×2) ширины и не шире колонки; у каждого подпись;
  • у каждой статьи под заголовком «Версия калькулятора X.Y.Z · обновлено
    ДД.ММ.ГГГГ», версия равна версии на значке калькулятора — с выпуском
    статью перечитывают и поднимают (Константин 19.10.2026: «к статье добавь
    версию и дату… Когда будут выходить апдейты, статью нужно будет
    обновлять»);

в бою (?contour=prod): раздела «Статьи» и статьи нет, разделов пять.

    python3 check_manual_nav_groups.py
"""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_manual_home as д
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
ЖДЁМ = ["Начало работы", "Расчёт", "Пресеты и клиент", "Документы", "Аккаунт и сервис", "Статьи"]


def плохо(т):
    НАХОДКИ.append(т)


МЕНЮ = """() => [...document.querySelectorAll('.sb-nav > .sb-group[data-grp]')].map(г => {
  const сп = document.getElementById('grp-' + г.getAttribute('data-grp')), р = г.getBoundingClientRect();
  return { имя: г.querySelector('span').textContent.trim(), выс: Math.round(р.height), стрелка: !!г.querySelector('.sb-group-chevron'),
    свёрнут: г.classList.contains('collapsed'), aria: г.getAttribute('aria-expanded'),
    видно: сп ? [...сп.querySelectorAll('.sb-a')].filter(а => а.getBoundingClientRect().height > 0 && сп.getBoundingClientRect().height > 2).length : 0,
    глав: сп ? сп.querySelectorAll('.sb-a').length : 0 }; })"""


def открыть(стр, ш):
    стр.evaluate("() => openManual()")
    к = д.кадр_справки(стр); стр.wait_for_timeout(1200)
    if ш <= 720:
        к.locator("body").evaluate("() => toggleMobMenu()"); стр.wait_for_timeout(400)
    return к


def прогон(бр, порт, ш):
    н = f"[{ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ош = []
    стр.on("pageerror", lambda e: ош.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=д.ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(д.ЗАГЛУШКА); стр.add_init_script(д.ЦЕНЫ)
    стр.add_init_script("window.__ТАБЛИЦЫ.app_docs = " + json.dumps(д.ряды(), ensure_ascii=False) + ";")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
    к = открыть(стр, ш)
    т = к.locator("body")
    т.evaluate("() => { try { localStorage.removeItem('manual_nav_collapsed'); } catch (e) {} }")
    м = т.evaluate("() => (" + МЕНЮ + ")()")
    if [г["имя"] for г in м] != ЖДЁМ:
        плохо(f"{н} разделы меню: {[г['имя'] for г in м]}")
    if not м:
        плохо(f"{н} в меню нет сворачиваемых разделов"); стр.close(); return
    мин = 44 if ш <= 720 else 34
    for г in м:
        if not г["стрелка"] or г["выс"] < мин - .5 or г["свёрнут"] or г["видно"] != г["глав"] or not г["глав"]:
            плохо(f"{н} раздел «{г['имя']}» в начале: {г}")
    if т.evaluate("() => [...document.querySelectorAll('.sb-group')].some(г => /Прочее/.test(г.textContent))"):
        плохо(f"{н} в меню остался раздел «Прочее»")
    стр.screenshot(path=str(СНИМКИ / f"manual-nav-{ш}.png"))
    # Один раздел.
    к.locator('.sb-group[data-grp="calc"]').click(); стр.wait_for_timeout(500)
    г = {x["имя"]: x for x in т.evaluate("() => (" + МЕНЮ + ")()")}["Расчёт"]
    if not г["свёрнут"] or г["видно"] or г["aria"] != "false":
        плохо(f"{н} нажатие на «Расчёт» не свернуло раздел: {г}")
    к.locator('.sb-group[data-grp="calc"]').click(); стр.wait_for_timeout(500)
    г = {x["имя"]: x for x in т.evaluate("() => (" + МЕНЮ + ")()")}["Расчёт"]
    if г["свёрнут"] or г["видно"] != г["глав"]:
        плохо(f"{н} повторное нажатие не развернуло «Расчёт»: {г}")
    # Все разом.
    к.locator("#sbToggle").click(); стр.wait_for_timeout(500)
    м = т.evaluate("() => (" + МЕНЮ + ")()")
    подпись = т.evaluate("() => document.getElementById('sbToggleLbl').textContent")
    if not all(x["свёрнут"] and not x["видно"] for x in м) or подпись != "Развернуть":
        плохо(f"{н} «Свернуть» не свернул все: {[(x['имя'], x['свёрнут'], x['видно']) for x in м]}, подпись «{подпись}»")
    if т.evaluate("() => document.querySelector('.ch.on').id") != "ch-home":
        плохо(f"{н} «Свернуть» в строке «Главная» увёл с главной")
    стр.screenshot(path=str(СНИМКИ / f"manual-nav-collapsed-{ш}.png"))
    # Помнится при новом открытии.
    стр.evaluate("async () => { closeManual(); await openManual(); }")
    к = д.кадр_справки(стр); стр.wait_for_timeout(1000); т = к.locator("body")
    м = т.evaluate("() => (" + МЕНЮ + ")()")
    if not all(x["свёрнут"] for x in м):
        плохо(f"{н} свёрнутые разделы не запомнились: {[(x['имя'], x['свёрнут']) for x in м]}")
    # Глава из оглавления раскрывает свой раздел.
    к.locator(".hm-ch[data-go='presets']").click(); стр.wait_for_timeout(600)
    г = {x["имя"]: x for x in т.evaluate("() => (" + МЕНЮ + ")()")}["Пресеты и клиент"]
    if г["свёрнут"]:
        плохо(f"{н} глава из оглавления не раскрыла свой раздел: {г}")
    т.evaluate("() => { go('home'); }"); стр.wait_for_timeout(300)
    if ш <= 720:
        т.evaluate("() => toggleMobMenu()"); стр.wait_for_timeout(300)
    # Открыт хоть один раздел — кнопка сворачивает все (как в базе знаний),
    # и только потом разворачивает.
    if т.evaluate("() => document.getElementById('sbToggleLbl').textContent") != "Свернуть":
        плохо(f"{н} при открытом разделе кнопка не «Свернуть»")
    к.locator("#sbToggle").click(); стр.wait_for_timeout(500)
    к.locator("#sbToggle").click(); стр.wait_for_timeout(500)
    м = т.evaluate("() => (" + МЕНЮ + ")()")
    if not all(not x["свёрнут"] for x in м) or т.evaluate("() => document.getElementById('sbToggleLbl').textContent") != "Свернуть":
        плохо(f"{н} «Развернуть» не развернул все: {[(x['имя'], x['свёрнут']) for x in м]}")
    # Оглавление.
    разделы = т.evaluate("() => [...document.querySelectorAll('#ch-home .hm-nm')].map(э => э.textContent.trim())")
    if разделы != ЖДЁМ:
        плохо(f"{н} оглавление на главной: {разделы}")
    # Статья.
    т.evaluate("() => go('art-print')"); стр.wait_for_timeout(1500)
    сн = т.evaluate("""() => { const к = document.querySelector('#ch-art-print'); if (!к) return null; const ш = к.getBoundingClientRect().width;
      return [...к.querySelectorAll('figure.art-shot')].map(ф => { const и = ф.querySelector('img'), р = и.getBoundingClientRect();
        return { src: и.getAttribute('src'), загр: и.complete && и.naturalWidth > 0, ш: Math.round(р.width), нат: и.naturalWidth, кол: Math.round(ш),
          подпись: !!(ф.querySelector('figcaption') || {}).textContent }; }); }""")
    if not сн or len(сн) != 6:
        плохо(f"{н} в статье не шесть снимков: {сн}")
    else:
        for с in сн:
            if not с["загр"] or not с["подпись"] or с["ш"] > с["нат"] / 2 + 1 or с["ш"] > с["кол"] + 1:
                плохо(f"{н} снимок статьи: {с}")
    # Выходные данные каждой статьи: версия калькулятора — та, что стоит на
    # значке (статья сверена с этим выпуском), дата правки — настоящая и не
    # из будущего; строка мельче текста статьи и стоит сразу под заголовком.
    версия = стр.evaluate("() => (document.getElementById('versionBadge').textContent.match(/\\d+\\.\\d+\\.\\d+/) || [''])[0]")
    for а in т.evaluate("""() => [...document.querySelectorAll('.ch[id^="ch-art-"]')].map(к => { const м = к.querySelector('h2 + p.art-meta, h2 + .art-bar > p.art-meta'),
        п = к.querySelector('p:not(.art-meta):not(.lead)');
      return { id: к.id, текст: м ? м.textContent.trim() : null,
        кегль: м ? parseFloat(getComputedStyle(м).fontSize) : 0, текстКегль: п ? parseFloat(getComputedStyle(п).fontSize) : 0 }; })"""):
        import datetime, re
        в = re.search(r"Версия калькулятора (\d+\.\d+\.\d+) · обновлено (\d\d)\.(\d\d)\.(\d{4})$", а["текст"] or "")
        if not в:
            плохо(f"{н} {а['id']}: нет строки «Версия калькулятора … · обновлено ДД.ММ.ГГГГ» под заголовком: {а['текст']!r}"); continue
        if в.group(1) != версия:
            плохо(f"{н} {а['id']}: статья сверена с {в.group(1)}, а калькулятор {версия} — перечитать статью и поднять версию")
        try:
            день = datetime.date(int(в.group(4)), int(в.group(3)), int(в.group(2)))
            if день > datetime.date.today():
                плохо(f"{н} {а['id']}: дата правки из будущего: {день}")
        except ValueError:
            плохо(f"{н} {а['id']}: дата правки не дата: {а['текст']!r}")
        if not а["кегль"] or а["кегль"] >= а["текстКегль"]:
            плохо(f"{н} {а['id']}: строка версии не мельче текста ({а['кегль']} против {а['текстКегль']})")
    # Содержание статьи: кнопка в строке версии, панель справа с разделами,
    # нажатие ведёт к разделу и отмечает его, Esc и уход в другую главу закрывают.
    к2 = к.locator("#ch-art-print .art-toc-btn")
    if not к2.count():
        плохо(f"{н} у статьи нет кнопки «Содержание»")
    else:
        кн = т.evaluate("""() => { const б = document.querySelector('#ch-art-print .art-toc-btn'), м = document.querySelector('#ch-art-print .art-meta');
          const р = б.getBoundingClientRect(), рм = м.getBoundingClientRect(), к = document.querySelector('#ch-art-print').getBoundingClientRect();
          return { выс: Math.round(р.height), зазор: Math.round(р.top >= рм.bottom - 1 ? 99 : р.left - рм.right), внутри: р.right <= к.right + 1 && р.left >= к.left - 1,
            ряд: б.parentElement.className }; }""")
        if кн["выс"] < 30 or кн["ряд"] != "art-bar" or not кн["внутри"] or кн["зазор"] < 8:
            плохо(f"{н} кнопка «Содержание»: {кн}")
        к2.click(); стр.wait_for_timeout(500)
        пан = т.evaluate("""() => { const п = document.getElementById('artToc'); if (!п) return null; const р = п.querySelector('.art-toc-panel').getBoundingClientRect();
          return { открыт: п.classList.contains('open'), пр: Math.round(р.right), лев: Math.round(р.left), шир: Math.round(р.width), W: innerWidth,
            пункты: [...п.querySelectorAll('.art-toc-a')].map(а => а.textContent.replace(/\\s+/g, '')),
            разделы: [...document.querySelectorAll('#ch-art-print .sec')].map(с => с.textContent.replace(/\\s+/g, '')),
            заголовок: (п.querySelector('.art-toc-h') || {}).textContent }; }""")
        if not пан or not пан["открыт"] or пан["шир"] < 200 or пан["пр"] > пан["W"] + 1 or пан["лев"] < 0:
            плохо(f"{н} панель содержания не открылась справа: {пан}")
        elif пан["пункты"] != пан["разделы"] or len(пан["пункты"]) < 5 or пан["заголовок"] != "Как печатать документы":
            плохо(f"{н} пункты содержания не совпали с разделами: {пан['пункты']} / {пан['разделы']} / {пан['заголовок']}")
        else:
            стр.screenshot(path=str(СНИМКИ / f"manual-art-toc-{ш}.png"))
            к.locator("#artToc .art-toc-a").nth(4).click(); стр.wait_for_timeout(1200)
            пос = т.evaluate("""() => { const с = document.querySelectorAll('#ch-art-print .sec')[4].getBoundingClientRect().top;
              const он = [...document.querySelectorAll('#artToc .art-toc-a')].findIndex(а => а.classList.contains('on'));
              return { верх: Math.round(с), он, открыт: document.getElementById('artToc').classList.contains('open') }; }""")
            if not (0 <= пос["верх"] <= 60) or (ш > 720 and пос["он"] != 4) or (ш <= 720) == пос["открыт"]:
                плохо(f"{н} пункт «5.» не привёл к разделу или не отмечен: {пос}")
            if ш > 720:
                стр.keyboard.press("Escape"); стр.wait_for_timeout(300)
                if т.evaluate("() => document.getElementById('artToc').classList.contains('open')"):
                    плохо(f"{н} Esc не закрыл содержание")
            т.evaluate("() => window.scrollTo(0, 0)"); стр.wait_for_timeout(300)
            к2.click(); стр.wait_for_timeout(400)
            т.evaluate("() => go('overview')"); стр.wait_for_timeout(300)
            if т.evaluate("() => document.getElementById('artToc').classList.contains('open')"):
                плохо(f"{н} содержание осталось открытым в другой главе")
            т.evaluate("() => go('art-print')"); стр.wait_for_timeout(500)
    стр.screenshot(path=str(СНИМКИ / f"manual-art-print-{ш}.png"))
    for о in [о for о in ош if not any(ш_ in о for ш_ in д.ШУМ)][:3]:
        плохо(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def в_бою(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    адрес = f"http://127.0.0.1:{порт}/__manual-probe.html?contour=prod"
    html = д.в_тоне(бр, порт, д.справка.достать("manual").replace("<html", '<html data-start="home"', 1))
    стр.route(адрес, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=html))
    стр.goto(адрес, wait_until="load"); стр.wait_for_timeout(600)
    р = стр.evaluate("""() => ({ разделы: [...document.querySelectorAll('.sb-nav > .sb-group')].map(г => г.textContent.trim()),
      статья: !!document.getElementById('ch-art-print') && !!document.querySelector('.sb-a[onclick="go(\\'art-print\\')"]'),
      оглавление: [...document.querySelectorAll('#ch-home .hm-nm')].map(э => э.textContent.trim()) })""")
    if р["разделы"] != ЖДЁМ[:5] or р["оглавление"] != ЖДЁМ[:5] or р["статья"]:
        плохо(f"[бой] разделы {р['разделы']}, оглавление {р['оглавление']}, статья в меню {р['статья']}")
    стр.close()


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = д.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=д.хром(), args=["--no-sandbox"])
            в_бою(бр, порт)
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: в меню справки шесть разделов со стрелками, каждый сворачивается, «Свернуть / Развернуть» — все разом, "
          "состояние помнится, глава раскрывает свой раздел; статья «Как печатать документы» — шесть снимков с подписями; "
          "в бою «Статей» нет; на 390 и 1440.")


if __name__ == "__main__":
    главная()
