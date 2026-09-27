#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«По коду»: найденный пресет убирается из списка — по одному.

Константин 27.09.2026: «В разделе „По коду“ нужно иметь возможность очищать
пресеты, так как это по сути результаты поиска. Очистка по одному пресету
должна быть, не все сразу».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • у каждой карточки «По коду» в правом верхнем углу стоит крестик «Убрать
    из списка» — без коробки, поле нажатия не меньше 40 px, у края карточки,
    не наезжает ни на название, ни на метку технологии; на «Общих» его нет
    (вариант 1 макета mockups/code-drop-v1.html, выбран 27.09.2026 — кружок
    в ряду действий Константин снял);
  • нажатие убирает ровно эту карточку: остальные на месте, список в
    настройках аккаунта (`codeFound`) без неё и записан, сообщение словами;
  • кнопки «убрать всё» нет;
  • строка автора не лежит на линейке нижней полосы (на широком «Бланке»
    кружок с инициалами касался её — замечено на снимке этой же пробы);
  • карточка, найденная набранным кодом, убирается вместе с кодом в поле —
    иначе список тут же нашёл бы её снова.

    python3 check_code_drop.py
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
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
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


ПОДГОТОВКА = """async (ui) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle(ui, false);
  selectProjectOption(0); await ждать(700);
  const снимок = collectState(); снимок.tech = 'frame';
  const строки = {
    '365484': { short_code: '365484', preset_id: 'preset_x', author_id: 'u-другой', author_name: 'Проба Другой',
      name: 'Неопубликованный пресет пробы', state: снимок, is_public: false, visibility: 'public',
      created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z', locked: false },
    '111222': { short_code: '111222', preset_id: 'preset_y', author_id: 'u-другой', author_name: 'Проба Другой',
      name: 'Опубликованный пресет пробы', state: снимок, is_public: true, visibility: 'public',
      created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z', locked: false } };
  window.__RPC = window.__RPC || {};
  window.__RPC.get_preset_by_code = а => строки[а.code] ? [строки[а.code]] : [];
  _sharedPresets.length = 0; _sharedPresets.push(Object.assign({ id: '111222' }, строки['111222']));
  window.__ТАБЛИЦЫ.preset_links = [Object.assign({}, строки['111222'])];
  try { _общиеЗагружены = true; } catch (e) {}
  appSettings.sharedStars = []; _sharedStars = new Set(); appSettings.codeFound = ['365484', '111222'];
  window.__записей = 0; const было = window.saveSettings; window.saveSettings = function () { window.__записей++; return было.apply(this, arguments); };
  window.__тосты = []; window.showToast = т => window.__тосты.push(String(т));
  openPresetPanel(); await ждать(300);
  switchPresetTab('code'); await ждать(900);
  return true;
}"""

