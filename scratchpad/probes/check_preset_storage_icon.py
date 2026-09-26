#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Значок места хранения пресета и точка у «Активного».

Константин 26.09.2026: «внизу справа пресета давай добавим меленькую иконку,
которая будет показывать, где сохранён — в базе или на компьютере»; глобус —
«по размеру как компьютер»; следом глобус снят (рядом «Публ.», и он читался
как «опубликован») — выбрано облако с галочкой. Значок виден всем: «я когда вижу пресет на
компьютере у менеджера, должен понимать, где он хранится».
Про «Активный»: «поставь серую точку, как возле активного пресета и на
кнопке пресетов. Сейчас кнопка солнца вообще не к месту».

Проба держит:
  • в правом нижнем углу каждой своей карточки значок — и у менеджера, и у
    администратора: облако с галочкой — пресет в базе, экран — ждёт связи в очереди;
  • связь вернулась, очередь ушла — экран сам сменяется облаком;
  • нажатие показывает подсказку словами, второе — прячет;
  • на 390 / 768 / 1440, в «Бланке» и «Модерне», днём и ночью значок не
    за краем, не прилип ни к краю карточки, ни к соседней кнопке и не висит
    в пустоте; облако не меньше экрана;
  • у «Активного» серая точка 6 px вместо значка солнца, по центру строки.

    python3 check_preset_storage_icon.py
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
НЕТ_СВЯЗИ = ("(function () { const с = window.supabase.createClient;"
    " window.supabase.createClient = function () { const к = с.apply(this, arguments); const f = к.from.bind(к);"
    " к.from = function (т) { const о = f(т); if (т === 'presets') { const u = о.upsert;"
    " о.upsert = function (в, н) { if (window.__нетСвязи) return { then: r => r({ error: { message: 'Failed to fetch' } }) };"
    " return u.call(о, в, н); }; } return о; }; return к; }; })();")
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


РАЗЛОЖИТЬ = """async (роль) => {
  _sbProfile = Object.assign({}, _sbProfile || {}, { role: роль });
  window.__нетСвязи = true;
  const п = (ид, имя, код, сумма) => ({ id: ид, name: имя, savedAt: '2026-09-25T18:03:00Z', shortCode: код,
    state: { project: { name: имя }, thickness: 1, totalNum: сумма, tech: 'frame', savedAt: '2026-09-25T18:03:00Z' } });
  window._пресеты = { p_base: п('p_base', 'Хай-тек баня «Виго» 7,7х8,2', '321910', 7044020),
                      p_loc: п('p_loc', 'Фахверковая баня «Милан» 8х8', '452137', 9048682) };
  _вОчередь(window._пресеты.p_loc);
  openPresetPanel(); renderPresetList();
  await new Promise(r => setTimeout(r, 200));
}"""

