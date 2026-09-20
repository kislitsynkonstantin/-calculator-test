#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Комплектация не пишется поверх открытого расчёта, и несохранённое видно.

Константин 20.09.2026: «когда выбран у менеджера пресет активный и он из этого
пресета выбирает комплектацию — комплектация переписывает весь пресет. Все
данные с пресета уходят… так менеджер случайно может затереть расчёт». И там
же: «добавь сообщение… когда менеджер выбрал проект, но не сохранил ещё
пресет. Как напоминание сохранить, чтобы случайно не закрыл».

Затирание чужой работы не ловится глазами: расчёт открыт, набор применён,
на экране всё хорошо — а прежнего содержимого пресета уже нет. Поэтому проба
смотрит в само хранилище, а не на экран:

  • снимок пресета до применения набора и после — он обязан совпасть;
  • расчёт после набора отвязан от пресета: автосохранению писать некуда;
  • сказано словами, что расчёт стал новым, и назван прежний;
  • напоминание висит, пока расчёт не сохранён, и гаснет, как только он
    привязан; крестик его убирает, новый проект возвращает.

    python3 check_kit_not_overwrite.py
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
ЗДЕСЬ = pathlib.Path(__file__).parent
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


ПОЛОСКА = """() => {
  const п = document.getElementById('saveReminder');
  if (!п) return { есть: false };
  const к = п.getBoundingClientRect();
  const кн = п.querySelector('.sv-go');
  const кр = п.querySelector('.sv-x');
  const поле = э => { if (!э) return 0;
    const b = э.getBoundingClientRect();
    const с = getComputedStyle(э, '::before');
    return Math.round(b.height - 2 * (parseFloat(с.top) || 0)); };
  return {
    есть: true,
    видна: getComputedStyle(п).display !== 'none' && к.height > 0,
    текст: (п.textContent || '').trim(),
    фон: getComputedStyle(п).backgroundColor,
    зеленее: (() => { const ф = getComputedStyle(п).backgroundColor.match(/\\d+/g) || [];
      const [r, g, b] = ф.slice(0, 3).map(Number);
      return g > r + 24 && g > b + 24; })(),
    вОкне: к.left >= -1 && к.right <= window.innerWidth + 1
           && к.bottom <= window.innerHeight + 1,
    полеКнопки: поле(кн), полеКрестика: поле(кр),
    // Два расширенных поля рядом перекрываются молча: каждое по отдельности
    // 44 px, а нажатие у края уходит соседу — и «убрать напоминание»
    // оказывается «сохранить», или наоборот.
    поляНаходят: (() => {
      const поле = э => { const b = э.getBoundingClientRect();
        const с = getComputedStyle(э, '::before');
        const вв = parseFloat(с.left) || 0;
        return { l: b.left + вв, r: b.right - вв }; };
      if (!кн || !кр) return false;
      const a = поле(кн), b = поле(кр);
      return a.r > b.l + 0.5 && a.l < b.r - 0.5;
    })(),
  };
}"""

# Всё, что стоит внизу по центру и способно закрыть соседа: сообщение,
# напоминание сохранить, полоска общего расчёта, полоска итога.
НИЗ = """() => {
  const кто = { тост: 'toastMsg', напоминание: 'saveReminder',
                общий: 'sharedModeIndicator', итог: 'totalStrip' };
  const вышло = {};
  for (const [имя, ид] of Object.entries(кто)) {
    const э = document.getElementById(ид);
    if (!э) continue;
    const с = getComputedStyle(э);
    const к = э.getBoundingClientRect();
    if (с.display === 'none' || с.visibility === 'hidden'
        || parseFloat(с.opacity || '1') < 0.05 || к.height < 1) continue;
    вышло[имя] = { top: к.top, bottom: к.bottom, left: к.left, right: к.right };
  }
  return вышло;
}"""


