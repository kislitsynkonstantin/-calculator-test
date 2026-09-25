#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Код пресета: выдаётся при каждом сохранении и стоит мелко в углу листа печати.

25.09.2026 Константин: у сохранения Артёма в журнале нет кода — «менеджер
когда сохраняет пресет — сразу присваивай ему код и в журнале этот код
пиши». Разбор базы: у трёх менеджеров из четырёх новые пресеты уходили в
облако без кода и без публикации. Код кладётся в локальную копию, а она не
записывалась — память браузера полна, — и `назначитьКодПресету` молча
возвращала пустоту. Затем: «зашей в PDF внизу справа очень очень мелкий
шрифт код пресета… код есть всегда».

Проба держит:
  • память браузера полна — пресет всё равно получает код и код уходит в
    журнал (с (32) пресеты в браузер не пишутся вовсе — проба это держит);
  • печать несохранённого расчёта сохраняет его пресетом и ставит код в
    правый нижний угол листа: «код 123 456», 3,5 pt, светло-серым;
  • печать уже сохранённого берёт его код и нового пресета не заводит;
  • штамп на листе внутри страницы, у правого нижнего края, и мельче любого
    текста листа;
  • тот же код стоит на листе предпросмотра — во всех шести стилях, на 390 и
    1440 px, в правом нижнем углу, не наезжая на текст; открытие
    предпросмотра несохранённого расчёта код уже даёт (Константин,
    25.09.2026: «не вижу код пресета в версии для печати»); в окно печати
    штамп предпросмотра не уходит, печать по договорам код несёт.

    python3 check_print_code.py
