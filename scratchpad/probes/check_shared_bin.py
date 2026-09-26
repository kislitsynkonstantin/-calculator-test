#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Корзина на карточке общего пресета — только у администратора.

Константин 26.09.2026: «кнопка удалить была активна только для своего пресета
и администратору для всех пресетов. Менеджеры чужие пресеты (даже с открытым
замком) не могут удалять. Только свои могут — защита от дурака».

Проба держит на 390 и 1440 для трёх ролей — администратор, редактор, менеджер:
  • корзина на чужой карточке есть только у администратора, и на открытом, и
    на запертом пресете;
  • на своей карточке корзины нет ни у кого, стоит «Отозвать»;
  • корзина снимает пресет через функцию базы `admin_unpublish_preset`, а не
    прямой записью: прямую запись правило доступа отвергает, и прежняя корзина
    не срабатывала ни на одном чужом пресете;
  • ответ функции «не снято» оставляет пресет в общих и говорит об этом.

Серверную половину — страж `preset_links_guard` — проба видеть не может:
заглушка базы правил доступа не знает. Она проверена на живой базе блоком с
откатом (CHANGELOG, v2.5.12 (29)).

    python3 check_shared_bin.py
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



СЦЕНАРИЙ = """async (роль) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  window._sbProfile = Object.assign({}, window._sbProfile || {}, { role: роль });
  try { _sbProfile = window._sbProfile; } catch (e) {}
  window.__RPC = window.__RPC || {};
  const вызовы = []; let ответ = false;
  window.__RPC.admin_unpublish_preset = а => { вызовы.push(а.p_code); return ответ; };
  const прямые = [];
  const былFrom = _sb.from.bind(_sb);
  _sb.from = т => { const з = былFrom(т); if (т === 'preset_links') { const u = з.update; з.update = (...а) => { прямые.push(а[0]); return u.apply(з, а); }; } return з; };
  window.confirm = () => true;
  const тосты = []; const былТост = window.showToast; window.showToast = т => { тосты.push(String(т)); };
  const я = _sbUser && _sbUser.id;
  const с = (код, свой, замок) => ({ short_code: код, id: код, name: 'Пресет ' + код, author_name: свой ? 'Проба' : 'Максим Григорьев',
    author_id: свой ? я : 'u-другой', is_public: true, visibility: 'public', locked: замок,
    created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 8017902, tech: 'frame' } });
  openPresetPanel();
  _sharedPresets.length = 0;
  _sharedPresets.push(с('111111', true, false), с('222222', false, false), с('333333', false, true));
  try { _общиеЗагружены = true; } catch (e) {}
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  setSharedFilter('all'); await ждать(200);
  const корзина = код => document.querySelector('.shared-pcard[data-scode="' + код + '"] [onclick^="adminRemoveShared"]');
  const видно = код => { const к = корзина(код); return !!(к && к.offsetWidth); };
  const карта = { свой: видно('111111'), чужойОткрытый: видно('222222'), чужойЗапертый: видно('333333'),
    отозватьУСвоего: !!document.querySelector('.shared-pcard[data-scode="111111"] .btn-retract') };
  let отказ = null, снят = null;
  if (роль === 'admin') {
    ответ = false; корзина('333333')?.click(); await ждать(200);
    отказ = { вОбщих: !!document.querySelector('.shared-pcard[data-scode="333333"]'), тост: тосты[тосты.length - 1] || '' };
    ответ = true; корзина('333333')?.click(); await ждать(200);
    снят = { вОбщих: !!document.querySelector('.shared-pcard[data-scode="333333"]'), тост: тосты[тосты.length - 1] || '' };
  }
  window.showToast = былТост; _sb.from = былFrom;
  closePresetPanel();
  return { карта, вызовы, прямые: прямые.length, отказ, снят };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for роль in ("admin", "editor", "manager"):
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; applyUiStyle('blank', false); }")
                    р = стр.evaluate(СЦЕНАРИЙ, роль)
                    н = f"{ш} {роль}"
                    if ш == 390:
                        print("  " + н + ": " + json.dumps(р, ensure_ascii=False)[:600])
                    к = р["карта"]
                    админ = роль == "admin"
                    if к["свой"]: плохо(н + ": на своей карточке стоит корзина")
                    if not к["отозватьУСвоего"]: плохо(н + ": на своей карточке нет «Отозвать»")
                    for имя in ("чужойОткрытый", "чужойЗапертый"):
                        if к[имя] != админ:
                            плохо(н + f": {имя} — корзина {'есть' if к[имя] else 'нет'}, а должна {'быть' if админ else 'отсутствовать'}")
                    if админ:
                        if р["прямые"]: плохо(н + ": корзина пишет в строку напрямую, а не через функцию базы")
                        if р["вызовы"] != ["333333", "333333"]: плохо(н + f": функция admin_unpublish_preset вызвана не так ({р['вызовы']})")
                        о, сн = р["отказ"] or {}, р["снят"] or {}
                        if not о.get("вОбщих") or "Снято" in о.get("тост", ""): плохо(н + f": отказ базы выдан за успех ({о})")
                        if сн.get("вОбщих") or "Снято" not in сн.get("тост", ""): плохо(н + f": запертый чужой пресет не снят ({сн})")
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
    print("Чисто: корзина на чужой карточке — только у администратора, на открытом и запертом пресете; на своей — "
          "«Отозвать» и корзины нет; снятие идёт через функцию базы, отказ не выдаётся за успех — на 390 и 1440.")


if __name__ == "__main__":
    главная()
