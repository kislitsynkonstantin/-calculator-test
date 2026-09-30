#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Убранные с холста снимки удаляются из хранилища — если больше никому не нужны.

Константин 30.09.2026: «когда распознаю проект — добавляется много видов
планировки (6-7). Потом оставляю 1, остальные с базы пропадают? Чтобы не
забивать память картинками». До этого убранный снимок лежал в хранилище
навсегда: на тот день 151 файл из 252 не был нужен никому.

Проба (390 и 1440) кладёт на холст снимки с адресами хранилища и убирает их
крестиком, как менеджер, затем сохраняет пресет и держит:
  • до сохранения ничего не удаляется;
  • после сохранения база спрошена только о своих файлах (папка = свой id), и
    удалён только тот, на который, по её ответу, нет ссылок;
  • не удаляются: чужой файл, снимок, на который база нашла ссылку (копия
    пресета, клиентская ссылка), снимок, который вернули на холст, и снимок,
    ещё не ушедший в хранилище (data:).

    python3 check_canvas_cleanup.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_card as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ПОДГОТОВКА = """(порт) => {
  const uid = _sbUser.id, адрес = п => `http://127.0.0.1:${порт}/storage/v1/object/public/preset-photos/${п}`;
  window.__спрошено = []; window.__убрано = [];
  window.__RPC.unreferenced_canvas_images = а => { window.__спрошено.push(...а.p_names); return а.p_names.filter(н => !н.includes('держит')); };
  const исх = _sb.storage.from.bind(_sb.storage);
  _sb.storage.from = б => { const о = исх(б); о.remove = имена => { window.__убрано.push(...имена); return Promise.resolve({ data: [], error: null }); }; return о; };
  canvasItems.length = 0; document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
  const снимки = {
    лишний: адрес(uid + '/проба/1.jpg'),
    держит: адрес(uid + '/проба/держит.jpg'),
    чужой: адрес('другой-пользователь/проба/3.jpg'),
    вернули: адрес(uid + '/проба/4.jpg'),
    новый: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' };
  const ид = {};
  Object.entries(снимки).forEach(([к, src]) => { ид[к] = canvasAddImageAt(src, 10, 10, 200, 150); });
  window.__снимки = снимки; return { uid, ид }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = к.начать(бр, порт, ш, в, False)
    стр.evaluate("() => { закрытьКарточкуЗначка && закрытьКарточкуЗначка(); const б = document.getElementById('btnCollapseImageCard'); if (б && б.classList.contains('collapsed')) toggleImageCard(); }")
    п = стр.evaluate(ПОДГОТОВКА, порт)
    uid = п["uid"]
    # Убираем крестиком, как менеджер.
    for имя in ("лишний", "держит", "чужой", "вернули", "новый"):
        # Крестик виден только под курсором — нажимаем его событием, как делает щелчок.
        есть = стр.evaluate("(ид) => { const к = document.querySelector(`#imageCanvas [id=\"${ид}\"] .img-delete`); if (!к) return false; к.dispatchEvent(new MouseEvent('click', { bubbles: true })); return true; }", п["ид"][имя])
        if not есть:
            НАХОДКИ.append(f"{н} у снимка «{имя}» нет крестика")
        стр.wait_for_timeout(100)
    # «Вернули» — снова на холсте до сохранения.
    стр.evaluate("() => canvasAddImageAt(window.__снимки.вернули, 10, 10, 200, 150)")
    стр.wait_for_timeout(300)
    до = стр.evaluate("() => window.__убрано.slice()")
    if до:
        НАХОДКИ.append(f"{н} удалено до сохранения: {до}")
    стр.evaluate("async () => { await sbSavePreset({ id: 'проба', name: 'проба', state: {} }); }")
    стр.wait_for_timeout(5500)
    р = стр.evaluate("() => ({ спрошено: window.__спрошено.slice(), убрано: window.__убрано.slice() })")
    свои = [x for x in р["спрошено"] if not x.startswith(uid + "/")]
    if свои:
        НАХОДКИ.append(f"{н} база спрошена о чужих файлах: {свои}")
    if р["убрано"] != [uid + "/проба/1.jpg"]:
        НАХОДКИ.append(f"{н} удалено {р['убрано']}, ждали только {uid}/проба/1.jpg (спрошено {р['спрошено']})")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт, 1440, 900)
            прогон(бр, порт, 390, 844)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: убранный крестиком свой снимок удаляется из хранилища после сохранения, если база не нашла на "
          "него ссылок; чужой, удержанный ссылкой, возвращённый на холст и ещё не выгруженный — остаются; до "
          "сохранения ничего не удаляется — на 1440 и 390.")


if __name__ == "__main__":
    главная()