"""
import functools, http.server, json, os, pathlib, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


# Окно печати подменяем: записанный в него документ забираем и печать не зовём.
ПОДМЕНА = r"""() => {
  window.__листы = []; window.__журнал = [];
  window.open = () => { const д = { html: '' }; window.__листы.push(д);
    return { document: { write: h => { д.html += h; }, close() {} }, focus() {}, print() {} }; };
  const был = window.logEvent;
  window.logEvent = function (тип, дет) { window.__журнал.push({ тип, дет }); try { return был.apply(this, arguments); } catch (e) {} };
}"""


def страница(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      try { localStorage.removeItem(PRESET_STORAGE_KEY); } catch (e) {}
      selectProjectOption(0); calc(); }""")
    стр.wait_for_timeout(400)
    стр.evaluate(ПОДМЕНА)
    return стр, ошибки


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

            # 1. Память браузера полна.
            стр, ошибки = страница(бр, порт)
            р = стр.evaluate("""async () => {
              const был = Storage.prototype.setItem;
              Storage.prototype.setItem = function (к, в) { if (к === PRESET_STORAGE_KEY) throw new DOMException('full', 'QuotaExceededError'); return был.call(this, к, в); };
              const код = await сохранитьНовыйПресет('Проба полная память', 'Проба полная память', collectState());
              Storage.prototype.setItem = был;
              const с = window.__журнал.find(з => з.тип === 'preset_saved');
              return { код, активный: _активныйПресетКод(), журнал: с ? JSON.stringify(с.дет) : '' }; }""")
            if not р["код"] or not re.fullmatch(r"\d{6}", str(р["код"])):
                плохо(f"полная память: код не выдан ({р['код']!r})")
            if р["активный"] != р["код"]:
                плохо(f"полная память: у открытого пресета код {р['активный']!r}, выдан {р['код']!r}")
            if f'"presetCode":"{р["код"]}"' not in р["журнал"]:
                плохо(f"полная память: код не дошёл до журнала: {р['журнал'][:160]}")
            print(f"  полная память: код {р['код']}, в журнале — да")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()

            # 2. Печать несохранённого расчёта, затем сохранённого.
            стр, ошибки = страница(бр, порт)
            р = стр.evaluate("""() => { const до = Object.keys(loadAllPresets()).length;
              openPrintPreview(); setPrintStyle('blank', true); printFromPreview();
              const после = Object.keys(loadAllPresets()).length, код = _активныйПресетКод();
              printFromPreview();
              return { до, после, после2: Object.keys(loadAllPresets()).length, код,
                       листы: window.__листы.map(л => л.html) }; }""")
            if р["после"] != р["до"] + 1:
                плохо(f"печать несохранённого не завела пресет: было {р['до']}, стало {р['после']}")
            if р["после2"] != р["после"]:
                плохо("повторная печать завела ещё один пресет")
            ждём = f"код {str(р['код'])[:3]} {str(р['код'])[3:]}"
            for i, л in enumerate(р["листы"]):
                if ждём not in л:
                    плохо(f"лист {i + 1}: нет «{ждём}»")
            print(f"  печать: пресетов {р['до']} → {р['после']} → {р['после2']}, на листах «{ждём}»")
            # Штамп на отрисованном листе: угол, мелкость.
            if р["листы"]:
                л = бр.new_page(viewport={"width": 900, "height": 1200})
                л.set_content(р["листы"][0]); л.wait_for_timeout(300)
                ш = л.evaluate("""() => { const e = document.querySelector('.spec-code-stamp'); if (!e) return null;
                  const r = e.getBoundingClientRect(), fs = parseFloat(getComputedStyle(e).fontSize);
                  const мин = Math.min(...[...document.querySelectorAll('body *')].filter(x => x !== e && x.childNodes.length && [...x.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
                    .map(x => parseFloat(getComputedStyle(x).fontSize)));
                  return { справа: innerWidth - r.right, снизу: innerHeight - r.bottom, fs, мин, fixed: getComputedStyle(e).position }; }""")
                if not ш:
                    плохо("на отрисованном листе штампа нет")
                else:
                    if ш["fixed"] != "fixed" or not (0 <= ш["справа"] <= 30 and 0 <= ш["снизу"] <= 20):
                        плохо(f"штамп не в правом нижнем углу: {ш}")
                    if not ш["fs"] < ш["мин"] or ш["fs"] > 5:
                        плохо(f"штамп не мельче текста листа: {ш['fs']} px при самом мелком {ш['мин']} px")
                    print(f"  штамп: {ш['fs']:.2f} px (самый мелкий текст листа {ш['мин']:.2f}), от края {ш['справа']:.0f}/{ш['снизу']:.0f} px")
                л.close()
            if any("spec-code-stamp-view" in л for л in р["листы"]):
                плохо("в окно печати ушёл и штамп предпросмотра — код стоит дважды")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()

            # 3. Лист предпросмотра: код в правом нижнем углу во всех стилях,
            #    на телефоне и на широком экране; открытие несохранённого
            #    расчёта код уже даёт.
            for ширина in (390, 1440):
                стр, ошибки = страница(бр, порт)
                стр.set_viewport_size({"width": ширина, "height": 900})
                стр.wait_for_timeout(200)
                р = стр.evaluate("""async () => {
                  const до = Object.keys(loadAllPresets()).length;
                  openPrintPreview();
                  await new Promise(r => setTimeout(r, 120));
                  const код = _активныйПресетКод(), после = Object.keys(loadAllPresets()).length;
                  const итог = {};
                  for (const стиль of ['blank', 'modern', 'classic', 'architect', 'cards', 'luxury']) {
                    setPrintStyle(стиль, true);
                    await new Promise(r => setTimeout(r, 120));
                    const лист = document.getElementById('printDoc');
                    const ш = лист.querySelectorAll('.spec-code-stamp-view');
                    if (ш.length !== 1) { итог[стиль] = { сколько: ш.length }; continue; }
                    const r = ш[0].getBoundingClientRect(), л = лист.getBoundingClientRect();
                    // Что стоит на листе ниже штампа или заходит на него.
                    const наложение = [...лист.querySelectorAll('*')].filter(x => x !== ш[0] && !x.contains(ш[0])
                      && [...x.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).some(x => {
                        const q = x.getBoundingClientRect();
                        return q.width && q.height && q.left < r.right && q.right > r.left && q.top < r.bottom && q.bottom > r.top; });
                    итог[стиль] = { сколько: 1, текст: ш[0].textContent, справа: л.right - r.right, снизу: л.bottom - r.bottom,
                      fs: parseFloat(getComputedStyle(ш[0]).fontSize), видим: getComputedStyle(ш[0]).display !== 'none' && r.width > 0,
                      наложение };
                  }
                  return { до, после, код, итог }; }""")
                ждём = f"код {str(р['код'])[:3]} {str(р['код'])[3:]}"
                if not р["код"] or р["после"] != р["до"] + 1:
                    плохо(f"{ширина} px: открытие предпросмотра несохранённого расчёта не дало кода")
                for стиль, и in р["итог"].items():
                    где = f"{ширина} px, стиль {стиль}"
                    if и["сколько"] != 1:
                        плохо(f"{где}: штампов на листе {и['сколько']}")
                        continue
                    if и["текст"] != ждём or not и["видим"]:
                        плохо(f"{где}: на листе «{и['текст']}», ждали «{ждём}»")
                    if not (0 <= и["справа"] <= 30 and 0 <= и["снизу"] <= 20):
                        плохо(f"{где}: штамп не в правом нижнем углу листа: {и['справа']:.0f}/{и['снизу']:.0f} px")
                    if и["fs"] > 5:
                        плохо(f"{где}: штамп крупнее 5 px ({и['fs']:.2f})")
                    if и["наложение"]:
                        плохо(f"{где}: штамп наезжает на текст листа")
                print(f"  предпросмотр {ширина} px: «{ждём}» в {sum(1 for и in р['итог'].values() if и['сколько'] == 1)} стилях из 6")
                if ширина == 1440:
                    т = стр.evaluate("""() => { window.__листы.length = 0; printByContracts();
                      return window.__листы.map(л => л.html); }""")
                    if not т or ждём not in т[0]:
                        плохо("печать по договорам без кода")
                    elif т[0].count(ждём) != 1:
                        плохо(f"печать по договорам: код стоит {т[0].count(ждём)} раз")
                    стр.set_viewport_size({"width": 1440, "height": 900})
                    стр.evaluate("() => { setPrintStyle('blank', true); document.getElementById('printDoc').scrollIntoView({block: 'end'}); }")
                    стр.wait_for_timeout(300)
                    стр.screenshot(path=str(ЗДЕСЬ / "снимок-код-предпросмотр-1440.png"))
                if ошибки:
                    плохо(f"{ширина} px: ошибки страницы: " + "; ".join(ошибки)[:200])
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: код выдаётся и при полной памяти браузера и уходит в журнал; печать ставит его мелко "
          "в правый нижний угол, несохранённый расчёт сохраняя пресетом, а сохранённый — не дублируя.")


if __name__ == "__main__":
    главная()