ОСМОТР = """() => {
  const сп = document.getElementById('codePresetList');
  const карт = [...сп.querySelectorAll('.shared-pcard')];
  return { карточки: карт.map(к => к.dataset.scode),
    кнопки: карт.map(к => { const у = к.querySelector('.pcode-drop'); if (!у || !у.offsetWidth) return null;
      const r = у.getBoundingClientRect(), кр = к.getBoundingClientRect(), cs = getComputedStyle(у), до = getComputedStyle(у, '::before');
      const пересечение = (а, б) => а.left < б.right && б.left < а.right && а.top < б.bottom && б.top < а.bottom;
      const имя = к.querySelector('.shared-pcard-name'), чип = к.querySelector('.tech-chip');
      const ри = имя ? имя.getBoundingClientRect() : null, рч = чип && чип.offsetWidth ? чип.getBoundingClientRect() : null;
      const поле = до.content !== 'none' ? { w: r.width - 2 * parseFloat(до.left), h: r.height - 2 * parseFloat(до.top) } : { w: r.width, h: r.height };
      return { доПрава: Math.round(кр.right - r.right), доВерха: Math.round(r.top - кр.top),
               коробка: parseFloat(cs.borderTopWidth) > 0 || !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor),
               поле: Math.round(Math.min(поле.w, поле.h)), наИмени: !!(ри && пересечение(r, ри)),
               наЧипе: !!(рч && пересечение(r, рч)), доЧипа: рч ? Math.round(Math.min(Math.abs(рч.left - r.right), Math.abs(r.left - рч.right))) : null,
               подпись: у.getAttribute('aria-label') }; }),
    автор: карт.map(к => { const а = к.querySelector('.shared-author-av') || к.querySelector('.shared-author-name');
      if (!а || !а.offsetWidth) return null; const низ = а.getBoundingClientRect().bottom;
      const ниже = [...к.querySelectorAll('.pcard-code-row, .shared-pcard-actions')].map(x => x.getBoundingClientRect().top).filter(t => t >= низ - 6);
      return ниже.length ? Math.round(Math.min(...ниже) - низ) : null; }),
    всё: [...document.querySelectorAll('#ptab-content-code button')].some(к => /убрать вс|очистить (список|вс)/i.test(к.textContent + (к.getAttribute('aria-label') || ''))),
    сохранено: (appSettings.codeFound || []).slice(), записей: window.__записей, тосты: window.__тосты.slice(),
    поле: document.getElementById('codeSearchInput').value };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank", "light"):
                for ш in (390, 1440):
                    н = f"[{ui} {ш}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    стр.evaluate(ПОДГОТОВКА, ui)
                    р = стр.evaluate(ОСМОТР)
                    print("  " + н, json.dumps(р, ensure_ascii=False))
                    if sorted(р["карточки"]) != ["111222", "365484"]:
                        плохо(f"{н} в «По коду» не две карточки: {р['карточки']}"); стр.close(); continue
                    for код, к in zip(р["карточки"], р["кнопки"]):
                        if not к:
                            плохо(f"{н} у карточки {код} нет кнопки «Убрать из списка»"); continue
                        if not (0 <= к["доПрава"] <= 14 and 0 <= к["доВерха"] <= 14):
                            плохо(f"{н} у {код} крестик не в углу: до правого края {к['доПрава']}, до верха {к['доВерха']} px")
                        if к["коробка"]:
                            плохо(f"{н} у {код} у крестика коробка — просили без неё")
                        if к["поле"] < 40:
                            плохо(f"{н} у {код} поле нажатия крестика {к['поле']} px")
                        if к["наИмени"] or к["наЧипе"]:
                            плохо(f"{н} у {код} крестик наезжает на {'название' if к['наИмени'] else 'метку технологии'}")
                        if к["доЧипа"] is not None and к["доЧипа"] < 4 and not к["наЧипе"]:
                            плохо(f"{н} у {код} крестик прижат к метке технологии: {к['доЧипа']} px")
                    for код, з in zip(р["карточки"], р["автор"]):
                        if з is not None and з < 4:
                            плохо(f"{н} у {код} строка автора прижата к нижней полосе: зазор {з} px")
                    if р["всё"]:
                        плохо(f"{н} есть кнопка очистки всего списка — просили по одному")
                    стр.screenshot(path=str(СНИМКИ / f"code-drop-{ui}-{ш}.png"))
                    # на «Общих» кнопки нет
                    общ = стр.evaluate("async () => { switchPresetTab('shared'); await new Promise(r => setTimeout(r, 500));"
                                       " const к = document.querySelector('#sharedPresetList .shared-pcard[data-scode=\"111222\"]');"
                                       " return { есть: !!к, убрать: !!(к && к.querySelector('.pcode-drop')) }; }")
                    if not общ["есть"] or общ["убрать"]:
                        плохо(f"{н} на «Общих»: карточка {общ['есть']}, кнопка убрать {общ['убрать']} — ждали карточку без неё")
                    стр.evaluate("async () => { switchPresetTab('code'); await new Promise(r => setTimeout(r, 500)); }")
                    # убираем одну
                    if not стр.locator('#codePresetList .pcode-drop').count():
                        стр.close(); continue
                    стр.locator('#codePresetList .shared-pcard[data-scode="365484"] .pcode-drop').click()
                    стр.wait_for_timeout(500)
                    п = стр.evaluate(ОСМОТР)
                    if п["карточки"] != ["111222"] or п["сохранено"] != ["111222"]:
                        плохо(f"{н} после «убрать» карточки {п['карточки']}, в аккаунте {п['сохранено']} — ждали одну 111222")
                    if п["записей"] < 1:
                        плохо(f"{н} список аккаунта после «убрать» не записан")
                    if not any("убран" in т for т in п["тосты"]):
                        плохо(f"{н} после «убрать» нет сообщения: {п['тосты']}")
                    # карточка, найденная набранным кодом
                    стр.fill("#codeSearchInput", "111222"); стр.wait_for_timeout(600)
                    стр.locator('#codePresetList .shared-pcard[data-scode="111222"] .pcode-drop').click()
                    стр.wait_for_timeout(600)
                    к = стр.evaluate(ОСМОТР)
                    if к["карточки"] or к["сохранено"] or к["поле"]:
                        плохо(f"{н} убранный из поиска код вернулся: карточки {к['карточки']}, в аккаунте {к['сохранено']}, в поле «{к['поле']}»")
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"{н} ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в «По коду» у каждой карточки в углу крестик «Убрать из списка» без коробки, с полем 40+ px, не на названии и метке; "
          "нажатие убирает ровно её и записывает список аккаунта, найденная набранным кодом уходит вместе с кодом в поле; "
          "на «Общих» кнопки нет — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