def накладки(низ):
    """Пары, которые перекрылись или сошлись вплотную.

    Меряется не одно пересечение: сообщение, прижатое к полоске вплотную,
    формально её не закрывает, а читаются обе как одна слипшаяся плашка.
    Зазор меньше 6 px — слипание.
    """
    имена = sorted(низ)
    вышло = []
    for i, а in enumerate(имена):
        for б in имена[i + 1:]:
            п, в = низ[а], низ[б]
            if п["right"] <= в["left"] + 0.5 or в["right"] <= п["left"] + 0.5:
                continue          # стоят в разных половинах строки
            зазор = max(в["top"] - п["bottom"], п["top"] - в["bottom"])
            if зазор < 6:
                вышло.append((а, б, round(зазор)))
    return вышло


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
            стр.wait_for_timeout(2600)

            стр.evaluate("""async () => {
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
            }""")

            # ── 1. Проект выбран, расчёт не сохранён — напоминание висит ──
            п1 = стр.evaluate(ПОЛОСКА)
            if not п1.get("есть"):
                плохо("проект выбран, расчёт нигде не сохранён, а напоминания нет")
            else:
                if not п1["видна"]:
                    плохо("напоминание в разметке есть, но не видно")
                if "не сохранён" not in п1["текст"]:
                    плохо(f"напоминание не говорит о несохранённом: «{п1['текст'][:60]}»")
                if п1["зеленее"]:
                    плохо(f"напоминание зелёное ({п1['фон']}) — зелёным помечен "
                          "общий расчёт, у которого правки как раз сохраняются; "
                          "одинаковый вид у противоположных состояний")
                if not п1["вОкне"]:
                    плохо("напоминание вылезло за край окна")
                if п1.get("поляНаходят"):
                    плохо("поля нажатия «Сохранить» и крестика перекрываются — "
                          "нажатие у края уйдёт соседу")
                for имя, в in (("«Сохранить»", п1["полеКнопки"]),
                               ("крестика", п1["полеКрестика"])):
                    if в < 44:
                        плохо(f"поле нажатия {имя} в напоминании {в} px — меньше 44")

            # ── 2. Сохранили расчёт в пресет — напоминание гаснет ──
            снимок = стр.evaluate("""async () => {
              const ид = 'проба1';
              const все = loadAllPresets();
              все[ид] = { id: ид, name: 'Расчёт клиента Иванова',
                          savedAt: new Date().toISOString(),
                          state: collectState() };
              localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(все));
              setActivePreset(ид);
              await new Promise(r => setTimeout(r, 400));
              return JSON.stringify(loadAllPresets()[ид].state);
            }""")
            п2 = стр.evaluate(ПОЛОСКА)
            if п2.get("есть") and п2.get("видна"):
                плохо("расчёт привязан к пресету, а напоминание сохранить "
                      "по-прежнему висит")

            # ── 3. Применили комплектацию — пресет обязан уцелеть ──
            итог = стр.evaluate("""async () => {
              window.__вести = [];
              const прежний = window.showToast;
              window.showToast = т => { window.__вести.push(String(т)); };
              komplSelected = 'comfort';
              await applyKompl();
              // Автосохранение отложенное: ждём заведомо дольше его паузы,
              // иначе проба разошлась бы с бедой, которую ловит, — она как
              // раз и случается через секунду после применения.
              await new Promise(r => setTimeout(r, 3500));
              window.showToast = прежний;
              const п = loadAllPresets()['проба1'];
              return {
                живПресет: !!п,
                состояние: п ? JSON.stringify(п.state) : null,
                активный: (typeof activePresetId !== 'undefined') ? activePresetId : null,
                вести: (window.__вести || []).slice(),
              };
            }""")
            if not итог["живПресет"]:
                плохо("после применения комплектации пресет исчез из списка")
            elif итог["состояние"] != снимок:
                плохо("комплектация переписала сохранённый пресет: его состояние "
                      "после применения не то, что было до — это и есть затёртый "
                      "расчёт клиента")
            if итог["активный"]:
                плохо(f"после комплектации расчёт остался привязан к пресету "
                      f"«{итог['активный']}» — следующая же правка ляжет поверх него")
            вести = " ".join(итог["вести"] or [])
            if "новый расчёт" not in вести:
                плохо("расчёт стал новым, а сказано об этом не было: "
                      f"«{вести[:90]}»")
            if "Иванова" not in вести:
                плохо("в сообщении не назван расчёт, от которого отвязались — "
                      "менеджеру негде увидеть, что именно осталось как было")

            # ── 4. Расчёт снова несохранён — напоминание вернулось ──
            стр.wait_for_timeout(400)
            п3 = стр.evaluate(ПОЛОСКА)
            if not (п3.get("есть") and п3.get("видна")):
                плохо("после комплектации расчёт нигде не сохранён, "
                      "а напоминания нет")

            # ── 5. Крестик убирает, новый проект возвращает ──
            стр.evaluate("() => снятьНапоминаниеСохранить()")
            стр.wait_for_timeout(250)
            if стр.evaluate(ПОЛОСКА).get("видна"):
                плохо("крестик нажат, а напоминание осталось")
            стр.evaluate("""async () => {
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 6'));
              selectProjectOption(и >= 0 ? и : 1);
              await new Promise(r => setTimeout(r, 1000));
            }""")
            if not стр.evaluate(ПОЛОСКА).get("видна"):
                плохо("выбран новый проект, а снятое прежде напоминание не "
                      "вернулось — один крестик выключил его навсегда")

            # ── 6. Сообщение не ложится на полоску напоминания ──
            # Константин 20.09.2026 прислал снимок применённой комплектации:
            # сообщение легло прямо на полоску «Расчёт не сохранён», и обе
            # читались наполовину. Обе стоят внизу по центру, и подъёмы у
            # тоста были только над полоской итога и над полоской общего
            # расчёта. Гоняем и с полоской итога тоже: она поднимает
            # напоминание, а снятая прежде мерка осталась бы старой.
            for ширина, высота in ((390, 844), (1440, 950)):
                стр.set_viewport_size({"width": ширина, "height": высота})
                for итоговая in (False, True):
                    стр.evaluate("""async (низ) => {
                      window.scrollTo(0, низ ? document.body.scrollHeight : 0);
                      await new Promise(r => setTimeout(r, 450));
                      if (typeof refreshTotalStrip === 'function') refreshTotalStrip();
                      _напоминаниеСнято = false;
                      обновитьНапоминаниеСохранить();
                      await new Promise(r => setTimeout(r, 350));
                      showToast('Комплектация «Тёплый контур» применена — '
                                + 'не вошли 2 позиции');
                    }""", итоговая)
                    стр.wait_for_timeout(500)
                    где = f"{ширина}px" + (" с полоской итога" if итоговая else "")
                    низ = стр.evaluate(НИЗ)
                    if "напоминание" not in низ:
                        плохо(f"[{где}] напоминание пропало — накладку мерить не на чем")
                    elif "тост" not in низ:
                        плохо(f"[{где}] сообщение не показалось — "
                              "накладку мерить не на чем")
                    for а, б, зазор in накладки(низ):
                        плохо(f"[{где}] «{а}» и «{б}» сошлись внизу: зазор "
                              f"{зазор} px — читаются одной слипшейся плашкой, "
                              "а при отрицательном одна закрывает другую")
            стр.set_viewport_size({"width": 1440, "height": 950})

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:220])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: комплектация не трогает сохранённый пресет и отвязывает от "
          "него расчёт, сказав об этом словами; напоминание сохранить висит "
          "ровно тогда, когда расчёт не сохранён нигде.")


if __name__ == "__main__":
    главная()
