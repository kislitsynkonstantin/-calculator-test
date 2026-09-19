#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба темы «Бланк» и замка комплектаций.

Четыре правки 19.09.2026 по снимкам Константина:

  • ряд вкладок редактора — кнопки не наезжают на вкладки и не касаются нижней
    линейки ряда: «кнопка наехала на полоску»;
  • замок комплектаций переключается сразу, не дожидаясь ответа базы, а при
    отказе возвращается как было: с телефона ожидание длилось секунды, и его
    принимали за непопадание по кнопке;
  • окно «Данные для договора» в «Бланке» со светлой шапкой, а не с зелёной
    от «Модерна»;
  • разделы в таблице комплектаций держатся чертой в два пикселя чернилами
    акцента, а не бледной заливкой, в которой они сливались со строками.

Проверяется отрисовка, а не разметка: и зазор, и цвет, и время берутся из
живого браузера.

    python3 check_blank_windows.py
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
ПРОЕКТ = "Проба 6×4"
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


ХРОМ = хром()
ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": ПРОЕКТ, "name": ПРОЕКТ,
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
    "project_kits": [], "project_kit_locks": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}


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
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:120])
        return None


def тема(стр, имя):
    стр.evaluate("(и) => { document.body.classList.toggle('ui-blank', и === 'blank'); }", имя)
    стр.wait_for_timeout(150)


# ── ряд вкладок: кнопки не наезжают ни на вкладки, ни на линейку ────────────
РЯД = """() => {
  const ряд = document.getElementById('kedTabsRow');
  if (!ряд) return { нет: true };
  const r = ряд.getBoundingClientRect();
  const граница = parseFloat(getComputedStyle(ряд).borderBottomWidth) || 0;
  const кнопки = [...ряд.querySelectorAll('#kedSeedBtn, #kedCopyBtn')]
    .filter(э => э.getClientRects().length);
  const вкладки = [...ряд.querySelectorAll('#kedTabsHost button')]
    .filter(э => э.getClientRects().length);
  const пересечения = [];
  кнопки.forEach(к => {
    const б = к.getBoundingClientRect();
    вкладки.forEach(в => {
      const т = в.getBoundingClientRect();
      const пересек = !(б.right <= т.left || б.left >= т.right || б.bottom <= т.top || б.top >= т.bottom);
      if (пересек) пересечения.push((к.id || 'кнопка') + ' × ' + (в.id || 'вкладка'));
    });
  });
  return {
    зазоры: кнопки.map(к => ({ ид: к.id,
      доЛинейки: Math.round(r.bottom - граница - к.getBoundingClientRect().bottom) })),
    пересечения,
  };
}"""


def проверить_ряд(стр, ширина, имяТемы):
    м = спросить(стр, РЯД)
    if not м or м.get("нет"):
        плохо("ряда вкладок редактора нет в разметке")
        return
    for п in м["пересечения"]:
        плохо(f"[{имяТемы} {ширина}] кнопка наехала на вкладку: {п}")
    for з in м["зазоры"]:
        if з["доЛинейки"] < 6:
            плохо(f"[{имяТемы} {ширина}] {з['ид']} прижата к линейке ряда: {з['доЛинейки']} px")


# ── замок: переключается сразу, при отказе возвращается ─────────────────────
ЗАМЕДЛИТЬ = """(мс) => {
  // База отвечает медленно: так ход и выглядит с телефона.
  const исх = _sb.from.bind(_sb);
  _sb.from = (табл) => {
    const о = исх(табл);
    if (табл !== 'project_kit_locks') return о;
    const прежний = о.then.bind(о);
    о.then = (ок, нет) => new Promise(r => setTimeout(r, мс)).then(() => прежний(ок, нет));
    return о;
  };
}"""

СЛОМАТЬ = """() => {
  const исх = _sb.from.bind(_sb);
  _sb.from = (табл) => {
    const о = исх(табл);
    if (табл !== 'project_kit_locks') return о;
    о.then = (ок) => Promise.resolve(ок({ data: null, error: { message: 'нет связи' } }));
    return о;
  };
}"""


def проверить_замок(стр):
    стр.evaluate(ЗАМЕДЛИТЬ, 1500)
    стр.evaluate("() => { toggleKitLock(); }")
    стр.wait_for_timeout(250)
    сразу = стр.evaluate("""() => ({
      состояние: !!_kitLocks[currentProjectSlug()],
      надпись: (document.getElementById('kitLockBtn') || {}).textContent || '' })""")
    if not сразу["состояние"]:
        плохо("замок не переключился за 250 мс — ход ждёт ответа базы, "
              "а с телефона это секунды молчания")
    if "Закрыто" not in сразу["надпись"]:
        плохо(f"значок замка не показал новое состояние сразу: «{сразу['надпись'].strip()}»")
    стр.wait_for_timeout(1600)
    if not стр.evaluate("() => !!_kitLocks[currentProjectSlug()]"):
        плохо("после ответа базы замок отвалился обратно")

    # Отказ базы: состояние обязано вернуться как было.
    стр.evaluate(СЛОМАТЬ)
    стр.evaluate("() => { toggleKitLock(); }")
    стр.wait_for_timeout(500)
    if not стр.evaluate("() => !!_kitLocks[currentProjectSlug()]"):
        плохо("база отказала, а замок остался снятым — на экране одно, в базе другое")


