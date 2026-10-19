#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Общие пресеты: без «Скачать»; отправленный на согласование не отзывается.

Константин 19.10.2026, снимком вкладки «Общие»: «1. С общих пресетов кнопку
„Скачать“ вообще убери, чтобы не плодили дубли. 2. Когда общий пресет
отправляют на согласование, то кнопку „Отозвать“ делай бледной, чтобы
случайно не отозвали. Такой пресет отозвать больше нельзя. Когда его
согласуют, подпишут договор — кнопка отозвать также неактивна».

Проба держит, на заглушке базы:
  • на карточках «Общих» (свои и чужие) кнопки «Скачать» нет;
  • у своего опубликованного без согласования «Отозвать» обычная и
    спрашивает подтверждения;
  • у своего с согласованием в любом состоянии (ждёт, согласован, подписан)
    «Отозвать» бледная (aria-disabled, прозрачность), нажатие говорит словами и
    базу не трогает — окна подтверждения нет; то же у карточки в «Моих» и в
    меню мини-окна «Снять с публикации»;
  • список узнаёт о согласовании сам, одним запросом к preset_approvals.
На 390 и 1440 px.

    python3 check_retract_approval.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_shared_lock_btn as л
from playwright.sync_api import sync_playwright

НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


СЦЕНАРИЙ = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  window.__RPC = window.__RPC || {};
  const вызовы = [];
  window.__RPC.retract_preset = а => { вызовы.push(а.p_code); return true; };
  const тосты = []; window.showToast = т => { тосты.push(String(т)); };
  const я = _sbUser && _sbUser.id;
  const с = (код, имя, свой) => ({ short_code: код, name: имя, author_name: свой ? 'Проба' : 'Максим Григорьев',
    author_id: свой ? я : 'u-другой', is_public: true, visibility: 'public', locked: false,
    created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 8017902, tech: 'frame' } });
  window.__ТАБЛИЦЫ.preset_approvals = [
    { code: '611111', state: 'pending' }, { code: '622222', state: 'approved' }, { code: '633333', state: 'signed' }];
  let запросов = 0;
  const былFrom = _sb.from.bind(_sb);
  _sb.from = т => { if (т === 'preset_approvals') запросов++; return былFrom(т); };
  openPresetPanel();
  setSharedFilter('all');
  _sharedPresets.length = 0;
  _sharedPresets.push(с('600000', 'Свой без согласования', true), с('611111', 'Свой ждёт согласования', true),
    с('622222', 'Свой согласован', true), с('633333', 'Свой подписан', true), с('700000', 'Чужой', false));
  _общиеЗагружены = true;
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  renderSharedList(); await ждать(600);
  const карты = Object.fromEntries([...document.querySelectorAll('#sharedPresetList .shared-pcard')].map(к => {
    const о = к.querySelector('.btn-retract');
    return [к.dataset.scode, { скачать: !!к.querySelector('[onclick*="downloadSharedPreset"], [aria-label*="Скачать"]'),
      отозвать: !!о, бледная: о ? о.getAttribute('aria-disabled') === 'true' : null, прозрачность: о ? +getComputedStyle(о).opacity : null }];
  }));
  const нажать = async код => { тосты.length = 0; const о = document.querySelector('#sharedPresetList .shared-pcard[data-scode="' + код + '"] .btn-retract');
    о && о.click(); await ждать(250);
    const д = document.getElementById('confirmDialog'), окно = !!(д && д.classList.contains('show'));
    if (окно) document.getElementById('confirmDialogCancel').click();
    await ждать(100); return { окно, тост: тосты.slice(-1)[0] || '' }; };
  const без = await нажать('600000');
  const нажатия = {};
  for (const код of ['611111', '622222', '633333']) нажатия[код] = await нажать(код);
  // Мои: опубликованный пресет с согласованием — та же бледная кнопка.
  const все = loadAllPresets();
  все['p-проба-сг'] = { id: 'p-проба-сг', name: 'Мой с согласованием', publishedAs: 'user', shortCode: '611111', savedAt: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 8017902 } };
  saveAllPresets(все); renderPresetList(); await ждать(300);
  const мой = document.querySelector('#presetList [data-pid="p-проба-сг"] .pcard-retract');
  // Мини-окно: меню «Снять с публикации».
  const меню = отозватьНельзя('611111') && !отозватьНельзя('600000');
  return { карты, без, нажатия, вызовы, запросов,
    мои: мой ? { бледная: мой.getAttribute('aria-disabled') === 'true' } : null, меню };
}"""


def главная():
    с, порт = л.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=л.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                н = f"[{ш}]"
                стр = бр.new_page(viewport={"width": ш, "height": в})
                ош = []
                стр.on("pageerror", lambda e: ош.append(str(e)))
                стр.add_init_script(л.ЗАГЛУШКА); стр.add_init_script(л.ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                р = стр.evaluate(СЦЕНАРИЙ)
                к = р["карты"]
                for код, д in к.items():
                    if д["скачать"]:
                        плохо(f"{н} {код}: на общей карточке есть «Скачать»")
                if not к.get("600000", {}).get("отозвать") or к["600000"]["бледная"]:
                    плохо(f"{н} свой без согласования: «Отозвать» {к.get('600000')}")
                for код in ("611111", "622222", "633333"):
                    д = к.get(код, {})
                    if not д.get("отозвать") or not д.get("бледная") or (д.get("прозрачность") or 1) > .5:
                        плохо(f"{н} {код}: «Отозвать» не бледная при согласовании: {д}")
                    нж = р["нажатия"][код]
                    if нж["окно"] or "согласование" not in нж["тост"]:
                        плохо(f"{н} {код}: нажатие на бледную «Отозвать»: {нж}")
                if not р["без"]["окно"]:
                    плохо(f"{н} обычная «Отозвать» не спросила подтверждения")
                if р["вызовы"]:
                    плохо(f"{н} база вызвана для отзыва: {р['вызовы']}")
                if р["запросов"] < 1:
                    плохо(f"{н} список не спросил preset_approvals")
                if not р["мои"] or not р["мои"]["бледная"]:
                    плохо(f"{н} в «Моих» «Отозвать» у пресета с согласованием: {р['мои']}")
                if not р["меню"]:
                    плохо(f"{н} мини-окно разрешает «Снять с публикации» пресету с согласованием")
                стр.screenshot(path=str(pathlib.Path("/tmp") / f"retract-approval-{ш}.png"))
                for о in [о for о in ош if "supabase.co" not in о][:3]:
                    плохо(f"{н} ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        raise SystemExit(1)
    print("Чисто: на общих карточках «Скачать» нет; у пресета с согласованием (ждёт, согласован, подписан) «Отозвать» "
          "бледная в «Общих», «Моих» и меню мини-окна, нажатие объясняет словами и базу не трогает; без согласования — "
          "как прежде, с подтверждением; на 390 и 1440.")


if __name__ == "__main__":
    главная()
