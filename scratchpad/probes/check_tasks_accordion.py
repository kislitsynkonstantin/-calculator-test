#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Лог развития: задачи сворачиваются, как выпуски журнала обновлений.

Константин 14.10.2026: «В логе развития сделай опцию сворачивания содержания
задач, чтобы можно было пройтись по разделам. Как в Журнале обновлений
версии».

Глава видна только администратору — проба входит им. Держит, через
калькулятор на 1440 и 390 px, днём и ночью:
  • при открытии главы развёрнута первая задача, остальные — одной строкой
    (номер, название, метка, стрелка), их содержимого не видно;
  • нажатие по строке раскрывает задачу и сворачивает обратно; Enter — так же;
    признак aria-expanded идёт следом;
  • «Свернуть все» сворачивает все задачи и становится «Развернуть все»;
    второе нажатие разворачивает все;
  • поле нажатия свёрнутой строки — от 44 px в высоту;
  • названия задач с однозначными номерами начинаются в одну линию: «1» в
    Unbounded уже «2» на три с половиной пикселя, и без моноширинных цифр
    первое название выступало из столбца;
  • стрелка стоит рядом с меткой состояния, а не висит посреди строки
    (до ближайшего соседа не больше 26 px), и не выходит за колонку;
  • переход из поиска к тексту свёрнутой задачи раскрывает её;
  • в печати все задачи развёрнуты, стрелок и кнопки нет.

    python3 check_tasks_accordion.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ЦЕНЫ = (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8")
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


РЯДЫ = [{"doc": ч["doc"], "part": ч["part"], "ord": ч["ord"], "staff_only": ч["staff_only"], "html": ч["html"]}
        for ч in справка.части("manual")]

СОСТ = """() => {
  const все = [...document.querySelectorAll('#ch-tasks .tsk')];
  const вид = э => !!э && getComputedStyle(э).display !== 'none' && э.getClientRects().length > 0;
  const w = innerWidth;
  return {
    задач: все.length,
    открыты: все.map(т => т.classList.contains('open')),
    содержимое: все.map(т => [...т.children].filter(э => !э.classList.contains('tsk-head')).some(вид)),
    aria: все.map(т => (т.querySelector('.tsk-head') || {}).getAttribute ? т.querySelector('.tsk-head').getAttribute('aria-expanded') : null),
    кнопка: ((document.getElementById('tskCtl') || {}).textContent || '').trim(),
    названия: все.filter(т => ((т.querySelector('.tsk-num') || {}).textContent || '').trim().length === 1 && т.querySelector('.tsk-name')).map(т => т.querySelector('.tsk-name').getBoundingClientRect().left),
    вширь: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    стрелки: все.map(т => { const с = т.querySelector('.tsk-chev'), м = т.querySelector('.tsk-st'), ш = т.querySelector('.tsk-head');
      if (!с || !м) return null; const а = с.getBoundingClientRect(), б = м.getBoundingClientRect(), к = ш.getBoundingClientRect();
      const рядом = Math.abs((а.top + а.bottom) / 2 - (б.top + б.bottom) / 2) < 12;
      return { зазор: рядом ? Math.round(а.left - б.right) : Math.round(Math.min(а.left - к.left, к.right - а.right)), вКолонке: а.right <= к.right + .5 && а.right <= w }; }),
  };
}"""

ПОЛЕ = """(_, i) => { const т = document.querySelectorAll('#ch-tasks .tsk')[i], ш = т.querySelector('.tsk-head');
  т.scrollIntoView({ block: 'center' });
  const r = т.getBoundingClientRect(), x = r.left + 30; let верх = null, низ = null;
  for (let y = Math.floor(r.top); y <= Math.ceil(r.bottom); y++) { const э = document.elementFromPoint(x, y);
    if (э && (э === ш || ш.contains(э))) { if (верх === null) верх = y; низ = y; } }
  return верх === null ? 0 : низ - верх + 1; }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш in (1440, 390):
        for ночь in (False, True):
            н = f"[{ш} {'ночь' if ночь else 'день'}]"
            стр = бр.new_page(viewport={"width": ш, "height": 900}, device_scale_factor=2 if ш == 1440 else 1)
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
            стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + ЦЕНЫ + ");\n"
                                "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(РЯДЫ, ensure_ascii=False) + ";\n"
                                "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'admin' }); });")
            стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("(ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';"
                         " window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'admin' }); document.body.classList.toggle('dark', ночь); }", ночь)
            стр.evaluate("() => openManual('tasks')")
            кадр = None
            for _ in range(50):
                стр.wait_for_timeout(200)
                if стр.frame_locator("#manualFrame").locator("#ch-tasks.on").count():
                    кадр = стр.frame_locator("#manualFrame"); break
            if not кадр:
                факт(False, f"{н} глава «Лог развития» не открылась"); стр.close(); continue
            стр.wait_for_timeout(600)
            тело = кадр.locator("body")
            д = тело.evaluate(СОСТ)
            n = д["задач"]
            факт(n >= 3, f"{н} задач в главе: {n}")
            факт(д["открыты"][:1] == [True] and not any(д["открыты"][1:]) and д["содержимое"] == д["открыты"],
                 f"{н} при открытии развёрнута первая задача, остальные — строкой: {д['открыты']}, видно содержимое {д['содержимое']}")
            факт(д["aria"] == [str(о).lower() for о in д["открыты"]], f"{н} aria-expanded по состоянию: {д['aria']}")
            факт(д["кнопка"] == "Свернуть все", f"{н} кнопка: {д['кнопка']!r}")
            факт(all(с_ and с_["вКолонке"] and 0 <= с_["зазор"] <= 26 for с_ in д["стрелки"]), f"{н} стрелка рядом с меткой и в колонке: {д['стрелки'][:3]}")
            факт(д["вширь"] <= 0, f"{н} страница не шире окна: {д['вширь']}")
            р = max(д["названия"]) - min(д["названия"]) if д["названия"] else 99
            факт(р <= .5, f"{н} названия задач начинаются в одну линию, как бы ни был узок номер: разброс {р:.1f} px")
            поле = тело.evaluate(ПОЛЕ, 1)
            факт(поле >= 44, f"{н} поле нажатия свёрнутой строки: {поле} px")
            if not кадр.locator("#tskCtl").count() or not кадр.locator("#ch-tasks .tsk-chev").count():
                факт(False, f"{н} сворачивания нет: ни кнопки «Свернуть все», ни стрелок у задач"); стр.close(); continue
            if ш == 1440 and not ночь:
                стр.screenshot(path=str(СНИМКИ / "tasks-accordion-1440.png"))
            # Нажатие и Enter.
            кадр.locator("#ch-tasks .tsk >> nth=1").locator(".tsk-head").click(); стр.wait_for_timeout(250)
            д = тело.evaluate(СОСТ)
            факт(д["открыты"][1] and д["содержимое"][1] and д["aria"][1] == "true", f"{н} нажатие раскрыло вторую задачу: {д['открыты'][:3]}")
            кадр.locator("#ch-tasks .tsk >> nth=1").locator(".tsk-head").press("Enter"); стр.wait_for_timeout(250)
            д = тело.evaluate(СОСТ)
            факт(not д["открыты"][1] and not д["содержимое"][1], f"{н} Enter свернул её обратно: {д['открыты'][:3]}")
            # Свернуть все / развернуть все.
            кадр.locator("#tskCtl").click(); стр.wait_for_timeout(250)
            д = тело.evaluate(СОСТ)
            факт(not any(д["открыты"]) and д["кнопка"] == "Развернуть все", f"{н} «Свернуть все»: {д['открыты']}, кнопка {д['кнопка']!r}")
            if ш == 1440 and not ночь:
                стр.screenshot(path=str(СНИМКИ / "tasks-accordion-1440-all.png"))
            кадр.locator("#tskCtl").click(); стр.wait_for_timeout(250)
            д = тело.evaluate(СОСТ)
            факт(all(д["открыты"]) and all(д["содержимое"]) and д["кнопка"] == "Свернуть все", f"{н} «Развернуть все»: {д['открыты']}")
            # Поиск к тексту свёрнутой задачи.
            кадр.locator("#tskCtl").click(); стр.wait_for_timeout(250)
            найдено = тело.evaluate("""() => { const т = document.querySelectorAll('#ch-tasks .tsk')[2]; const п = т.querySelector('p, li');
              const слово = п.textContent.trim().split(/\\s+/).slice(0, 4).join(' ');
              const пол = document.getElementById('guideSearch'); пол.value = слово; doSearch(слово);
              const и = [...document.querySelectorAll('.srch-item')].findIndex(э => э.textContent.includes(слово.slice(0, 20)));
              if (и < 0) return { слово, и };
              goHit(и); return { слово, и }; }""")
            стр.wait_for_timeout(700)
            д = тело.evaluate(СОСТ)
            факт(найдено["и"] >= 0 and д["открыты"][2], f"{н} переход из поиска раскрыл третью задачу: {найдено}, {д['открыты'][:4]}")
            # Печать.
            стр.emulate_media(media="print"); стр.wait_for_timeout(200)
            п = тело.evaluate("""() => ({ содержимое: [...document.querySelectorAll('#ch-tasks .tsk')].every(т => [...т.children].filter(э => !э.classList.contains('tsk-head')).some(э => getComputedStyle(э).display !== 'none')),
              стрелок: [...document.querySelectorAll('#ch-tasks .tsk-chev')].filter(э => getComputedStyle(э).display !== 'none').length,
              кнопка: getComputedStyle(document.getElementById('tskCtlRow')).display })""")
            стр.emulate_media(media="screen")
            факт(п["содержимое"] and п["стрелок"] == 0 and п["кнопка"] == "none", f"{н} в печати всё развёрнуто, без стрелок и кнопки: {п}")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                факт(False, f"{н} ошибка страницы: {о[:160]}")
            стр.close()
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: задачи лога развития сворачиваются, как выпуски журнала; кнопка, поиск и печать работают; 1440 и 390, день и ночь.")