# ── окно «Данные для договора» в «Бланке» ───────────────────────────────────
def проверить_окно_договора(стр):
    стр.evaluate("() => { try { openContractDataModal(); } catch (e) {} }")
    стр.wait_for_timeout(400)
    м = спросить(стр, """() => {
      const ш = document.querySelector('#contractDataOverlay .ovl-head');
      if (!ш) return { нет: true };
      const с = getComputedStyle(ш);
      const имя = ш.querySelector('span');
      const рубец = getComputedStyle(ш, '::after');
      const числа = з => (з.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
      return { фон: числа(с.backgroundColor), цветИмени: имя ? числа(getComputedStyle(имя).color) : null,
               черта: рубец.height, видно: getComputedStyle(document.getElementById('contractDataOverlay')).display };
    }""")
    if not м or м.get("нет"):
        плохо("окна «Данные для договора» нет в разметке")
        return
    светлая = m_светлая(м["фон"])
    if not светлая:
        плохо(f"шапка «Данных для договора» в «Бланке» осталась тёмной: rgb({m_строка(м['фон'])}) — "
              "это зелёная шапка «Модерна»")
    if м["цветИмени"] and m_светлая(м["цветИмени"]):
        плохо("название окна осталось белым — на светлой шапке его не прочесть")
    стр.screenshot(path=str(pathlib.Path(__file__).parent / "бланк-договор.png"),
                   clip={"x": 0, "y": 0, "width": 900, "height": 240})
    стр.evaluate("() => { try { closeContractDataModal(); } catch (e) {} }")
    стр.wait_for_timeout(200)


def m_светлая(цвет):
    if not цвет or len(цвет) < 3:
        return False
    r, g, b = цвет[:3]
    return (0.299 * r + 0.587 * g + 0.114 * b) > 170


def m_строка(цвет):
    return ", ".join(str(int(з)) for з in (цвет or [])[:3])


# ── разделы в таблице комплектаций ──────────────────────────────────────────
def проверить_разделы(стр):
    стр.evaluate("() => { openKompl(); switchKomplTab('table'); }")
    стр.wait_for_timeout(400)
    м = спросить(стр, """() => {
      const раздел = document.querySelector('#komplTable tr.kompl-sec td');
      if (!раздел) return { нет: true };
      const с = getComputedStyle(раздел);
      const строка = document.querySelector('#komplTable tbody tr:not(.kompl-sec) td');
      const числа = з => (з.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
      return { черта: parseFloat(с.borderBottomWidth) || 0,
               цветЧерты: числа(с.borderBottomColor),
               цвет: числа(с.color),
               цветСтроки: строка ? числа(getComputedStyle(строка).color) : null };
    }""")
    if not м or м.get("нет"):
        плохо("в таблице комплектаций нет строк-разделов с именем класса")
        return
    if м["черта"] < 2:
        плохо(f"раздел в «Бланке» без черты: {м['черта']} px — он сливается со строками")
    яркость = 0.299 * м["цветЧерты"][0] + 0.587 * м["цветЧерты"][1] + 0.114 * м["цветЧерты"][2]
    if яркость > 150:
        плохо(f"черта раздела бледная: rgb({m_строка(м['цветЧерты'])})")
    if м["цвет"] == м["цветСтроки"]:
        плохо("название раздела набрано тем же цветом, что и строки")
    стр.locator("#komplTable").screenshot(
        path=str(pathlib.Path(__file__).parent / "бланк-разделы.png"))


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                "window.addEventListener('DOMContentLoaded', function () {\n"
                "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n"
                "});")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            спросить(стр, """async (имя) => {
              const беда = document.getElementById('pricingErrorScreen');
              if (беда) беда.style.display = 'none';
              const и = PROJECTS.findIndex(p => p[0] === имя);
              if (и >= 0) selectProjectOption(и);
              await new Promise(r => setTimeout(r, 400));
            }""", ПРОЕКТ)

            for имяТемы in ("модерн", "бланк"):
                тема(стр, "blank" if имяТемы == "бланк" else "modern")
                стр.evaluate("() => { openKompl(); switchKomplTab('editor'); }")
                for ш in (390, 768, 1440):
                    стр.set_viewport_size({"width": ш, "height": 900})
                    стр.wait_for_timeout(250)
                    проверить_ряд(стр, ш, имяТемы)
                    if ш == 390:
                        стр.screenshot(path=str(pathlib.Path(__file__).parent
                                                / f"ряд-{имяТемы}-390.png"),
                                       clip={"x": 0, "y": 90, "width": 390, "height": 230})
            стр.set_viewport_size({"width": 1440, "height": 900})
            тема(стр, "blank")
            проверить_замок(стр)
            проверить_разделы(стр)
            стр.evaluate("() => { try { closeKompl(); } catch (e) {} }")
            проверить_окно_договора(стр)

            важные = [о for о in ошибки if "supabase.co" not in о and "цены" not in о]
            for о in важные[:3]:
                плохо("ошибка страницы: " + о[:160])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: ряд вкладок без наездов и с зазором до линейки, замок переключается "
          "сразу и возвращается при отказе, шапка «Данных для договора» светлая, "
          "разделы таблицы держатся чертой.")


if __name__ == "__main__":
    главная()
