#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно «Пресеты»: глобус на общих вместо «Для всех», без «Мой» на своих.

Константин 26.09.2026: «может тогда «Для всех» подпись убрать, а поставить
глобус. А в моих будет метка базы (как сейчас), что тоже будет указывать, что
это мой пресет. Тогда структура будет одинаковая».

Проба держит на 390 и 1440, в «Бланке» и «Модерне»:
  • на «Общих» у опубликованного для всех — глобус в строке кода перед «Код»,
    метки «Для всех» нет; у своего общего метка «Мой» остаётся;
  • ветки «только администраторам» больше нет (такую публикацию сняли):
    ни щита, ни метки «Admin only», ни раздела «Только admin»;
  • на «Моих» меток нет вовсе: у опубликованного вместо «Опубл.» и облака —
    глобус в строке кода (Константин, 26.09.2026: «в моих пресетах, когда
    опубликовал, тоже меняй на глобус. А справа сверху «Опубл» убери»);
  • метка «Мой» на «Общих» нажимается и включает фильтр «Мои» этой вкладки,
    а поле нажатия у неё не меньше 32 px по высоте;
  • глобус того же размера, что облако на «Моих», и стоит так же: не у края
    карточки и не вплотную к «Код»; нажатие показывает подсказку.

    python3 check_shared_globe.py
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
  _sbProfile = Object.assign({}, _sbProfile || {}, { role: 'admin' });
  const п = (ид, имя, опубл) => Object.assign({ id: ид, name: имя, savedAt: new Date().toISOString(), shortCode: ид === 'm1' ? '111111' : '222222',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 3000000, tech: 'frame' } }, опубл ? { publishedAs: 'user', sharedId: '222222' } : {});
  window._пресеты = { m1: п('m1', 'Свой пресет', false), m2: п('m2', 'Свой опубликованный', true) };
  openPresetPanel(); switchPresetTab('my'); renderPresetList(); await ждать(200);
  const мои = [...document.querySelectorAll('#presetList .pcard')].map(к => ({ ид: к.dataset.pid,
    метка: (к.querySelector('.pcard-badge') || {}).textContent || '',
    глобус: !!к.querySelector('.pcard-code-row .pst svg circle'),
    облако: (() => { const s = к.querySelector('.pcard-code-row .pst svg'); return s ? s.getBoundingClientRect().width * s.getBoundingClientRect().height : 0; })() }));
  const с = (код, имя, вид, свой) => ({ short_code: код, name: имя, author_name: свой ? 'Проба' : 'Максим Григорьев',
    author_id: свой ? (_sbUser && _sbUser.id) : 'u-другой', is_public: true, visibility: вид,
    created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 8017902, tech: 'frame' } });
  setSharedFilter('all');
  _sharedPresets.length = 0;
  _sharedPresets.push(с('775165', 'Чужой для всех', 'public', false), с('333333', 'Свой для всех', 'public', true), с('444444', 'Только админам', 'admin', false));
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  renderSharedList(); await ждать(200);
  const общие = [...document.querySelectorAll('#sharedPresetList .shared-pcard')].map(к => {
    const b = к.querySelector('.pcard-code-row .pst'), s = b && b.querySelector('svg');
    const r = s ? s.getBoundingClientRect() : null, c = к.getBoundingClientRect(), л = к.querySelector('.pcard-code-label').getBoundingClientRect();
    return { код: к.dataset.scode, метка: (к.querySelector('.shared-pcard-badge') || {}).textContent || '',
      глобус: !!(s && s.querySelector('circle')), щит: !!(s && !s.querySelector('circle') && s.querySelector('path')),
      площадь: r ? r.width * r.height : 0, доКрая: r ? Math.round(r.left - c.left) : -1, доКод: r ? Math.round(л.left - r.right) : -1,
      подсказка: b ? (b.querySelector('.pst-tip') || {}).textContent : '' };
  });
  const мой = document.querySelector('#sharedPresetList .shared-pcard[data-scode="333333"] .badge-pub-mine');
  let поле = 0, фильтр = '', карточек = -1;
  if (мой) {
    const r = мой.getBoundingClientRect(), x = r.left + r.width / 2;
    for (let y = Math.floor(r.top) - 30; y <= r.bottom + 30; y++) if (мой.contains(document.elementFromPoint(x, y))) поле++;
    мой.click(); await ждать(150);
    фильтр = _sharedFilter;
    карточек = [...document.querySelectorAll('#sharedPresetList .shared-pcard')].map(к => к.dataset.scode).join(',');
    setSharedFilter('all');
  }
  closePresetPanel();
  return { мои, общие, мой: { поле, фильтр, карточек } };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                for тема in ("blank", "light"):
                    стр.evaluate(f"() => applyUiStyle('{тема}', false)")
                    р = стр.evaluate(СЦЕНАРИЙ)
                    н = f"{ш} {тема}"
                    if ш == 390 and тема == "blank":
                        print("  " + json.dumps(р, ensure_ascii=False))
                    мои = {x["ид"]: x for x in р["мои"]}
                    if "Мой" in мои.get("m1", {}).get("метка", ""): плохо(н + ": на «Моих» осталась метка «Мой»")
                    if мои.get("m2", {}).get("метка", ""): плохо(н + ": у опубликованного на «Моих» осталась метка «Опубл.»")
                    if not мои.get("m2", {}).get("глобус"): плохо(н + ": у опубликованного на «Моих» нет глобуса")
                    if мои.get("m1", {}).get("глобус"): плохо(н + ": неопубликованный на «Моих» показан глобусом")
                    м = р.get("мой", {})
                    if м.get("фильтр") != "mine": плохо(н + ": нажатие на «Мой» не включило фильтр «Мои»")
                    elif м.get("карточек") != "333333": плохо(н + f": после «Мой» в списке {м.get('карточек')}, а не только свой")
                    if м.get("поле", 0) < 32: плохо(н + f": поле нажатия «Мой» {м.get('поле')} px по высоте, нужно от 32")
                    облако = мои.get("m1", {}).get("облако", 0)
                    общ = {x["код"]: x for x in р["общие"]}
                    for код, х in общ.items():
                        if "Для всех" in х["метка"]: плохо(н + f" {код}: осталась метка «Для всех»")
                        if х["доКрая"] < 10: плохо(н + f" {код}: значок у края карточки ({х['доКрая']})")
                        if х["доКод"] < 8: плохо(н + f" {код}: значок вплотную к «Код» ({х['доКод']})")
                        if not х["подсказка"]: плохо(н + f" {код}: у значка нет подсказки")
                    for код in ("775165", "333333"):
                        if not общ.get(код, {}).get("глобус"): плохо(н + f" {код}: у опубликованного для всех нет глобуса")
                        elif облако and abs(общ[код]["площадь"] - облако) > облако * 0.3: плохо(н + f" {код}: глобус не по размеру облака")
                    if "Мой" not in общ.get("333333", {}).get("метка", ""): плохо(н + ": у своего общего пропала метка «Мой»")
                    if any(х["щит"] or "Admin" in х["метка"] for х in общ.values()):
                        плохо(н + ": осталась ветка «только администраторам» — щит или метка «Admin only»")
                    if "444444" in общ and not общ["444444"]["глобус"]:
                        плохо(н + ": старая запись с видимостью «admin» показана без глобуса")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{ш}: ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:30]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: на «Общих» глобус перед «Код» вместо метки «Для всех», у своего общего — «Мой», ветки «только администраторам» нет; "
          "на «Моих» меток нет, опубликованный — с глобусом; «Мой» включает фильтр «Мои»; значки одного размера и не прилипли — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
