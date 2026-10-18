#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чат пресета: просмотр снимков и PDF на странице и отправка файлов сразу.

Константин 17.10.2026, двумя снимками чата: «Фото и PDF открывай как превью
прямо на этой странице» и «Файлы сделай, чтобы отправлялись сразу и потом
после отправки шел вот тут маленький кружок загрузки».

Проба держит, на заглушке базы, с настоящим PDF (его собирает сам Chromium) и
pdf.js из папки pdfjs рядом:
  • нажатие на снимок открывает просмотр поверх страницы: имя, «1 из 3» (два
    снимка и PDF одного сообщения), снимок загружен и целиком в кадре,
    ссылка «Скачать» — с именем файла; мини-окно под просмотром не закрылось,
    страница под ним не прокручивается;
  • стрелки листают; PDF — листами pdf.js, на первом листе есть рисунок;
    Escape закрывает только просмотр, фокус возвращается к снимку;
  • нажатие на PDF в ленте открывает его сразу; прочий файл (docx) — по
    прежнему ссылкой на скачивание; нажатие по полю вокруг снимка закрывает;
  • отправка: сообщение с файлом в ленте сразу, поле пустое и свободное, на
    месте размера — кружок, строки «Ответить…» нет, в базе пока ничего;
    второе, отправленное следом, встаёт под ним и уходит в базу после него;
    когда файл лёг — кружок сменяется размером; снимок до загрузки виден
    сразу, кружок у него в углу;
  • вёрстка на 390 и 1440: кнопки просмотра не меньше 44 px, лист PDF не шире
    экрана, просмотр вбок не ходит, на телефоне стрелки не накрывают лист;
    лента с кружком — как в пробе чата.

    python3 check_chat_files.py
