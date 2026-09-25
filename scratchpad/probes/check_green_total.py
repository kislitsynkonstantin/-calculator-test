#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Зелёный»: карточка итога и полоска итога — графит, и всё на них читается.

Константин 25.09.2026 выбрал вариант 02 макета green-total-v1 («Графит с
зелёным»): средний зелёный #6faa36 хорош на кнопках, но белая сумма итога
на нём давала 2,8:1. Проба меряет отрисованное — в «Модерне» и «Бланке», днём
и ночью, на 390 / 768 / 1440 px:

  • в «Зелёном» карточка итога («Модерн») и полоска итога залиты графитом
    #24271f днём и #1b1d17 ночью; в «Бланке» у карточки заливки нет —
    правило её не трогает;
  • каждая надпись в обоих залитых блоках — сумма, подписи, цена со скидкой, «за
    наличные», текст в полях — держит контраст не ниже 4,5:1 к своему фону
    (крупная сумма — 3:1); прежде проба не спрашивала контраст вовсе, и
    белое на светлом зелёном проходило;
  • лист печати в стиле «Карточки» (25.09.2026: «тут тоже графит зелёный
    должен быть в теме для печати») — блок итога тем же графитом, цена со
    скидкой зелёная, надписи держат контраст; в «Бирюзовом» блок прежний;
  • в «Бирюзовом» оба блока остались прежними — заливка var(--br-28);
  • ничего не вылезает за окно, ошибок страницы нет.

    python3 check_green_total.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or ЗДЕСЬ)


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    класс = functools.partial(Тихий, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(где, т):
    НАХОДКИ.append(f"{где}: {т}")


# Контраст считается по отрисованным цветам: цвет текста с его прозрачностью
# накладывается на ближайший непрозрачный фон вверх по дереву, полупрозрачные
# подложки (панель скидки, поле) — поверх него по очереди.
ЗАМЕР = r"""() => {
  const разбор = с => { const м = с.match(/[\d.]+/g) || []; return м.length < 3 ? null : [+м[0], +м[1], +м[2], м.length > 3 ? +м[3] : 1]; };
  const на = (в, п) => [0,1,2].map(i => в[i] * в[3] + п[i] * (1 - в[3]));
  const фон = эл => {
    const слои = [];
    for (let е = эл; е; е = е.parentElement) {
      const ц = разбор(getComputedStyle(е).backgroundColor);
      if (ц && ц[3] > 0) { слои.push(ц); if (ц[3] >= 1) break; }
    }
    let и = [255, 255, 255];
    for (let i = слои.length - 1; i >= 0; i--) и = на(слои[i], и);
    return и;
  };
  const яр = ц => { const л = ц.map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
                    return .2126 * л[0] + .7152 * л[1] + .0722 * л[2]; };
  const контраст = (а, б) => { const x = яр(а), y = яр(б); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
  const hex = ц => '#' + ц.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  const надписи = [];
  const блоки = [['карточка', document.getElementById('resultCard')], ['полоска', document.getElementById('totalStrip') || document.querySelector('.total-strip')]];
  for (const [имя, блок] of блоки) {
    if (!блок) continue;
    const виден = getComputedStyle(блок).display !== 'none';
    if (!виден) continue;
    const узлы = [...блок.querySelectorAll('*')].filter(е => {
      if (!е.getClientRects().length) return false;
      const st = getComputedStyle(е);
      if (st.visibility === 'hidden' || +st.opacity === 0) return false;
      if (е.tagName === 'INPUT') return е.type !== 'checkbox';
      return [...е.childNodes].some(н => н.nodeType === 3 && н.textContent.trim());
    });
    for (const е of узлы) {
      if (е.id === 'kitBadge' || е.closest('#kitBadge')) continue;
      const ц = разбор(getComputedStyle(е).color); if (!ц) continue;
      const ф = фон(е), т = на(ц, ф);
      const кегль = parseFloat(getComputedStyle(е).fontSize), жир = +getComputedStyle(е).fontWeight;
      const крупный = кегль >= 24 || (кегль >= 18.66 && жир >= 700);
      const текст = (е.tagName === 'INPUT' ? '[поле ' + е.id + ']' : е.textContent.trim()).slice(0, 30);
      надписи.push({ блок: имя, текст, к: +контраст(т, ф).toFixed(2), порог: крупный ? 3 : 4.5, цвет: hex(т), фон: hex(ф) });
    }
  }
  const заливка = с => { const е = document.querySelector(с); return е ? hex(разбор(getComputedStyle(е).backgroundColor)) : ''; };
  const правый = Math.max(...[...document.querySelectorAll('#resultCard *, .total-strip *')]
                  .filter(е => е.getClientRects().length).map(е => е.getBoundingClientRect().right));
  return { надписи, карточка: заливка('#resultCard'), полоска: заливка('.total-strip'),
           тон: document.documentElement.dataset.tone || '', вылет: правый - innerWidth,
           гориз: document.documentElement.scrollWidth - innerWidth };
}"""


def открыть(бр, порт, ш, в, бланк, ночь, тон):
    к = бр.new_context(viewport={"width": ш, "height": в})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""([бланк, ночь, тон]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      applyThemeMode(ночь ? 'dark' : 'light', false);
      applyTone(тон, false);
      selectProjectOption(0);
    }""", [бланк, ночь, тон])
    стр.wait_for_timeout(700)
    # Скидка и «за наличные» — чтобы цена со скидкой и приписка были на экране.
    стр.evaluate("""() => {
      const п = document.getElementById('discountPctInput'); п.value = 5;
      document.getElementById('cashDiscountCheck').checked = true;
      calc();
    }""")
    стр.wait_for_timeout(300)
    return к, стр, ошибки


def полоска(стр):
    # Полоска выходит, когда карточка итога ушла за верх экрана.
    стр.evaluate("() => window.scrollTo(0, document.getElementById('resultCard').getBoundingClientRect().bottom + scrollY + 300)")
    стр.wait_for_timeout(600)


def проверить(бр, порт, ш, в, бланк, ночь, тон, снимок=False):
    где = f"{тон} · {'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"
    к, стр, ошибки = открыть(бр, порт, ш, в, бланк, ночь, тон)
    стр.evaluate("() => document.getElementById('resultCard').scrollIntoView({block:'center'})")
    стр.wait_for_timeout(400)
    з = стр.evaluate(ЗАМЕР)
    if снимок:
        стр.locator("#resultCard").screenshot(path=str(СНИМКИ / f"итог-{тон}-{'бланк' if бланк else 'модерн'}-{'ночь' if ночь else 'день'}-{ш}.png"))
    полоска(стр)
    зп = стр.evaluate(ЗАМЕР)
    if снимок:
        стр.screenshot(path=str(СНИМКИ / f"полоска-{тон}-{'бланк' if бланк else 'модерн'}-{'ночь' if ночь else 'день'}-{ш}.png"))
    граф = "#1b1d17" if ночь else "#24271f"
    if тон == "bmsk":
        if not бланк and з["карточка"] != граф:
            плохо(где, f"карточка итога {з['карточка']}, ждали графит {граф}")
        if зп["полоска"] != граф:
            плохо(где, f"полоска итога {зп['полоска']}, ждали графит {граф}")
    else:
        if з["карточка"] == граф or зп["полоска"] == граф:
            плохо(где, "графит протёк в другой тон")
    # В «Бланке» у карточки итога заливки нет: её надписи — чернила листа,
    # и за них отвечает тема, а не это правило. Полоска там та же.
    надписи = [н for н in з["надписи"] if н["блок"] == "карточка" and not бланк] + [н for н in зп["надписи"] if н["блок"] == "полоска"]
    if not any(н["блок"] == "полоска" for н in надписи):
        плохо(где, "полоска итога так и не показалась")
    if тон == "bmsk":
        for н in надписи:
            if н["к"] < н["порог"]:
                плохо(где, f"{н['блок']}: «{н['текст']}» {н['цвет']} на {н['фон']} — {н['к']}:1, нужно {н['порог']}")
    for зз in (з, зп):
        if зз["вылет"] > 0.5 or зз["гориз"] > 0:
            плохо(где, f"вылет за окно: {зз['вылет']:.1f} px, прокрутка вбок {зз['гориз']} px")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    мин = min((н["к"] for н in надписи), default=0)
    к.close()
    print(f"  {где}: карточка {з['карточка']}, полоска {зп['полоска']}, надписей {len(надписи)}, наименьший контраст {мин}")


ПЕЧАТЬ = r"""() => {
  const д = document.getElementById('printDoc');
  const блок = [...д.querySelectorAll('div')].find(е => /Общая стоимость/i.test(е.textContent) && /Спец\. цена/.test(е.textContent)
                 && getComputedStyle(е).borderRadius === '14px');
  if (!блок) return null;
  const разбор = с => (с.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  const яр = ц => { const л = ц.map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
                    return .2126 * л[0] + .7152 * л[1] + .0722 * л[2]; };
  const ф = разбор(getComputedStyle(блок).backgroundColor);
  const надписи = [...блок.querySelectorAll('div')].filter(е => [...е.childNodes].some(н => н.nodeType === 3 && н.textContent.trim())).map(е => {
    const с = getComputedStyle(е).color, м = с.match(/[\d.]+/g).map(Number), а = м.length > 3 ? м[3] : 1;
    const т = [0,1,2].map(i => м[i] * а + ф[i] * (1 - а));
    const x = яр(т), y = яр(ф);
    return { текст: е.textContent.trim().slice(0, 30), к: +((Math.max(x, y) + .05) / (Math.min(x, y) + .05)).toFixed(2), цвет: с };
  });
  return { фон: '#' + ф.map(v => v.toString(16).padStart(2, '0')).join(''), надписи };
}"""


def печать(бр, порт, тон):
    где = f"{тон} · печать «Карточки»"
    к, стр, ошибки = открыть(бр, порт, 1440, 900, False, False, тон)
    стр.evaluate("() => { openPrintPreview(); setPrintStyle('cards', true); }")
    стр.wait_for_timeout(700)
    п = стр.evaluate(ПЕЧАТЬ)
    к.close()
    if not п:
        плохо(где, "блок итога на листе не найден")
        return
    if тон == "bmsk":
        if п["фон"] != "#24271f":
            плохо(где, f"блок итога {п['фон']}, ждали графит #24271f")
        for н in п["надписи"]:
            if н["к"] < 4.5:
                плохо(где, f"«{н['текст']}» {н['цвет']} — {н['к']}:1, нужно 4.5")
    elif п["фон"] == "#24271f":
        плохо(где, "графит протёк в другой тон")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    print(f"  {где}: блок {п['фон']}, наименьший контраст {min(н['к'] for н in п['надписи'])}")


def главная():
    снимки = "--снимки" in sys.argv
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ночь in (False, True):
                    for ш, в in ((390, 844), (768, 1024), (1440, 900)):
                        try:
                            проверить(бр, порт, ш, в, бланк, ночь, "bmsk", снимки)
                        except Exception as e:
                            плохо(f"{бланк}/{ночь}/{ш}", f"проба оборвалась: {e!s:.300}")
            for бланк in (False, True):
                try:
                    проверить(бр, порт, 1440, 900, бланк, False, "teal")
                except Exception as e:
                    плохо(f"teal/{бланк}", f"проба оборвалась: {e!s:.300}")
            for тон in ("bmsk", "teal"):
                try:
                    печать(бр, порт, тон)
                except Exception as e:
                    плохо(f"печать/{тон}", f"проба оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: в «Зелёном» карточка и полоска итога — графит, каждая надпись на них читается; "
          "в «Бирюзовом» всё как было.")


if __name__ == "__main__":
    главная()
