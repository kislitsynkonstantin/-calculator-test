#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полоска открытого общего пресета: кнопка замка у автора на телефоне.

Константин 26.09.2026: «кнопку замка сделай побольше на публичном пресете у
автора пресета. Можно на высоту плашки, по центру. Так как там всегда 2
строки. Так и удобнее пальцем будет нажимать, если с телефона».

Проба держит на 390 (две строки) и 1440 (одна строка), в «Бланке» и
«Модерне», днём и ночью:
  • на 390 замок справа по центру высоты двух строк (зазоры сверху и снизу
    равны ±2 px), коробка лёгкая — 24–32 px в высоту и 30–40 в ширину
    (Константин, 26.09.2026: «окантовка слишком здоровая. Сам замок размер
    нормальный»), значок не меньше 15 px;
  • поле нажатия по вертикали не меньше 44 px — во всю высоту полоски;
  • у открытого замка дужка поднята: над корпусом она выше, чем у закрытого,
    не меньше чем на 2 единицы рисунка, и конец правой ноги отстоит от
    корпуса — и в полоске, и на карточке «Общих»
    («открытие сделай замка душку выше, чтобы видно было»);
  • имя и состояние не заходят на кнопку, до звезды не меньше 6 px;
  • кнопка внутри полоски, полоска внутри окна;
  • на 1440 кнопка с подписью остаётся в одной строке с именем.

    python3 check_strip_lock_btn.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];")
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


