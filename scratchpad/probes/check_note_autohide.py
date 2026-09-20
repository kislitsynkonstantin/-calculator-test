#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: примечание, которое прячется само, действительно прячется.

Константин 20.09.2026, двумя снимками: «когда нажимаю галочку на обработку
террасной доски, выходит уведомление, что скрыто примечание про лессирующую
краску. Но примечание не скрывается… уведомление ложное. Должно быть вот так:
выбираем террасу — скрывается примечание по ней. До этого было всё нормально,
там что-то сдвинулось».

Сдвинулось вот что: ключ скрытого примечания получил приставку технологии
(`frame_paint_0`), а автоматика осталась на прежнем «раздел_номер». Она писала
ключ, которого никто не читает: примечание оставалось на месте, а сообщение
всё равно выходило. Поэтому проба меряет не флаг и не ключ, а три вещи разом:
строку на экране, строку в листе для печати и текст сообщения.

Проверяется по каждому правилу из `NOTE_AUTOHIDE`, какие бы они ни были:

  • текст правила есть среди примечаний своего раздела — опечатка в тексте
    делает правило немым, и заметить это иначе нельзя;
  • отметил опцию — примечание погасло на экране и ушло из листа печати;
  • сообщение назвало именно то примечание, которое погасло;
  • снял отметку — примечание вернулось и на экран, и в лист.

Отдельно — условные примечания печи, водостока и снегозадержателей: у них
ключи без номера, и проба смотрит, что они не сломались заодно.

    python3 check_note_autohide.py
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

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

ТАБЛИЦЫ_JS = (
    "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};"
    "window.__ТАБЛИЦЫ.pricing_projects = [1,2].map(и => ({"
    "  product: 'frame', sort: и, slug: 'Проба ' + и, name: 'Проба ' + и,"
    "  price_100: 1000000, price_150: 1200000, price_200: 1400000,"
    "  floors: 1, roof_type: 'двускатная', warm: true,"
    "  open_area: 10, closed_area: 20, facade_area: 60,"
    "  paint_area: 60, roof_area: 40 }));")


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(текст):
    НАХОДКИ.append(текст)


def спросить(стр, js, *арг):
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:130])
        return None