МЕРА = """() => [...document.querySelectorAll('#presetPanel .pcard')].map(card => {
  const b = card.querySelector('.pst');
  if (!b) return { ид: card.dataset.pid, нет: true };
  const r = b.querySelector('svg').getBoundingClientRect(), c = card.getBoundingClientRect(), W = document.documentElement.clientWidth;
  const г = b.querySelector('svg').getBBox();
  let сосед = 1e9, кто = '';
  card.querySelectorAll('button, .pcard-code-value, .pcard-code-label').forEach(x => {
    if (x === b || b.contains(x)) return; const q = x.getBoundingClientRect();
    if (!q.width || q.bottom <= r.top || q.top >= r.bottom) return;
    const dx = q.right <= r.left ? r.left - q.right : (q.left >= r.right ? q.left - r.right : 0);
    if (dx < сосед) { сосед = dx; кто = (x.textContent || x.className).trim().slice(0, 14); }
  });
  return { ид: card.dataset.pid, лок: b.classList.contains('loc'), знак: г.width * г.height,
           облако: !!b.querySelector('svg path[d^="M17.5 19"]') && !b.querySelector('svg circle'),
           доКрая: Math.round(c.right - r.right), доНиза: Math.round(c.bottom - r.bottom), сосед: Math.round(сосед), кто,
           вне: r.right > W || r.left < 0 };
})"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 768, 1440):
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.add_init_script(НЕТ_СВЯЗИ)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
                  const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none'; }""")
                for тема in ("blank", "light"):
                    for ночь in (False, True):
                        стр.evaluate(f"() => {{ applyUiStyle('{тема}', false); document.body.classList.toggle('dark', {str(ночь).lower()}); }}")
                        стр.evaluate(РАЗЛОЖИТЬ, "manager")
                        метка = f"{ш} {тема} {'ночь' if ночь else 'день'}"
                        м = {x["ид"]: x for x in стр.evaluate(МЕРА)}
                        if м["p_base"].get("нет") or м["p_loc"].get("нет"):
                            плохо(метка + ": у менеджера нет значка")
                            continue
                        if not м["p_base"]["облако"]:
                            плохо(метка + ": у пресета в базе не облако с галочкой")
                        if м["p_base"]["лок"] or not м["p_loc"]["лок"]:
                            плохо(метка + ": значок не отвечает месту хранения")
                        if м["p_base"]["знак"] < м["p_loc"]["знак"] * 0.95:
                            плохо(метка + f": облако мельче экрана ({м['p_base']['знак']:.0f} против {м['p_loc']['знак']:.0f})")
                        for х in м.values():
                            н = f"{метка} {х['ид']}"
                            if х["вне"]: плохо(н + ": значок за краем экрана")
                            if х["доКрая"] < 10: плохо(н + f": прилип к краю карточки ({х['доКрая']})")
                            if х["доНиза"] < 10: плохо(н + f": прилип к низу карточки ({х['доНиза']})")
                            if х["сосед"] < 8: плохо(н + f": вплотную к «{х['кто']}» ({х['сосед']})")
                            if х["сосед"] > 26 and х["доКрая"] > 26: плохо(н + f": висит в пустоте ({х['сосед']} / {х['доКрая']})")
                        if ш == 390 and тема == "blank" and not ночь:
                            print(f"  {метка}: {json.dumps(м, ensure_ascii=False)}")
                # Подсказка по нажатию.
                стр.evaluate("() => applyUiStyle('blank', false)")
                стр.evaluate(РАЗЛОЖИТЬ, "admin")
                п = стр.evaluate("""() => { const b = document.querySelector('.pcard[data-pid="p_loc"] .pst');
                  if (!b) return { два: true, слова: '' };
                  b.click(); const раз = getComputedStyle(b.querySelector('.pst-tip')).opacity;
                  const слова = b.querySelector('.pst-tip').textContent;
                  b.click(); return { раз, слова, два: b.classList.contains('on') }; }""")
                стр.wait_for_timeout(250)
                if п["два"] or "браузере" not in п["слова"]:
                    плохо(f"{ш}: подсказка не открывается и не прячется нажатием: {п}")
                # Связь вернулась — экран сменился облаком.
                р = стр.evaluate("""async () => { window.__нетСвязи = false; await выгрузитьОчередь();
                  await new Promise(r => setTimeout(r, 200));
                  const b = document.querySelector('.pcard[data-pid="p_loc"] .pst'); return b && b.classList.contains('loc'); }""")
                if р:
                    плохо(f"{ш}: очередь ушла в базу, а значок остался экраном")
                # Администратор видит тот же значок.
                стр.evaluate(РАЗЛОЖИТЬ, "admin")
                if стр.evaluate("() => document.querySelectorAll('#presetPanel .pst').length") != 2:
                    плохо(f"{ш}: у администратора нет значка места хранения")
                # «Активный»: точка вместо солнца.
                т = стр.evaluate("""() => { const b = [...document.querySelectorAll('#presetPanel .ptoolbar-btn')].find(x => x.textContent.includes('Активный'));
                  const d = b.querySelector('.ptb-dot'); if (!d) return null;
                  const r = d.getBoundingClientRect(), br = b.getBoundingClientRect();
                  return { svg: !!b.querySelector('svg'), w: r.width, h: r.height, фон: getComputedStyle(d).backgroundColor,
                           центр: Math.abs((r.top + r.bottom) / 2 - (br.top + br.bottom) / 2) }; }""")
                if not т:
                    плохо(f"{ш}: у «Активного» нет серой точки")
                else:
                    if т["svg"]: плохо(f"{ш}: у «Активного» остался значок солнца")
                    if round(т["w"]) != 6 or round(т["h"]) != 6: плохо(f"{ш}: точка «Активного» не 6 px: {т}")
                    if т["фон"] != "rgb(154, 167, 173)": плохо(f"{ш}: точка «Активного» не серая: {т['фон']}")
                    if т["центр"] > 1.5: плохо(f"{ш}: точка «Активного» не по центру строки: {т['центр']:.1f}")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{ш}: ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: у менеджера и администратора в правом нижнем углу карточки облако с галочкой — пресет в базе — или экран — ждёт связи; "
          "очередь ушла — значок сменился сам; на 390/768/1440 в обеих темах днём и ночью "
          "значок у своего места и не прилип; подсказка открывается нажатием; у «Активного» серая точка вместо солнца.")


if __name__ == "__main__":
    главная()
