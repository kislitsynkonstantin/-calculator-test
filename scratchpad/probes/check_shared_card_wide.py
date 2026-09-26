#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Общие» на широком экране: метка технологии над суммой, дата за толщиной.

Константин 26.09.2026 снимком вкладки «Общие»: «писал уже про это: дату
перенеси, где слева выделил; технологию (тут каркас) перенеси над суммой по
правому краю» — та же раскладка, что у «Моих» с (30) и (32).

Проба держит в «Бланке»:
  • на 1440 метка технологии в строке названия: середина на первой строке
    имени (±1,5 px), правый край вровень с суммой, до имени не меньше 8 px,
    поле нажатия не ложится на сумму;
  • на 1440 дата стоит сразу за толщиной (4–16 px) на той же строке, а в
    строке автора даты нет;
  • на 390 всё как было: метка рядом с суммой, дата в строке автора, в
    строке проекта её нет;
  • в «Модерне» на 1440 ничего не сдвинулось: дата в строке автора.
Карточки — своя и чужая, одна в избранных (у неё полоса слева).

    python3 check_shared_card_wide.py
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
  const с = (код, свой, имя) => ({ short_code: код, id: код, name: имя, author_name: свой ? 'Проба' : 'Анатолий Шевалдов',
    author_id: свой ? я : 'u-другой', is_public: true, visibility: 'public', locked: false,
    created_at: '2026-09-01T18:57:00Z', updated_at: '2026-09-01T18:57:00Z',
    state: { project: { name: 'Санторини хай-тек' }, thickness: 150, totalNum: 12391389, tech: 'frame' } });
  openPresetPanel();
  _sharedPresets.length = 0;
  _sharedPresets.push(с('257752', false, 'Санторини хай-тек 7 · 19.08.26'), с('321910', true, 'Хай-тек баня «Виго» 7,7х8,2 · 25.09.26'));
  try { _sharedStars.add('321910'); } catch (e) {}
  try { _общиеЗагружены = true; } catch (e) {}
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  setSharedFilter('all'); await ждать(250);
  const виден = el => !!el && getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().width > 0;
  return [...document.querySelectorAll('#sharedPresetList .shared-pcard')].map(к => {
    const м = к.querySelector('.tech-chip'), ц = к.querySelector('.shared-pcard-price'), и = к.querySelector('.shared-pcard-name');
    const пр = к.querySelector('.shared-pcard-project'), дп = к.querySelector('.sp-date'), да = к.querySelector('.shared-author-date');
    const мк = м.getBoundingClientRect(), цк = ц.getBoundingClientRect(), карт = к.getBoundingClientRect();
    const р = document.createRange(); р.selectNodeContents(и); const первая = р.getClientRects()[0];
    const сб = parseFloat(getComputedStyle(м, '::before').bottom) || 0;
    let текстПроекта = null;
    if (пр && пр.firstChild && пр.firstChild.nodeType === 3) { const р2 = document.createRange(); р2.selectNodeContents(пр.firstChild); текстПроекта = р2.getBoundingClientRect(); }
    return { код: к.dataset.scode,
      вСтрокеИмени: первая ? Math.abs((мк.top + мк.bottom) / 2 - (первая.top + первая.bottom) / 2) : null,
      правыеКрая: Math.abs(мк.right - цк.right), доИмени: мк.left - и.getBoundingClientRect().right,
      полеНаСумме: (мк.bottom - сб) - цк.top, рядомССуммой: Math.abs((мк.top + мк.bottom) / 2 - (цк.top + цк.bottom) / 2) < 14,
      датаВПроекте: виден(дп), датаУАвтора: виден(да),
      зазорДаты: (виден(дп) && текстПроекта) ? дп.getBoundingClientRect().left - текстПроекта.right : null,
      датаНаСтроке: (виден(дп) && текстПроекта) ? Math.abs((дп.getBoundingClientRect().top + дп.getBoundingClientRect().bottom) / 2 - (текстПроекта.top + текстПроекта.bottom) / 2) < 4 : null,
      текстДаты: дп ? дп.textContent : null };
  });
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш, тема, ночь in ((1440, "blank", False), (1440, "blank", True), (390, "blank", False), (1440, "light", False)):
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate(f"() => {{ const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; applyUiStyle('{тема}', false); document.body.classList.toggle('dark', {str(ночь).lower()}); }}")
                карточки = стр.evaluate(СЦЕНАРИЙ)
                н = f"[{ш} {тема}{' ночь' if ночь else ''}]"
                print("  " + н, json.dumps(карточки, ensure_ascii=False)[:600])
                if len(карточки) != 2:
                    плохо(н + f" карточек {len(карточки)}, а не две"); стр.close(); continue
                for к in карточки:
                    кн = н + " " + к["код"]
                    if тема == "blank" and ш >= 900:
                        if к["вСтрокеИмени"] is None or к["вСтрокеИмени"] > 1.5:
                            плохо(кн + f" метка не в строке названия ({к['вСтрокеИмени']})")
                        if к["правыеКрая"] > 1:
                            плохо(кн + f" метка не вровень с суммой ({round(к['правыеКрая'], 1)} px)")
                        if к["доИмени"] < 8:
                            плохо(кн + f" имя подходит к метке на {round(к['доИмени'])} px")
                        if к["полеНаСумме"] > 0:
                            плохо(кн + f" поле нажатия метки ложится на сумму ({round(к['полеНаСумме'])} px)")
                        if not к["датаВПроекте"] or not к["датаНаСтроке"] or not (4 <= (к["зазорДаты"] or 0) <= 16):
                            плохо(кн + f" дата не сразу за толщиной ({к})")
                        if к["датаУАвтора"]:
                            плохо(кн + " дата осталась и в строке автора")
                    else:
                        if not к["рядомССуммой"]:
                            плохо(кн + " метка ушла от суммы там, где раскладка не менялась")
                        if к["датаВПроекте"] or not к["датаУАвтора"]:
                            плохо(кн + f" дата сдвинулась там, где раскладка не менялась ({к})")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в «Общих» на широком экране «Бланка» метка технологии стоит в строке названия над суммой, дата — "
          "сразу за толщиной, в строке автора её нет; на телефоне и в «Модерне» раскладка прежняя.")


if __name__ == "__main__":
    главная()