# Одно правило целиком: отметить опцию, посмотреть экран и лист, снять.
ПРОВЕРИТЬ = """async (н) => {
  const тексты = SECTION_NOTES[н.раздел] || [];
  const место = тексты.indexOf(н.текст);
  if (место === -1) return { нетТекста: true };

  const строка = () => [...document.querySelectorAll('.note-item')]
    .find(э => (э.innerText || '').includes(н.текст.slice(0, 40)));
  const погашена = () => { const с = строка(); return с ? с.classList.contains('note-hidden') : null; };
  const вЛисте = async () => {
    openPrintPreview();
    await new Promise(r => setTimeout(r, 700));
    const л = document.getElementById('printDoc');
    const есть = л ? л.innerText.includes(н.текст.slice(0, 40)) : null;
    closePrintPreview();
    await new Promise(r => setTimeout(r, 200));
    return есть;
  };

  window.__тосты = [];
  const прежний = window.showToast;
  window.showToast = (т) => { window.__тосты.push(String(т)); };

  const доЭкран = погашена();
  const доЛист = await вЛисте();

  checkedOptions[н.опция] = true;
  const я = document.getElementById('lbl_' + н.опция);
  if (я) я.classList.add('active');
  const в = document.getElementById('chk_' + н.опция);
  if (в) в.checked = true;
  _autoHideОтРуки = true;      // сообщения выходят только на живом действии
  calc();
  await new Promise(r => setTimeout(r, 500));

  const послеЭкран = погашена();
  const послеЛист = await вЛисте();
  const тосты = window.__тосты.slice();

  checkedOptions[н.опция] = false;
  if (я) я.classList.remove('active');
  if (в) в.checked = false;
  calc();
  await new Promise(r => setTimeout(r, 500));
  const вернулосьЭкран = погашена();
  const вернулосьЛист = await вЛисте();

  window.showToast = прежний;
  return { место, доЭкран, доЛист, послеЭкран, послеЛист, тосты,
           вернулосьЭкран, вернулосьЛист };
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
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            спросить(стр, """async () => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              const и = PROJECTS.findIndex(x => x && x[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
            }""")

            правила = спросить(стр, """() => (typeof NOTE_AUTOHIDE === 'undefined' ? null
              : NOTE_AUTOHIDE.map(п => ({ раздел: п.section, текст: п.note,
                                          опции: (п.options || []).slice() })))""")
            if not правила:
                плохо("правил автоскрытия в файле нет — проверять нечего")
                правила = []
            if len(правила) < 2:
                плохо(f"правил всего {len(правила)} — раньше их было больше, "
                      "проба смотрела бы в пустоту")

            for п in правила:
                имя = п["текст"][:46]
                живые = [о for о in п["опции"]]
                if not живые:
                    # Правило только по палитре — отметить нечего, но текст
                    # всё равно обязан находиться.
                    есть = спросить(стр, """(н) => (SECTION_NOTES[н.раздел] || []).indexOf(н.текст) !== -1""", п)
                    if not есть:
                        плохо(f"«{имя}…»: текста правила нет среди примечаний раздела "
                              f"«{п['раздел']}» — правило немое")
                    continue
                # Опция должна существовать в каталоге, иначе правило мёртвое.
                опция = спросить(стр, """(живые) => живые.find(ид => OPTIONS.some(o => o.id === ид)) || null""", живые)
                if not опция:
                    плохо(f"«{имя}…»: ни одной опции правила нет в каталоге — правило мёртвое")
                    continue
                м = спросить(стр, ПРОВЕРИТЬ,
                             {"раздел": п["раздел"], "текст": п["текст"], "опция": опция}) or {}
                if м.get("нетТекста"):
                    плохо(f"«{имя}…»: текста правила нет среди примечаний раздела "
                          f"«{п['раздел']}» — правило немое, и заметить это иначе нельзя")
                    continue
                if м.get("доЭкран") is None:
                    плохо(f"«{имя}…»: строки примечания нет на экране — мерить нечего")
                    continue
                if м.get("доЭкран"):
                    плохо(f"«{имя}…»: примечание погашено ещё до отметки опции — "
                          "проба мерила бы вхолостую")
                    continue
                if not м.get("послеЭкран"):
                    плохо(f"«{имя}…»: опция «{опция}» отмечена, а примечание на экране "
                          "не погасло")
                if м.get("послеЛист"):
                    плохо(f"«{имя}…»: примечание осталось в листе для печати — "
                          "у клиента строка, которой в расчёте уже нет")
                тосты = м.get("тосты") or []
                про_себя = [т for т in тосты if п["текст"][:30] in т]
                чужие = [т for т in тосты if "примечание" in т.lower() and т not in про_себя]
                if not про_себя and тосты:
                    плохо(f"«{имя}…»: сообщение вышло не про это примечание: "
                          + "; ".join(т.replace("\n", " ")[:70] for т in тосты)[:150])
                if чужие:
                    плохо(f"«{имя}…»: заодно вышло ложное сообщение про чужое примечание: "
                          + "; ".join(т.replace("\n", " ")[:70] for т in чужие)[:150])
                if м.get("вернулосьЭкран"):
                    плохо(f"«{имя}…»: отметку сняли, а примечание осталось погашенным")
                if not м.get("вернулосьЛист"):
                    плохо(f"«{имя}…»: отметку сняли, а в лист примечание не вернулось")

            # ── Условные примечания без номера ──
            усл = спросить(стр, """async () => {
              const из = {};
              const проверить = async (текст, опция) => {
                const строка = () => [...document.querySelectorAll('.note-item')]
                  .find(э => (э.innerText || '').includes(текст.slice(0, 30)));
                const до = строка() ? строка().classList.contains('note-hidden') : null;
                checkedOptions[опция] = true;
                _autoHideОтРуки = true;
                calc();
                await new Promise(r => setTimeout(r, 400));
                const после = строка() ? строка().classList.contains('note-hidden') : null;
                checkedOptions[опция] = false;
                calc();
                await new Promise(r => setTimeout(r, 400));
                из[текст.slice(0, 24)] = { до, после };
              };
              const печь = OPTIONS.find(o => o.section === 'stove');
              if (печь) await проверить('Печь не входит в базовую комплектацию', печь.id);
              await проверить('Водосточная система не входит в стоимость', 'r12');
              await проверить('Снегозадержатели не входят в стоимость', 'r10');
              return из;
            }""") or {}
            for текст, м in усл.items():
                if м.get("до") is None:
                    плохо(f"условного примечания «{текст}…» нет на экране — мерить нечего")
                elif м.get("до"):
                    плохо(f"условное примечание «{текст}…» погашено до отметки — вхолостую")
                elif not м.get("после"):
                    плохо(f"условное примечание «{текст}…» не погасло по своей опции")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: каждое самоскрывающееся примечание гаснет по своей опции — "
          "на экране и в листе, — сообщение называет именно его, а снятая "
          "отметка возвращает строку.")


if __name__ == "__main__":
    главная()
