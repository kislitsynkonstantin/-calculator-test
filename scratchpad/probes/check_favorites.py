#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Избранные опции: вкладка в поиске, сброс последним и выключен, свой переключатель «глаза».

Константин 26.09.2026: «в поиске добавь ещё «Избранные» — там, где стоит
звёздочка»; «сбросить избранные поставь в конце в настройках и в выпадающем
окне. И по умолчанию поставь, чтобы тоггл был выключен. Идея в том, что
менеджер оставляет избранные опции и из проекта в проект они показываются»;
«не скрывать со звёздочками вынеси в отдельный тоггл. А в тоггле выше „со
звёздочкой“ убери».

Проба держит на 390 и 1440, в обеих темах:
  • в окне поиска по опциям есть вкладка «Избранные», и в ней ровно
    отмеченные звёздочкой опции;
  • «Сбросить избранные» — последний пункт меню «Сбросить» и последний
    переключатель списка «Сбросить всё», и он выключен даже у того, у кого в
    настройках сохранено старое `stars: true`;
  • «Сбросить всё» по умолчанию звёздочки не снимает, а с включённым пунктом —
    снимает;
  • у «глаза» отдельный переключатель «Не скрывать опции со звёздочкой»: с
    ним невыбранная опция со звёздочкой видна, без него — скрыта; по умолчанию
    он выключен (Константин, 26.09.2026: «этот тоггл по умолчанию поставь,
    чтобы был выключен»); в подписи «Скрывать не выбранные» звёздочки нет.

    python3 check_favorites.py
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
  const итог = {};
  // выбрать проект, чтобы опции нарисовались
  if (!selectedProject && typeof PROJECTS !== 'undefined' && PROJECTS.length) {
    try { selectProjectByName ? selectProjectByName(PROJECTS[0][0]) : null; } catch (e) {}
  }
  const все = OPTIONS.filter(o => !o.included && (typeof isOptionVisible !== 'function' || isOptionVisible(o)));
  const звёзды = все.slice(0, 2).map(o => o.id), третья = все[2] && все[2].id;
  starredOpts.clear(); звёзды.forEach(id => starredOpts.add(id));
  // 1. поиск
  openOptSearch(); await ждать(150);
  const чип = document.querySelector('#optSearchPanel .ops-chip[data-f="star"]');
  итог.чип = чип ? чип.textContent.trim() : '';
  if (чип) { setOptSearchFilter('star'); await ждать(150); }
  итог.вПоиске = (_optSearchRows || []).map(r => r.id);
  try { closeOptSearch(); } catch (e) { try { document.getElementById('optSearchOverlay').style.display = 'none'; } catch (e2) {} }
  // 2. меню сброса
  const пункты = [...document.querySelectorAll('#resetDropdownMenu .reset-dropdown-item')];
  итог.последнийВМеню = пункты.length ? пункты[пункты.length - 1].id : '';
  // 3. настройки: старое сохранённое stars:true; presentationMode — как из аккаунта, без нового ключа
  appSettings.presentationMode = { hideUnchecked: true, hidePrices: false, hideManual: false, hideSecPct: false };
  appSettings.resetAllConfig = Object.assign({}, appSettings.resetAllConfig, { stars: true });
  openSettings(); await ждать(200);
  const ряды = [...document.querySelectorAll('#settingsBody .st-fold-body .st-row')];
  const последний = ряды[ряды.length - 1];
  итог.последнийВНастройках = последний ? последний.querySelector('.st-label').textContent.trim() : '';
  итог.включёнПоУмолчанию = последний ? последний.querySelector('input').checked : null;
  const глаз = [...document.querySelectorAll('#settingsBody .st-row')].map(р => ({ имя: (р.querySelector('.st-label') || {}).textContent || '', подпись: (р.querySelector('.st-sub') || {}).textContent || '' }));
  const iСкр = глаз.findIndex(р => р.имя.trim() === 'Скрывать не выбранные опции');
  итог.подписьСкрытия = iСкр >= 0 ? глаз[iСкр].подпись.trim() : '';
  итог.следующийЗаСкрытием = iСкр >= 0 && глаз[iСкр + 1] ? глаз[iСкр + 1].имя.trim() : '';
  // По умолчанию переключатель выключен — и при пустом presentationMode из
  // аккаунта, где ключа ещё нет.
  const рядЗвёзд = [...document.querySelectorAll('#settingsBody .st-row')].find(р => ((р.querySelector('.st-label') || {}).textContent || '').trim() === 'Не скрывать опции со звёздочкой');
  итог.звёздыВключеныПоУмолчанию = рядЗвёзд ? рядЗвёзд.querySelector('input').checked : null;
  // Включение уходит в настройки аккаунта (profiles.app_settings), а не только в браузер.
  if (рядЗвёзд) { рядЗвёзд.querySelector('input').click(); await ждать(200); }
  const профиль = (window.__ТАБЛИЦЫ.profiles || [])[0] || {};
  итог.вАккаунте = ((профиль.app_settings || {}).presentationMode || {}).keepStarred;
  if (рядЗвёзд) { рядЗвёзд.querySelector('input').click(); await ждать(200); }
  итог.вАккаунтеПослеСнятия = ((((window.__ТАБЛИЦЫ.profiles || [])[0] || {}).app_settings || {}).presentationMode || {}).keepStarred;
  try { closeSettings(); } catch (e) {}
  // 4. сброс всего
  resetEverything(); await ждать(150);
  итог.звёздПослеСброса = starredOpts.size;
  appSettings.resetAllConfig.favorites = true;
  звёзды.forEach(id => starredOpts.add(id));
  resetEverything(); await ждать(150);
  итог.звёздПослеСбросаВкл = starredOpts.size;
  appSettings.resetAllConfig.favorites = false;
  return итог;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тема in ("blank", "light"):
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                    стр.evaluate(f"() => applyUiStyle('{тема}', false)")
                    н = f"{ш} {тема}"
                    try:
                        р = стр.evaluate(СЦЕНАРИЙ)
                    except Exception as e:
                        плохо(f"{н}: сценарий упал: {str(e)[:160]}"); стр.close(); continue
                    if ш == 390 and тема == "blank":
                        print("  " + json.dumps(р, ensure_ascii=False))
                    if р["чип"] != "Избранные": плохо(н + ": в поиске по опциям нет вкладки «Избранные»")
                    elif len(р["вПоиске"]) != 2: плохо(н + f": на вкладке «Избранные» {len(р['вПоиске'])} опций, а отмечено 2")
                    if р["последнийВМеню"] != "rdStars": плохо(н + f": последний пункт меню «Сбросить» — {р['последнийВМеню']}, а не «Сбросить избранные»")
                    if "Избранные" not in р["последнийВНастройках"]: плохо(н + f": последний в «Сбросить всё» — «{р['последнийВНастройках']}»")
                    if р["включёнПоУмолчанию"]: плохо(н + ": сброс избранных включён по умолчанию (при старом stars: true)")
                    if "звёзд" in р["подписьСкрытия"]: плохо(н + f": в подписи «Скрывать не выбранные» осталась звёздочка: «{р['подписьСкрытия']}»")
                    if р["следующийЗаСкрытием"] != "Не скрывать опции со звёздочкой": плохо(н + f": за «Скрывать не выбранные» идёт «{р['следующийЗаСкрытием']}»")
                    if р.get("звёздыВключеныПоУмолчанию") is not False: плохо(н + f": «Не скрывать опции со звёздочкой» по умолчанию не выключен ({р.get('звёздыВключеныПоУмолчанию')})")
                    if р.get("вАккаунте") is not True or р.get("вАккаунтеПослеСнятия") is not False:
                        плохо(н + f": переключатель не доходит до настроек аккаунта ({р.get('вАккаунте')} → {р.get('вАккаунтеПослеСнятия')})")
                    if р["звёздПослеСброса"] != 2: плохо(н + f": «Сбросить всё» по умолчанию сняло звёздочки (осталось {р['звёздПослеСброса']})")
                    if р["звёздПослеСбросаВкл"] != 0: плохо(н + ": с включённым пунктом «Сбросить всё» звёздочки не сняло")
                    # «глаз»: невыбранная опция со звёздочкой
                    вид = стр.evaluate("""async () => {
                      const ждать = мс => new Promise(r => setTimeout(r, мс));
                      const item = [...document.querySelectorAll('.opt-item')].find(i => i.dataset.optId && !i.classList.contains('active'));
                      if (!item) return null;
                      const id = item.dataset.optId; starredOpts.add(id);
                      appSettings.presentationMode = Object.assign({}, appSettings.presentationMode, { hideUnchecked: true, keepStarred: true });
                      if (!globalHiding) toggleHideAll(); await ждать(150);
                      const с = item.style.display !== 'none';
                      appSettings.presentationMode.keepStarred = false; toggleHideAll(); toggleHideAll(); await ждать(150);
                      const без = item.style.display !== 'none';
                      toggleHideAll(); starredOpts.delete(id); appSettings.presentationMode.keepStarred = true;
                      return { с, без };
                    }""")
                    if not вид: плохо(н + ": не нашлось невыбранной опции для проверки «глаза»")
                    else:
                        if not вид["с"]: плохо(н + ": с «Не скрывать опции со звёздочкой» опция со звёздочкой скрыта")
                        if вид["без"]: плохо(н + ": без «Не скрывать опции со звёздочкой» опция со звёздочкой видна")
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
    print("Чисто: в поиске есть «Избранные» ровно со звёздочками; «Сбросить избранные» последний в меню и в настройках и "
          "выключен даже при старом stars: true; «Сбросить всё» звёзды по умолчанию бережёт; у «глаза» свой переключатель для звёздочек.")


if __name__ == "__main__":
    главная()
