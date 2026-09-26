#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно «Пресеты», вкладка «Общие»: замок на карточке и честный отзыв.

Константин 26.09.2026: «сюда сделай кнопку замка на общие пресеты. Если мой —
могу открыть/закрыть по этой кнопке. Если чужой — кнопка не активна для меня,
но показывает состояние замка… И возле названия пресета (слева) убери замок…
Когда закрыт замок, также выделяй цветом цветовой схемы». И второе: «мой пресет
не отзывается — сначала показывает ок. Потом опять нужно отзывать».

Проба держит на 390 и 1440, в «Бланке» и «Модерне», днём и ночью:
  • у каждой карточки кнопка замка стоит сразу за скачиванием, до «Отозвать»;
  • свой — нажимается и переключает замок через функцию базы, чужой —
    выключен, но закрытый показан закрытым;
  • закрытый выделен: цвет рамки или фона отличается от открытого;
  • перед названием значка замка нет;
  • поле нажатия своей кнопки не меньше 32 px, до соседей не меньше 4 px;
  • отзыв идёт через функцию `retract_preset`; ответ «не снято» возвращает
    пресет в общие и говорит об ошибке, а не «убрано».

    python3 check_shared_lock_btn.py
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
  window.__RPC = window.__RPC || {};
  const вызовы = [];
  window.__RPC.set_preset_lock = а => { вызовы.push(['lock', а.p_code, а.p_locked]); return true; };
  let ответОтзыва = false;
  window.__RPC.retract_preset = а => { вызовы.push(['retract', а.p_code]); return ответОтзыва; };
  const тосты = []; const былТост = window.showToast; window.showToast = т => { тосты.push(String(т)); };
  const я = _sbUser && _sbUser.id;
  const с = (код, имя, свой, замок) => ({ short_code: код, name: имя, author_name: свой ? 'Проба' : 'Максим Григорьев',
    author_id: свой ? я : 'u-другой', is_public: true, visibility: 'public', locked: замок,
    created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 8017902, tech: 'frame' } });
  openPresetPanel();
  setSharedFilter('all');
  _sharedPresets.length = 0;
  _sharedPresets.push(с('111111', 'Свой под замком', true, true), с('222222', 'Свой открытый', true, false),
                      с('333333', 'Чужой под замком', false, true), с('444444', 'Чужой открытый', false, false));
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  renderSharedList(); await ждать(200);
  const карта = () => Object.fromEntries([...document.querySelectorAll('#sharedPresetList .shared-pcard')].map(к => {
    const кн = к.querySelector('.btn-shared-lock');
    const ряд = [...(к.querySelector('.shared-pcard-actions') || {children: []}).children].filter(x => x.offsetWidth);
    const i = ряд.indexOf(кн);
    const пред = ряд[i - 1], след = ряд[i + 1];
    let поле = 0, зазор = 99;
    if (кн) {
      const r = кн.getBoundingClientRect(), x = r.left + r.width / 2;
      for (let y = Math.floor(r.top) - 30; y <= r.bottom + 30; y++) if (кн.contains(document.elementFromPoint(x, y))) поле++;
      if (пред) зазор = Math.min(зазор, r.left - пред.getBoundingClientRect().right);
      if (след) зазор = Math.min(зазор, след.getBoundingClientRect().left - r.right);
    }
    const cs = кн ? getComputedStyle(кн) : null;
    return [к.dataset.scode, { есть: !!кн, выкл: кн ? кн.disabled : null, закрыт: кн ? кн.classList.contains('on') : null,
      послеСкачивания: !!(пред && /downloadSharedPreset/.test(пред.getAttribute('onclick') || '')),
      передОтозвать: след ? /Отозвать/.test(след.textContent) : null,
      вид: cs ? cs.borderTopColor + '|' + cs.backgroundColor + '|' + cs.color : '',
      замокУИмени: !!к.querySelector('.shared-pcard-name svg'), поле, зазор: Math.round(зазор) }];
  }));
  const до = карта();
  document.querySelector('.shared-pcard[data-scode="222222"] .btn-shared-lock')?.click(); await ждать(150);
  const чужаяНажата = document.querySelector('.shared-pcard[data-scode="333333"] .btn-shared-lock'); чужаяНажата?.click(); await ждать(100);
  const после = карта();
  ответОтзыва = false;
  await retractPreset('222222'); await ждать(150);
  const неСнят = { вОбщих: !!document.querySelector('.shared-pcard[data-scode="222222"]'), тост: тосты[тосты.length - 1] || '' };
  ответОтзыва = true;
  await retractPreset('222222'); await ждать(150);
  const снят = { вОбщих: !!document.querySelector('.shared-pcard[data-scode="222222"]'), тост: тосты[тосты.length - 1] || '' };
  window.showToast = былТост;
  closePresetPanel();
  return { до, после, вызовы, неСнят, снят };
}"""


def главная():
    с, порт = сервер()
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
                        if ш == 390 and тема == "blank" and not ночь:
                            print("  " + json.dumps(р, ensure_ascii=False)[:1500])
                        до, после = р["до"], р["после"]
                        for код, х in до.items():
                            if not х["есть"]: плохо(н + f" {код}: нет кнопки замка"); continue
                            if not х["послеСкачивания"]: плохо(н + f" {код}: замок не сразу за скачиванием")
                            if х["передОтозвать"] is False and код in ("111111", "222222"): плохо(н + f" {код}: за замком не «Отозвать»")
                            if х["замокУИмени"]: плохо(н + f" {код}: значок замка остался перед названием")
                            if х["зазор"] < 4: плохо(н + f" {код}: замок вплотную к соседу ({х['зазор']} px)")
                        for код, закрыт in (("111111", True), ("222222", False), ("333333", True), ("444444", False)):
                            if до.get(код, {}).get("закрыт") != закрыт: плохо(н + f" {код}: замок показан не в том состоянии")
                        for код, выкл in (("111111", False), ("222222", False), ("333333", True), ("444444", True)):
                            if до.get(код, {}).get("выкл") != выкл: плохо(н + f" {код}: кнопка {'нажимается' if not выкл else 'не нажимается'} вопреки хозяину")
                        if до.get("111111", {}).get("поле", 0) < 32: плохо(н + f": поле нажатия замка {до['111111']['поле']} px")
                        if до.get("111111", {}).get("вид") == до.get("222222", {}).get("вид"): плохо(н + ": закрытый замок не выделен цветом")
                        if до.get("333333", {}).get("вид") == до.get("444444", {}).get("вид"): плохо(н + ": чужой закрытый не отличается от открытого")
                        if ["lock", "222222", True] not in р["вызовы"]: плохо(н + ": свой замок не ушёл в базу")
                        if not после.get("222222", {}).get("закрыт"): плохо(н + ": после нажатия свой замок не закрылся")
                        if any(в[0] == "lock" and в[1] == "333333" for в in р["вызовы"]): плохо(н + ": чужой замок нажался")
                        if ["retract", "222222"] not in р["вызовы"]: плохо(н + ": отзыв идёт мимо функции retract_preset")
                        if not р["неСнят"]["вОбщих"] or "Убрано" in р["неСнят"]["тост"]: плохо(н + f": база отказала, а отзыв показан успешным ({р['неСнят']})")
                        if р["снят"]["вОбщих"] or "Убрано" not in р["снят"]["тост"]: плохо(н + f": успешный отзыв не убрал пресет ({р['снят']})")
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
    print("Чисто: на «Общих» замок стоит за скачиванием, свой переключается, чужой выключен и показывает состояние, "
          "закрытый выделен, у названия замка нет; отзыв идёт через функцию базы, отказ базы не выдаётся за успех — "
          "на 390 и 1440, в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
