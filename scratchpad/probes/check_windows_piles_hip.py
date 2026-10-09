#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окна Veka/Rehau, сваи по площади и вальмовая кровля.

Константин 08.10.2026 по таблице цен от 29.09.2026:
  • окна — переключатель Veka/Rehau, как у террасной доски; цена одна,
    Veka первой и по умолчанию; стеклянная дверь следует переключателю;
  • сваи — формула в калькуляторе: (тёплый контур + открытая + крытая
    терраса) × ставка по ступеням площади; без площадей — ручной ввод;
  • вальмовая кровля — 3 % цены 150 мм при любой толщине (09.10.2026).

Проба нажимает и смотрит на цену, имя и итог, а не на разметку:

  • у четырёх строк (базовые окна, 70, 80 мм, стеклянная дверь) есть
    переключатель, по умолчанию Veka; щелчок Rehau на одной строке переводит
    все четыре, цена и итог при этом не меняются;
  • расчёт, сохранённый до переключателя (бренда окон в нём нет), открывается
    с Rehau, сохранённый с Veka — с Veka;
  • сваи считаются от площадей проекта, число из прайса не берётся, цена,
    вписанная карандашом, главнее правила; у проекта без площадей цены нет —
    поле для ручного ввода;
  • вальмовая кровля — 3 % цены 150 мм и от толщины не зависит; галочка добавляет к итогу
    ровно свою цену;
  • алюминиевые окна закрывают и снимают пластиковые — базовые, 70 и 80 мм,
    белый профиль, обе ламинации и подоконники, — а установку, стёкла и двери
    не трогают; сняли алюминиевые — базовые окна, стеклопакет и подоконники
    вернулись;
  • открытый расчёт держит базовые строки в порядке каталога во всех
    разделах, а не задом наперёд.

    python3 check_windows_piles_hip.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))

# Проект без площадей — для ручного ввода цены свай.
ПУСТОЙ = dict(ДАННЫЕ["pricing_projects"][0], slug="proba-bez-ploschadey",
              name="Проба без площадей", warm=0, open_area=0, closed_area=0, sort=99)
ПРОЕКТЫ = ДАННЫЕ["pricing_projects"] + [ПУСТОЙ]
ОКНА_70 = 84656
ДОБАВКА = [
    {"product": "frame", "option_id": "w8", "section": "windows", "name": "x",
     "included": False, "price": ОКНА_70, "formula": None, "status": None, "sort": 83},
    {"product": "frame", "option_id": "w9", "section": "windows", "name": "x",
     "included": False, "price": 169312, "formula": None, "status": None, "sort": 84},
    {"product": "frame", "option_id": "w13", "section": "windows", "name": "x",
     "included": False, "price": 427350, "formula": None, "status": None, "sort": 88},
    {"product": "frame", "option_id": "f5", "section": "foundation", "name": "x",
     "included": False, "price": 237850, "formula": None, "status": None, "sort": 4},
    {"product": "frame", "option_id": "f9", "section": "foundation", "name": "x",
     "included": False, "price": 272028, "formula": None, "status": None, "sort": 8},
]
ОПЦИИ = [o for o in ДАННЫЕ["pricing_options"] if o["option_id"] not in {о["option_id"] for о in ДОБАВКА}] + ДОБАВКА
# Число в прайсе у свай правило брать не должно.
МАТРИЦА = ДАННЫЕ["pricing_matrix"] + [
    {"product": "frame", "project_slug": ПРОЕКТЫ[0]["slug"], "option_id": "f5", "price": 999999},
    {"product": "frame", "project_slug": ПУСТОЙ["slug"], "option_id": "f5", "price": 888888},
]
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(ДАННЫЕ, pricing_projects=ПРОЕКТЫ, pricing_options=ОПЦИИ,
                                pricing_matrix=МАТРИЦА), ensure_ascii=False) + ");")

П = ПРОЕКТЫ[0]
ПЛОЩАДЬ = (П["warm"] or 0) + (П["open_area"] or 0) + (П["closed_area"] or 0)