СЦЕНАРИЙ = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const я = _sbUser && _sbUser.id;
  _sharedPresets.length = 0;
  _sharedPresets.push({ short_code: '235788', name: 'D1_Хай-тек баня «Виго» 7,7x8,2 · 24.09.26', author_name: 'Проба',
    author_id: я, is_public: true, visibility: 'public', locked: true,
    created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 4600000, tech: 'frame' } });
  _activeSharedCode = '235788';
  updateSharedModeIndicator(); await ждать(250);
  const п = document.getElementById('sharedModeIndicator'), к = document.getElementById('presetLockBtn');
  if (!п || !к) return { нет: true };
  const P = п.getBoundingClientRect(), K = к.getBoundingClientRect();
  const З = п.querySelector('.si-star').getBoundingClientRect();
  const И = п.querySelector('.si-name').getBoundingClientRect(), С = п.querySelector('.si-status').getBoundingClientRect();
  let поле = 0; const x = K.left + K.width / 2;
  for (let y = Math.floor(K.top) - 30; y <= K.bottom + 30; y++) if (к.contains(document.elementFromPoint(x, y))) поле++;
  const cs = getComputedStyle(п);
  const внутр = { верх: P.top + parseFloat(cs.borderTopWidth), низ: P.bottom - parseFloat(cs.borderBottomWidth) };
  const r = v => Math.round(v * 10) / 10;
  return { полоска: [r(P.left), r(P.top), r(P.width), r(P.height)], кнопка: [r(K.left), r(K.top), r(K.width), r(K.height)],
    сверху: r(K.top - внутр.верх), снизу: r(внутр.низ - K.bottom), поле,
    доЗвезды: r(K.left - З.right), имяЗаходит: r(И.right - K.left), статусЗаходит: r(С.right - K.left),
    вОкне: P.left >= 0 && P.right <= innerWidth, внутри: K.left >= P.left && K.right <= P.right && K.top >= P.top && K.bottom <= P.bottom,
    подписьВидна: (() => { const л = к.querySelector('.si-lock-label'); return !!л && л.getBoundingClientRect().width > 2; })(),
    одинРяд: Math.abs((И.top + И.bottom) / 2 - (K.top + K.bottom) / 2) < 6,
    значок: r(к.querySelector('svg').getBoundingClientRect().width),
    дужка: await (async () => {
      // Подъём дужки — насколько высота дужки над корпусом у открытого больше,
      // чем у закрытого. Зазор у конца правой ноги был и прежде, а дужка
      // стояла на той же высоте, что у закрытого, и замок читался закрытым.
      const высота = svg => { const p = svg.querySelector('path'), rc = svg.querySelector('rect'); return rc.y.baseVal.value - p.getBBox().y; };
      const закрытый = document.querySelector('#presetLockBtn svg');
      const hЗакр = закрытый ? высота(закрытый) : 0;
      const зазор = svg => { if (!svg) return -99; const p = svg.querySelector('path'), rc = svg.querySelector('rect');
        const e = p.getPointAtLength(p.getTotalLength()); return Math.min(r(rc.y.baseVal.value - e.y), r(высота(svg) - hЗакр)); };
      _sharedPresets[0].locked = false; updateSharedModeIndicator(); await ждать(150);
      const вПолоске = зазор(document.querySelector('#presetLockBtn svg'));
      const д = document.createElement('div'); д.innerHTML = typeof ЗАМОК_ОТКРЫТ_SVG === 'string' ? ЗАМОК_ОТКРЫТ_SVG : '';
      document.body.appendChild(д); const наКарточке = зазор(д.querySelector('svg')); д.remove();
      _sharedPresets[0].locked = true; updateSharedModeIndicator();
      return { вПолоске, наКарточке };
    })() };
}"""


def главная():
    с, порт = сервер()
    снимки = pathlib.Path(os.environ.get("BM_SHOTS", "")) if os.environ.get("BM_SHOTS") else None
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тема in ("blank", "light"):
                    for ночь in (False, True):
                        стр = бр.new_page(viewport={"width": ш, "height": 900})
                        ошибки = []
                        стр.on("pageerror", lambda e: ошибки.append(str(e)))
                        стр.add_init_script(ЗАГЛУШКА)
                        стр.add_init_script(ТАБЛИЦЫ_JS)
                        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                        стр.wait_for_timeout(2500)
                        стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                        стр.evaluate(f"() => {{ applyUiStyle('{тема}', false); document.body.classList.toggle('dark', {str(ночь).lower()}); }}")
                        р = стр.evaluate(СЦЕНАРИЙ)
                        н = f"{ш} {тема} {'ночь' if ночь else 'день'}"
                        if ш == 390 and тема == "blank" and not ночь or ш == 1440 and тема == "blank" and not ночь:
                            print("  " + н + ": " + json.dumps(р, ensure_ascii=False))
                        if снимки and not ночь:
                            стр.screenshot(path=str(снимки / f"{ш}-{тема}.png"))
                        if р.get("нет"): плохо(н + ": у автора нет кнопки замка"); стр.close(); continue
                        if not р["вОкне"]: плохо(н + ": полоска выходит за окно")
                        if not р["внутри"]: плохо(н + ": кнопка замка выходит за полоску")
                        if р["поле"] < (44 if ш == 390 else 32): плохо(н + f": поле нажатия замка {р['поле']} px")
                        if р["доЗвезды"] < 6: плохо(н + f": замок вплотную к звезде ({р['доЗвезды']} px)")
                        if р["имяЗаходит"] > -4: плохо(н + f": имя заходит на кнопку ({р['имяЗаходит']})")
                        if р["статусЗаходит"] > -4: плохо(н + f": состояние заходит на кнопку ({р['статусЗаходит']})")
                        if ш == 390:
                            if abs(р["сверху"] - р["снизу"]) > 2: плохо(н + f": замок не по центру высоты ({р['сверху']} / {р['снизу']})")
                            ш_, в_ = р["кнопка"][2], р["кнопка"][3]
                            if not (24 <= в_ <= 32 and 30 <= ш_ <= 40): плохо(н + f": коробка замка {ш_}×{в_}, нужна лёгкая 30–40 × 24–32")
                            if р["значок"] < 15: плохо(н + f": значок замка {р['значок']} px")
                        else:
                            if not р["подписьВидна"]: плохо(н + ": на широком экране пропала подпись замка")
                            if not р["одинРяд"]: плохо(н + ": на широком экране замок ушёл со строки имени")
                        for где, з in р["дужка"].items():
                            if з < 2: плохо(н + f": у открытого замка ({где}) дужка не поднята над закрытой ({з})")
                        for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                            плохо(f"{н}: ошибка страницы: {о[:160]}")
                        стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: на телефоне замок автора справа по центру полоски в лёгкой коробке, нажимается во всю её высоту, дужка открытого поднята, "
          "имя, состояние и звезда его не касаются; на широком экране кнопка с подписью в строке имени — "
          "в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
