#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Макет «Убрать из „По коду“»: настоящее окно «Пресеты» и варианты кнопки.

Константин 27.09.2026 о кнопке-кружке с крестиком последней в ряду действий:
«Так не пойдёт, покажи отдельным макетом, варианты тут».

Окно снимается с живой страницы (заглушка базы, выдуманные имена и суммы), в
каждую карточку вкладки «По коду» дописывается разметка всех вариантов, а
показывает её класс `v0…v3` на body. Стили страницы, шрифты и окно
кладутся в один документ, который макет подставляет в две рамки — телефон
390 и компьютер 1280 (уменьшенный под ширину экрана).

    python3 build.py ../../mockups/code-drop-v1.html [шрифты.css]
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
КОРЕНЬ = ЗДЕСЬ.parent.parent
ПРОБЫ = КОРЕНЬ / "scratchpad" / "probes"
ЗАГЛУШКА = (ПРОБЫ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ПРОБЫ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Пётр', last_name: 'Образцов', full_name: 'Пётр Образцов', app_settings: {} }];")


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


ПОДГОТОВКА = r"""async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle('blank', false);
  selectProjectOption(0); await ждать(600);
  const снимок = collectState(); снимок.tech = 'frame';
  const ст = (код, имя, автор, свой, публ, закрыт) => ({ short_code: код, id: код, preset_id: 'p' + код,
    author_id: свой ? _sbUser.id : 'u-другой', author_name: автор, name: имя, state: снимок,
    is_public: публ, visibility: 'public', locked: закрыт, created_at: '2026-09-25T09:00:00Z', updated_at: '2026-09-26T18:41:00Z' });
  const строки = {
    '482915': ст('482915', 'Баня 6×4 с террасой · вариант для заказчика', 'Пётр Образцов', true, true, false),
    '365484': ст('365484', 'Дом 8×8 · черновой расчёт', 'Ольга Примерова', false, false, false),
    '731260': ст('731260', 'Баня 5×6 · Тёплый контур', 'Ольга Примерова', false, true, true) };
  window.__RPC = window.__RPC || {};
  window.__RPC.get_preset_by_code = а => строки[а.code] ? [строки[а.code]] : [];
  _sharedPresets.length = 0;
  ['482915', '731260'].forEach(к => _sharedPresets.push(Object.assign({}, строки[к])));
  window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(х => Object.assign({}, х));
  try { _общиеЗагружены = true; } catch (e) {}
  appSettings.sharedStars = ['731260']; _sharedStars = new Set(['731260']);
  appSettings.codeFound = ['731260', '482915', '365484'];
  openPresetPanel(); await ждать(300);
  switchPresetTab('code'); await ждать(1200);
  // Разметка всех вариантов — в каждую карточку.
  const крест = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  const крестМал = крест.replace(/13/g, '11');
  document.querySelectorAll('#codePresetList .shared-pcard').forEach(к => {
    const у = к.querySelector('.pcode-drop'); if (у) у.classList.add('mk-v0');
    к.insertAdjacentHTML('beforeend', `<button type="button" class="mk-x mk-v1" aria-label="Убрать из списка">${крест}</button>`);
    const ряд = к.querySelector('.pcard-code-row');
    if (ряд) ряд.insertAdjacentHTML('beforeend', `<div class="pcard-code-sep mk-v2"></div><button type="button" class="btn-copy-link mk-link mk-v2" aria-label="Убрать из списка">${крестМал}<span>Убрать</span></button>`);
    const д = к.querySelector('.shared-pcard-actions');
    if (д) д.insertAdjacentHTML('beforeend', `<button type="button" class="mk-word mk-v3">Убрать</button>`);
  });
  return true;
}"""

СОБРАТЬ = r"""() => {
  const стили = [...document.querySelectorAll('style')].map(с => с.textContent).join('\n');
  const п = document.getElementById('presetPanel').cloneNode(true);
  п.querySelectorAll('script').forEach(e => e.remove());
  п.querySelectorAll('*').forEach(e => { [...e.attributes].forEach(а => { if (/^on/i.test(а.name)) e.removeAttribute(а.name); }); });
  return { стили, окно: п.outerHTML, тон: document.documentElement.getAttribute('data-tone') || '' };
}"""

ВАРИАНТЫ_CSS = r"""
body:not(.v0) .mk-v0, body:not(.v1) .mk-v1, body:not(.v2) .mk-v2, body:not(.v3) .mk-v3 { display: none !important; }
/* 1 — крестик в углу карточки: без коробки, поле нажатия шире значка. */
#presetPanel .shared-pcard { position: relative; }
.mk-x { position: absolute; top: 9px; right: 8px; width: 24px; height: 24px; padding: 0; border: none; background: none;
  display: inline-flex; align-items: center; justify-content: center; color: var(--gray-light); border-radius: 6px; cursor: pointer; }
.mk-x::before { content: ''; position: absolute; inset: -10px; }
body.ui-blank .mk-x { color: var(--bl-ink3); top: 10px; right: 8px; }
body.v1 #codePresetList .shared-pcard-top { padding-right: 28px; }
body.v1.ui-blank #presetPanel #codePresetList .shared-pcard-top { padding-right: 44px !important; }
@media (min-width: 900px) {
  body.v1.ui-blank #presetPanel #codePresetList .shared-pcard .shared-pcard-top { padding-right: 132px !important; }
  body.v1.ui-blank #presetPanel #codePresetList .shared-pcard .shared-pcard-sum .tech-chip { right: 42px; }
  body.v1.ui-blank #presetPanel #codePresetList .shared-pcard-sum { padding-right: 26px; }
}
/* 2 — «Убрать» словом в полосе кода, рядом со «Скопировать», тише его. */
.mk-link { color: var(--gray-light) !important; }
body.ui-blank .mk-link { color: var(--bl-ink3) !important; position: relative; }
/* На телефоне слово в полосу кода не входит: остаётся крестик у её правого края. */
@media (max-width: 480px) {
  .mk-link.mk-v2 { margin-left: auto; border-color: transparent !important; background: none !important; padding: 3px 4px; position: relative; }
  .mk-link.mk-v2::before { content: ''; position: absolute; inset: -10px -8px; }
  .mk-link.mk-v2 span, .pcard-code-sep.mk-v2 { display: none !important; }
}
/* 3 — «Убрать» словом в конце ряда действий, без коробки. */
.mk-word { position: relative; align-self: center; border: none; background: none; padding: 0 4px; margin-left: 2px;
  font: 600 .7rem 'Geologica', sans-serif; color: var(--gray-light); cursor: pointer; white-space: nowrap; }
.mk-word::before { content: ''; position: absolute; inset: -12px -6px; }
body.ui-blank .mk-word { color: var(--bl-ink3); }
@media (hover: hover) {
  .mk-x:hover, .mk-word:hover, .mk-link:hover { color: var(--green-dark) !important; }
  body.ui-blank .mk-x:hover, body.ui-blank .mk-word:hover, body.ui-blank .mk-link:hover { color: var(--bl-acc2) !important; }
}
html, body { background: transparent; }
"""


def главная(выход, шрифты_путь):
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1280, "height": 900})
            стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
            стр.evaluate(ПОДГОТОВКА)
            д = стр.evaluate(СОБРАТЬ)
            бр.close()
    finally:
        с.shutdown()
    шрифты = pathlib.Path(шрифты_путь).read_text(encoding="utf-8")
    документ = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                f'<style>{шрифты}</style><style>{д["стили"]}</style><style>{ВАРИАНТЫ_CSS}</style></head>'
                f'<body class="ui-blank v1">{д["окно"]}</body></html>')
    оболочка = (ЗДЕСЬ / "shell.html").read_text(encoding="utf-8")
    # Документ окна едет строкой JSON: в srcdoc его подставляет скрипт макета.
    вставка = json.dumps(документ, ensure_ascii=False).replace("</", "<\\/")
    html = оболочка.replace("/*@@ДОКУМЕНТ@@*/null", вставка)
    pathlib.Path(выход).write_text(html, encoding="utf-8")
    print(выход, len(html.encode()) // 1024, "KB")


if __name__ == "__main__":
    главная(sys.argv[1], sys.argv[2])