"""
import os, pathlib, sys, tempfile, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
PDFJS = ЗДЕСЬ / "pdfjs"
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []
PDF = pathlib.Path(tempfile.mkdtemp()) / "планировка.pdf"


def плохо(т):
    НАХОДКИ.append(т)


def отдать_pdfjs(r):
    путь = PDFJS / r.request.url.rsplit("/", 1)[-1]
    if путь.exists():
        r.fulfill(status=200, content_type="application/javascript", body=путь.read_bytes())
    else:
        r.abort()


def это_pdf(адрес):
    return "/assets/logo-bmsk-dark.png" in адрес and ".pdf" in urllib.parse.unquote(адрес)


ДАННЫЕ = """(код) => {
  const т = window.__ТАБЛИЦЫ, д = Date.now();
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  const п = (и, имя, тип, доп) => Object.assign({ path: код + '/u-коллега/c0000000-0000-4000-8000-000000000001/' + и, name: имя, size: 48213, type: тип }, доп || {});
  т.preset_messages = [{ id: 'c0000000-0000-4000-8000-000000000001', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина',
    body: 'Снимки участка и планировка.', reply_to: null, review_state: null, kind: 'msg', created_at: new Date(д - 600e3).toISOString(),
    attachments: [п('1.png', 'Участок.png', 'image/png', { w: 400, h: 300 }), п('2.png', 'Въезд.png', 'image/png', { w: 300, h: 400 }),
      п('3.pdf', 'Планировка.pdf', 'application/pdf'), п('4.docx', 'Смета.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')] },
    // Второе сообщение со снимком: просмотр листает вложения всего чата, а не
    // одного сообщения (Константин, 18.10.2026).
    { id: 'c0000000-0000-4000-8000-000000000002', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина',
      body: 'И фасад.', reply_to: null, review_state: null, kind: 'msg', created_at: new Date(д - 500e3).toISOString(),
      attachments: [{ path: код + '/u-коллега/c0000000-0000-4000-8000-000000000002/1.png', name: 'Фасад.png', size: 40211, type: 'image/png', w: 400, h: 300 }] }];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  // Загрузка в хранилище — с задержкой, которую задаёт проба.
  const из = _sb.storage.from.bind(_sb.storage);
  _sb.storage.from = к => { const о = из(к), груз = о.upload; о.upload = (...а) => new Promise(r => setTimeout(r, window.__ЖДАТЬ || 0)).then(() => груз(...а)); return о; };
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
}"""

ПРОСМОТР = """() => { const в = document.querySelector('.ch-view'); if (!в) return null;
  const тело = в.querySelector('.ch-view-body'), к = в.querySelector('.ch-view-img'), дл = в.querySelector('[data-v="dl"]');
  const кр = к && к.getBoundingClientRect();
  const кнопки = [...в.querySelectorAll('.ch-view-b, .ch-view-arr')].map(б => { const р = б.getBoundingClientRect(); return [Math.round(р.width), Math.round(р.height)]; });
  return { имя: в.querySelector('.ch-view-n').textContent, счёт: в.querySelector('.ch-view-c').textContent,
    снимок: к ? к.naturalWidth : 0, вКадре: !!(кр && кр.left >= -.5 && кр.top >= -.5 && кр.right <= innerWidth + .5 && кр.bottom <= innerHeight + .5),
    скачать: дл.getAttribute('href') || '', скачатьИмя: дл.getAttribute('download'), листов: в.querySelectorAll('.ch-view-page').length,
    листШире: [...в.querySelectorAll('.ch-view-page')].some(л => л.getBoundingClientRect().right > innerWidth + .5 || л.getBoundingClientRect().left < -.5),
    вбок: тело.scrollWidth > тело.clientWidth + 1, кнопки,
    // Стрелки поверх листа PDF закрывали бы его текст — на телефоне их место в строке.
    накрыли: [...в.querySelectorAll('.ch-view-arr')].some(а => { const р = а.getBoundingClientRect();
      return [...в.querySelectorAll('.ch-view-page')].some(л => { const q = л.getBoundingClientRect(); return р.left < q.right && р.right > q.left && р.top < q.bottom && р.bottom > q.top; }); }), мелкие: кнопки.filter(([ш, в_]) => ш < 43.5 || в_ < 43.5).length,
    окно: document.getElementById('presetChipCard').classList.contains('show'), прокрутка: getComputedStyle(document.documentElement).overflow,
    фокус: document.activeElement && (document.activeElement.getAttribute('data-v') || document.activeElement.tagName) }; }"""

РИСУНОК = """() => { const х = document.querySelector('.ch-view-page canvas'); if (!х || !х.width) return 0;
  const д = х.getContext('2d').getImageData(0, 0, х.width, х.height).data; let н = 0;
  for (let i = 0; i < д.length; i += 16) if (д[i] < 200 || д[i + 1] < 200 || д[i + 2] < 200) н++; return н; }"""

ЛЕНТА = """() => { const к = document.getElementById('presetChipCard'), все = [...к.querySelectorAll('.pc-chm')];
  return все.slice(-2).map(м_ => ({ текст: (м_.querySelector('.pc-chx') || {}).textContent || '', кружков: м_.querySelectorAll('.pc-spin').length,
    размер: [...м_.querySelectorAll('.pc-chfl-s')].map(с => с.textContent).join('|'), уголок: м_.querySelectorAll('.pc-chim-up').length,
    снимок: м_.querySelectorAll('.pc-chim img').length, ответить: !!м_.querySelector('[data-act="ch-reply"]') })); }"""


def собрать_pdf(бр):
    с = бр.new_page()
    с.set_content("<html><head><meta charset='utf-8'><style>@page{size:A4;margin:20mm}body{font-family:sans-serif}"
                  "h1{font-size:40px}.л{page-break-after:always;height:240mm;border:4px solid #123}</style></head><body>"
                  + "".join(f"<div class='л'><h1>Учебный лист {н}</h1><p>Планировка для пробы просмотра.</p></div>" for н in (1, 2, 3))
                  + "</body></html>")
    с.pdf(path=str(PDF), format="A4", print_background=True)
    с.close()


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    стр.route("**/cdnjs.cloudflare.com/ajax/libs/pdf.js/**", отдать_pdfjs)
    стр.route(это_pdf, lambda r: r.fulfill(status=200, content_type="application/pdf", body=PDF.read_bytes()))
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(800)
    мид = "c0000000-0000-4000-8000-000000000001"
    сс = стр.evaluate("""(мид) => { const м_ = document.querySelector('#presetChipCard .pc-chm[data-mid="' + мид + '"]');
      return [...м_.querySelectorAll('.pc-chim a, .pc-chfl')].map(а => ({ имя: а.title || (а.querySelector('.pc-chfl-n') || {}).textContent, просмотр: а.getAttribute('data-act') === 'ch-view', скачать: а.hasAttribute('download') })); }""", мид)
    ждали = [{"имя": "Участок.png", "просмотр": True, "скачать": False}, {"имя": "Въезд.png", "просмотр": True, "скачать": False},
             {"имя": "Планировка.pdf", "просмотр": True, "скачать": True}, {"имя": "Смета.docx", "просмотр": False, "скачать": True}]
    if сс != ждали:
        плохо(f"{н} вложения в ленте: {сс}")
    # ── снимок ──
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{мид}'] .pc-chim a").first.click(); стр.wait_for_timeout(700)
    п = стр.evaluate(ПРОСМОТР)
    if not п or п["имя"] != "Участок.png" or п["счёт"] != "1 из 4" or not п["снимок"] or not п["вКадре"] or "download=" not in п["скачать"] \
            or п["скачатьИмя"] != "Участок.png" or not п["окно"] or п["прокрутка"] != "hidden" or п["фокус"] != "x" or п["мелкие"]:
        плохо(f"{н} просмотр снимка: {п}")
    if п:
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"view-img-{ш}{'-n' if ночь else ''}.png"))
    стр.keyboard.press("ArrowRight"); стр.wait_for_timeout(500)
    п = стр.evaluate(ПРОСМОТР)
    if not п or п["имя"] != "Въезд.png" or п["счёт"] != "2 из 4" or not п["снимок"] or not п["вКадре"]:
        плохо(f"{н} стрелка вправо — второй снимок: {п}")
    стр.keyboard.press("ArrowRight")
    try:
        стр.wait_for_function("() => document.querySelectorAll('.ch-view-page canvas').length >= 1", timeout=20000)
    except Exception:
        pass
    стр.wait_for_timeout(600)
    п = стр.evaluate(ПРОСМОТР)
    рисунок = стр.evaluate(РИСУНОК)
    if not п or п["имя"] != "Планировка.pdf" or п["счёт"] != "3 из 4" or п["листов"] != 3 or рисунок < 50 or п["листШире"] or п["вбок"] or (ш < 700 and п["накрыли"]):
        плохо(f"{н} PDF в просмотре: {п}, точек рисунка {рисунок}")
    else:
        стр.screenshot(path=str(СНИМКИ / f"view-pdf-{ш}{'-n' if ночь else ''}.png"))
    # Дальше — снимок следующего сообщения, а смахивание пальцем влево и
    # вправо листает так же, как стрелки.
    стр.keyboard.press("ArrowRight"); стр.wait_for_timeout(600)
    п = стр.evaluate(ПРОСМОТР)
    if not п or п["имя"] != "Фасад.png" or п["счёт"] != "4 из 4" or not п["снимок"]:
        плохо(f"{н} стрелка вправо после последнего вложения сообщения — снимок следующего сообщения: {п}")
    СМАХНУТЬ = """(dx) => { const в = document.querySelector('.ch-view'); const т = (x) => new Touch({ identifier: 1, target: в, clientX: x, clientY: 300 });
      в.dispatchEvent(new TouchEvent('touchstart', { touches: [т(200)], changedTouches: [т(200)], bubbles: true }));
      в.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [т(200 + dx)], bubbles: true })); }"""
    стр.evaluate(СМАХНУТЬ, 150); стр.wait_for_timeout(400)
    п = стр.evaluate(ПРОСМОТР)
    if not п or п["имя"] != "Планировка.pdf":
        плохо(f"{н} смахнули вправо — ждали предыдущее, PDF: {п and п['имя']}")
    стр.evaluate(СМАХНУТЬ, -150); стр.wait_for_timeout(400)
    п = стр.evaluate(ПРОСМОТР)
    if not п or п["имя"] != "Фасад.png":
        плохо(f"{н} смахнули влево — ждали следующее, снимок фасада: {п and п['имя']}")
    if стр.evaluate("() => typeof sideNavOpen !== 'undefined' && sideNavOpen"):
        плохо(f"{н} смахивание в просмотре открыло боковую панель разделов под ним")
        стр.evaluate("() => closeSideNav()")
    if not стр.evaluate("() => document.getElementById('presetChipCard').classList.contains('show')"):
        плохо(f"{н} смахивание в просмотре закрыло мини-окно под ним"); стр.close(); return
    стр.evaluate(СМАХНУТЬ, 30); стр.wait_for_timeout(300)
    if (стр.evaluate(ПРОСМОТР) or {}).get("имя") != "Фасад.png":
        плохо(f"{н} короткое движение пальцем перелистнуло вложение")
    стр.keyboard.press("Escape"); стр.wait_for_timeout(300)
    з = стр.evaluate("""() => ({ просмотр: !!document.querySelector('.ch-view'), окно: document.getElementById('presetChipCard').classList.contains('show'),
      прокрутка: document.documentElement.style.overflow, фокус: document.activeElement && document.activeElement.closest('.pc-chim') ? 'снимок' : (document.activeElement || {}).tagName }) """)
    if з["просмотр"] or not з["окно"] or з["прокрутка"] or з["фокус"] != "снимок":
        плохо(f"{н} Escape: {з}")
    # PDF из ленты — сразу им; нажатие по полю вокруг снимка закрывает.
    try:
        стр.locator(f"#presetChipCard .pc-chm[data-mid='{мид}'] .pc-chfl[data-act='ch-view']").click(timeout=8000); стр.wait_for_timeout(500)
    except Exception:
        стр.screenshot(path=str(СНИМКИ / f"view-blocked-{ш}{'-n' if ночь else ''}.png"))
        плохо(f"{н} после просмотра PDF в ленте не нажимается — его что-то накрыло (снимок view-blocked)"); стр.close(); return
    п = стр.evaluate(ПРОСМОТР)
    if not п or п["имя"] != "Планировка.pdf" or п["счёт"] != "3 из 4":
        плохо(f"{н} нажатие на PDF в ленте: {п}")
    стр.locator(".ch-view [data-v='x']").click(); стр.wait_for_timeout(250)
    стр.locator(f"#presetChipCard .pc-chm[data-mid='{мид}'] .pc-chim a").first.click(); стр.wait_for_timeout(600)
    стр.mouse.click(8, в - 8); стр.wait_for_timeout(250)
    з = стр.evaluate("() => ({ просмотр: !!document.querySelector('.ch-view'), окно: document.getElementById('presetChipCard').classList.contains('show') })")
    if з["просмотр"] or not з["окно"]:
        плохо(f"{н} нажатие по полю вокруг снимка: {з}")
    # ── отправка сразу ──
    стр.evaluate("() => { window.__ЖДАТЬ = 1800; }")
    было = стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.length")
    стр.locator("#pcChatFile").set_input_files(files=[{"name": "Смета_v2.pdf", "mimeType": "application/pdf", "buffer": PDF.read_bytes()}])
    стр.locator("#pcChatText").fill("Смета во вложении")
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(250)
    л = (стр.evaluate(ЛЕНТА) or [{}])[-1]
    с = стр.evaluate("() => ({ поле: document.getElementById('pcChatText').value, выкл: document.getElementById('pcChatText').disabled, строк: window.__ТАБЛИЦЫ.preset_messages.length })")
    if л["текст"] != "Смета во вложении" or л["кружков"] != 1 or л["размер"] != "" or л["ответить"] or с["поле"] or с["выкл"] or с["строк"] != было:
        плохо(f"{н} сразу после «Отправить»: {л}, {с}")
    for т in стр.evaluate(ч.ВЁРСТКА):
        плохо(f"{н} лента с кружком: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"send-{ш}{'-n' if ночь else ''}.png"))
    стр.locator("#pcChatText").fill("Второе, следом"); стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(250)
    д = стр.evaluate(ЛЕНТА)
    if [х["текст"] for х in д] != ["Смета во вложении", "Второе, следом"] or стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.length") != было:
        плохо(f"{н} второе следом: лента {[х['текст'] for х in д]}, в базе {стр.evaluate('() => window.__ТАБЛИЦЫ.preset_messages.length') - было} новых")
    стр.wait_for_timeout(2600)
    д = стр.evaluate(ЛЕНТА)
    база = стр.evaluate("() => window.__ТАБЛИЦЫ.preset_messages.slice(-2).map(х => х.body)")
    if len(д) < 2 or база != ["Смета во вложении", "Второе, следом"] or д[0]["кружков"] or not д[0]["размер"].endswith("КБ") or not д[0]["ответить"] or not д[1]["ответить"]:
        плохо(f"{н} после загрузки: в базе {база}, лента {д}")
    # Снимок до загрузки виден сразу, кружок — в углу.
    стр.locator("#pcChatFile").set_input_files(files=[{"name": "фото.png", "mimeType": "image/png", "buffer": (ЗДЕСЬ.parent.parent / "assets" / "logo-bmsk-dark.png").read_bytes()}])
    стр.wait_for_timeout(300)
    стр.locator("#presetChipCard [data-act='ch-send']").click(); стр.wait_for_timeout(300)
    л = стр.evaluate(ЛЕНТА)[-1]
    if л["снимок"] != 1 or л["уголок"] != 1:
        плохо(f"{н} снимок сразу после «Отправить»: {л}")
    стр.wait_for_timeout(2300)
    л = стр.evaluate(ЛЕНТА)[-1]
    if л["уголок"] or not л["ответить"]:
        плохо(f"{н} снимок после загрузки: {л}")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                собрать_pdf(бр)
                прогон(бр, порт, 1440, 900, False)
                прогон(бр, порт, 390, 844, True)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: снимок и PDF — просмотром на странице, стрелки, Escape, поле вокруг снимка, docx скачивается; "
          "отправка сразу с кружком на месте размера, очередь в порядке нажатия, снимок с кружком в углу; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