def ставка(ступени, площадь):
    return next(с for до, с in ступени if площадь <= до)


ЖДЁМ_F5 = round(ПЛОЩАДЬ * ставка([(20, 4000), (40, 3800), (60, 3400), (80, 3300), (100, 3200), (1e9, 3000)], ПЛОЩАДЬ))
ЖДЁМ_F9 = round(ПЛОЩАДЬ * ставка([(20, 4500), (40, 4300), (60, 3900), (80, 3800), (100, 3700), (1e9, 3500)], ПЛОЩАДЬ))
# Вальмовая — всегда 3 % цены 150 мм, при любой толщине (Константин, 09.10.2026).
ЖДЁМ_R24 = [round(П["price_150"] * 0.03)] * 3
НАХОДКИ = []


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


ШАГИ = """async ([пустой]) => {
  const пауза = (мс = 250) => new Promise(r => setTimeout(r, мс));
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const цифры = т => Number(String(т || '').replace(/\\D/g, '')) || 0;
  const имя = ид => ((document.querySelector('#lbl_' + ид + ' .opt-name') || {}).textContent || '').trim();
  const цена = ид => цифры((document.getElementById('optprice_' + ид) || {}).textContent);
  const ОКНА = ['w1', 'w8', 'w9', 'w14'];
  const бренды = () => ОКНА.map(ид => {
    const а = document.querySelector('#ovar_' + ид + '_0.active') ? 'Veka'
            : document.querySelector('#ovar_' + ид + '_1.active') ? 'Rehau' : '—';
    return а;
  });
  const р = {};
  const индекс = PROJECTS.findIndex(п => п[0] === 'Проба дом 8×8');
  selectProjectOption(индекс); await пауза(800);
  setThickness(1); await пауза(300);

  // ── окна ──
  р.кнопки = ОКНА.map(ид => [0, 1].map(и => (document.getElementById('ovar_' + ид + '_' + и) || {}).textContent || ''));
  р.брендДо = бренды();
  р.именаДо = ОКНА.map(имя);
  if (!checkedOptions.w8) toggleOpt('w8');
  await пауза();
  р.цена70До = цена('w8');
  р.итогДо = _currentTotal;
  setOptVariant('w8', 1); await пауза();
  р.брендПосле = бренды();
  р.именаПосле = ОКНА.map(имя);
  р.имяВДокументе = getOpt('w14').name;
  р.цена70После = цена('w8');
  р.итогПосле = _currentTotal;
  const снимокRehau = JSON.parse(JSON.stringify(collectState()));
  setOptVariant('w1', 0); await пауза();
  const снимокVeka = JSON.parse(JSON.stringify(collectState()));
  const старый = JSON.parse(JSON.stringify(снимокVeka));
  delete старый.optVariants.w1; delete старый.optVariants.w8; delete старый.optVariants.w9; delete старый.optVariants.w14;
  restoreState(старый); await пауза(800);
  р.старыйРасчёт = бренды();
  restoreState(снимокVeka); await пауза(800);
  р.расчётVeka = бренды();
  // базовые строки открытого расчёта — в порядке каталога, во всех разделах
  р.порядок = SECTIONS.map(с => {
    const список = document.getElementById('list_' + с.key); if (!список) return null;
    const наЭкране = [...список.children].map(э => э.dataset && э.dataset.optId).filter(ид => ид && (getOpt(ид) || {}).included);
    const вКаталоге = OPTIONS.filter(о => о.section === с.key && о.included).map(о => о.id).filter(ид => наЭкране.includes(ид));
    return наЭкране.join(',') === вКаталоге.join(',') ? null : с.key + ': ' + наЭкране.join(' ');
  }).filter(Boolean);
  restoreState(снимокRehau); await пауза(800);
  р.расчётRehau = бренды();
  setOptVariant('w1', 0); await пауза();
  if (checkedOptions.w8) toggleOpt('w8');
  await пауза();

  // ── алюминиевые окна закрывают пластиковые ──
  const закрыта = ид => { const л = document.getElementById('lbl_' + ид); return !!(л && л.querySelector('.excl-lock')); };
  const отмечена = ид => !!checkedOptions[ид];
  toggleOpt('w9'); await пауза();
  toggleOpt('w11'); await пауза();
  р.алюДо = ['w1','w2','w4','w8','w9','w10','w11'].map(ид => закрыта(ид));
  toggleOpt('w13'); await пауза();
  р.алюЗакрыты = ['w1','w2','w4','w8','w9','w10','w11'].filter(ид => !закрыта(ид) || отмечена(ид));
  р.алюОткрыты = ['w3','w16','w14','w15','w12'].filter(ид => закрыта(ид));
  р.алюОбщие = ['w3'].filter(ид => !отмечена(ид));
  toggleOpt('w13'); await пауза();
  р.алюСняты = ['w1','w2','w4'].filter(ид => !отмечена(ид) || закрыта(ид));
  р.алюСвободны = ['w8','w9','w10','w11'].filter(ид => закрыта(ид));

  // ── сваи ──
  р.f5 = цена('f5'); р.f9 = цена('f9');
  matrixOverrides.set(selectedProject, Object.assign({}, matrixOverrides.get(selectedProject) || {}, { f5: 123456 }));
  refreshOptPricesInDOM(); await пауза();
  р.f5Карандаш = цена('f5');
  const mo = matrixOverrides.get(selectedProject); delete mo.f5;
  refreshOptPricesInDOM(); await пауза();
  р.f5Вернулась = цена('f5');

  // ── вальмовая кровля ──
  р.r24Есть = !!document.getElementById('lbl_r24');
  р.r24 = [];
  for (const т of [0, 1, 2]) { setThickness(т); await пауза(300); р.r24.push(цена('r24')); }
  setThickness(1); await пауза(300);
  const итог0 = _currentTotal;
  toggleOpt('r24'); await пауза();
  р.r24Прирост = _currentTotal - итог0;
  toggleOpt('r24'); await пауза();

  // ── проект без площадей ──
  selectProjectOption(PROJECTS.findIndex(п => п[0] === пустой)); await пауза(800);
  р.пустойF5 = цена('f5');
  р.пустойРучнойВвод = !!document.getElementById('por_f5') || !!document.getElementById('porwrap_f5');
  р.пустойR24 = цена('r24');
  return р;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            try:
                р = стр.evaluate(ШАГИ, [ПУСТОЙ["name"]])
            except Exception as e:
                плохо(f"проба оборвалась: {e!s:.300}")
                р = None
            if р:
                if any(к != ["Veka", "Rehau"] for к in р["кнопки"]):
                    плохо(f"переключатель окон: {р['кнопки']}")
                if р["брендДо"] != ["Veka"] * 4:
                    плохо(f"по умолчанию не Veka: {р['брендДо']}")
                if not all("Veka" in и for и in р["именаДо"]):
                    плохо(f"имена по умолчанию: {р['именаДо']}")
                if р["брендПосле"] != ["Rehau"] * 4:
                    плохо(f"Rehau на одной строке не перевёл остальные: {р['брендПосле']}")
                if not all("Rehau" in и for и in р["именаПосле"]) or "Rehau" not in р["имяВДокументе"]:
                    плохо(f"имена после Rehau: {р['именаПосле']}, в документе: {р['имяВДокументе']}")
                if not ("Grazio 70" in р["именаПосле"][1] and "Intelio 80" in р["именаПосле"][2]):
                    плохо(f"у Rehau потерялась система профиля: {р['именаПосле'][1:3]}")
                if р["цена70До"] != ОКНА_70 or р["цена70После"] != ОКНА_70:
                    плохо(f"цена окон 70 мм: Veka {р['цена70До']}, Rehau {р['цена70После']}, ждали {ОКНА_70}")
                if р["итогДо"] != р["итогПосле"]:
                    плохо(f"смена бренда сдвинула итог: {р['итогДо']} → {р['итогПосле']}")
                if р["старыйРасчёт"] != ["Rehau"] * 4:
                    плохо(f"расчёт без бренда окон открылся с {р['старыйРасчёт']}, ждали Rehau")
                if р["порядок"]:
                    плохо(f"базовые строки открытого расчёта не в порядке каталога: {р['порядок'][:3]}")
                if р["расчётVeka"] != ["Veka"] * 4 or р["расчётRehau"] != ["Rehau"] * 4:
                    плохо(f"сохранённый бренд не вернулся: Veka → {р['расчётVeka']}, Rehau → {р['расчётRehau']}")
                if р["алюЗакрыты"]:
                    плохо(f"алюминиевые окна не закрыли пластиковые: открыты или отмечены {р['алюЗакрыты']}")
                if р["алюОткрыты"]:
                    плохо(f"алюминиевые окна закрыли лишнее: {р['алюОткрыты']}")
                if р["алюОбщие"]:
                    плохо(f"установка стеклопакета снялась вместе с пластиком: {р['алюОбщие']}")
                if р["алюСняты"]:
                    плохо(f"сняли алюминиевые — базовые окна, стеклопакет и подоконники не вернулись: {р['алюСняты']}")
                if р["алюСвободны"]:
                    плохо(f"сняли алюминиевые — пластик остался закрытым: {р['алюСвободны']}")
                if р["f5"] != ЖДЁМ_F5 or р["f9"] != ЖДЁМ_F9:
                    плохо(f"сваи при {ПЛОЩАДЬ} м²: винтовые {р['f5']} (ждали {ЖДЁМ_F5}), забивные {р['f9']} (ждали {ЖДЁМ_F9})")
                if р["f5Карандаш"] != 123456:
                    плохо(f"цена карандашом не главнее правила: {р['f5Карандаш']}")
                if р["f5Вернулась"] != ЖДЁМ_F5:
                    плохо(f"после снятия своей цены сваи не вернулись к правилу: {р['f5Вернулась']}")
                if not р["r24Есть"]:
                    плохо("строки «Вальмовая кровля» нет")
                if р["r24"] != ЖДЁМ_R24:
                    плохо(f"вальмовая кровля по толщинам: {р['r24']}, ждали {ЖДЁМ_R24}")
                if р["r24Прирост"] != ЖДЁМ_R24[1]:
                    плохо(f"галочка вальмовой кровли прибавила {р['r24Прирост']}, ждали {ЖДЁМ_R24[1]}")
                if р["пустойF5"] or not р["пустойРучнойВвод"]:
                    плохо(f"проект без площадей: цена свай {р['пустойF5']}, поле ручного ввода — {р['пустойРучнойВвод']}")
                if р["пустойR24"] != round(ПУСТОЙ["price_150"] * 0.03):
                    плохо(f"вальмовая кровля у проекта без площадей: {р['пустойR24']}")
                print(f"  окна 70 мм: {р['цена70До']} ₽ при Veka и Rehau, итог {р['итогДо']} → {р['итогПосле']}; "
                      f"старый расчёт → {р['старыйРасчёт'][0]}")
                print(f"  сваи {ПЛОЩАДЬ} м²: {р['f5']} / {р['f9']} ₽; карандаш {р['f5Карандаш']}; "
                      f"вальмовая {р['r24']}; без площадей — ручной ввод: {р['пустойРучнойВвод']}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:300])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: бренд окон один на четыре строки и не трогает цену, старый расчёт открывается "
          "с Rehau; сваи считаются от площадей, карандаш главнее, без площадей — ручной ввод; "
          "вальмовая кровля — 3 % базы выбранной толщины; алюминиевые окна закрывают пластиковые и подоконники "
          "и отпускают их, когда сняты; базовые строки открытого расчёта — в порядке каталога.")


if __name__ == "__main__":
    главная()
