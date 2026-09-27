#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Корзины на чужом общем пресете нет ни у кого — и у администратора.

Константин 26.09.2026 оставил корзину на чужих карточках только
администратору; 27.09.2026 снял и её: «Убери у администратора тоже эту
корзину в общих, чтобы случайно не удалить. Только автор может удалить пресет,
перед этим отозвав его».

Проба держит на 390 и 1440 для трёх ролей — администратор, редактор, менеджер:
  • на чужой карточке, открытой и запертой, нет ни корзины, ни другой кнопки
    снятия или удаления;
  • на своей карточке стоит «Отозвать», корзины нет;
  • функции снятия чужого пресета в калькуляторе больше нет, и функция базы
    `admin_unpublish_preset` не вызывается.

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
  const снятие = код => [...document.querySelectorAll('.shared-pcard[data-scode="' + код + '"] button')].filter(б => б.offsetWidth &&
    (б.classList.contains('danger') || /Снять|Удалить/i.test((б.title || '') + (б.getAttribute('aria-label') || '')) || /Remove|delete/i.test(б.getAttribute('onclick') || '')));
  const карта = { свой: снятие('111111').length > 0, чужойОткрытый: снятие('222222').length > 0, чужойЗапертый: снятие('333333').length > 0,
    отозватьУСвоего: !!document.querySelector('.shared-pcard[data-scode="111111"] .btn-retract'),
    функция: typeof window.adminRemoveShared === 'function' };
  const отказ = null, снят = null;
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
                    if к["свой"]: плохо(н + ": на своей карточке стоит корзина")
                    if not к["отозватьУСвоего"]: плохо(н + ": на своей карточке нет «Отозвать»")
                    for имя in ("чужойОткрытый", "чужойЗапертый"):
                        if к[имя]:
                            плохо(н + f": {имя} — на чужой карточке есть кнопка снятия или удаления")
                    if к["функция"]: плохо(н + ": функция снятия чужого пресета в калькуляторе осталась")
                    if р["вызовы"]: плохо(н + f": вызвана admin_unpublish_preset ({р['вызовы']})")
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
    print("Чисто: на чужой общей карточке нет кнопки снятия или удаления ни у администратора, ни у редактора, ни у "
          "менеджера; на своей — «Отозвать» и корзины нет — на 390 и 1440.")


if __name__ == "__main__":
    главная()
