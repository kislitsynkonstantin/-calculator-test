/* Заглушка Supabase для проб.
   Домен базы закрыт шлюзом наружу, да и настоящие данные пробе не нужны:
   проверяется разметка и расстояния, а не выборка. Подменяем создатель
   клиента до того, как страница до него дойдёт: `const _sb = supabase
   .createClient(...)` выполняется в первом же скрипте. */
(function () {
  var ПОЛЬЗОВАТЕЛЬ = { id: 'u-проба', email: 'probe@baniamsk.ru', user_metadata: { name: 'Проба' } };
  var СЕССИЯ = { user: ПОЛЬЗОВАТЕЛЬ, access_token: 'проба', refresh_token: 'проба',
                 expires_at: Math.floor(Date.now() / 1000) + 3600 };
  /* Строки, которые пробе нужны по существу: ссылка и три захода по ней.
     Без них перечитывание из полосы обнуляло бы счётчик, и снимок показывал
     бы «ещё не открывали» там, где проверяется подпись о заходах. */
  window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {
    client_links: [{
      code: 'adkv8q5j', revoked: false, author_id: 'u-проба', preset_id: '7',
      project_name: 'Фахверковая баня «Берлин» 9×5', client_name: 'Иванов Иван Сергеевич',
      created_at: '2026-09-10T09:00:00Z', snapshot_at: '2026-09-16T10:00:00Z', snapshot: {},
    }, {
      code: 'bezpres1', revoked: false, author_id: 'u-проба', preset_id: null,
      project_name: 'Баня 6×4 без пресета', client_name: '',
      created_at: '2026-09-14T08:00:00Z', snapshot_at: '2026-09-14T09:00:00Z', snapshot: {},
    }],
    // Пресет лежит только в облаке: в этом браузере его нет. Так проверяется
    // длинный путь перехода — достать строку прицельно и открыть.
    presets: [{ id: '7', user_id: 'u-проба', name: 'Фахверковая баня «Берлин» 9×5',
                state: {}, updated_at: '2026-09-16T10:00:00Z' }],
    client_link_visits: [
      { code: 'adkv8q5j', seen_at: '2026-09-16T14:22:00Z', version_at: '2026-09-16T10:00:00Z' },
      { code: 'adkv8q5j', seen_at: '2026-09-15T18:03:00Z', version_at: '2026-09-16T10:00:00Z' },
      { code: 'adkv8q5j', seen_at: '2026-09-15T11:40:00Z', version_at: '2026-09-12T08:00:00Z' },
      // Ссылка без пресета: её строка в уведомлениях открывать нечего.
      { code: 'bezpres1', seen_at: '2026-09-14T09:10:00Z', version_at: '2026-09-14T09:00:00Z' },
    ],
  };
/* Опции каркаса — как строки pricing_options (product 'frame'). С 17.10.2026
   список каркаса калькулятор берёт из базы, как у бруса, и проба без него
   показала бы пустые разделы. Цен здесь нет: цена, формула и статус берутся
   у строки того же id из таблиц пробы, если она там есть. */
  var ОПЦИИ_КАРКАСА = [
    {"option_id": "f1", "name": "Консультация менеджера по выбору типа фундамента", "section": "foundation", "included": true, "sort": 0},
    {"option_id": "f2", "name": "Выезд инженера по свайному фундаменту", "section": "foundation", "included": true, "sort": 1},
    {"option_id": "f3", "name": "Пробное бурение для определения несущей способности грунта", "section": "foundation", "included": true, "sort": 2},
    {"option_id": "f4", "name": "Приёмка фундамента технадзором (фундамент заказчика)", "section": "foundation", "included": false, "sort": 3, "status": "legacy"},
    {"option_id": "f5", "name": "Свайно-винтовой фундамент без обвязки (D108/L2500)", "section": "foundation", "included": false, "sort": 4},
    {"option_id": "f6", "name": "Двойная обвязка профилированной трубой к свайно-винтовому фундаменту", "section": "foundation", "included": false, "sort": 5},
    {"option_id": "f9", "name": "Забивные сваи (D150/L3000), без учёта перепада высот", "section": "foundation", "included": false, "sort": 6},
    {"option_id": "f7", "name": "Закрытие цоколя декоративными панелями (материал заказчика)", "section": "foundation", "included": false, "sort": 7},
    {"option_id": "f8", "name": "Закрытие цоколя профилированным листом (цвет на выбор)", "section": "foundation", "included": false, "sort": 8},
    {"option_id": "f12", "name": "Отливы на цоколь (металл)", "section": "foundation", "included": false, "sort": 9},
    {"option_id": "f10", "name": "Ленточный фундамент (мелкозаглублённый)", "section": "foundation", "included": false, "sort": 10, "status": "legacy"},
    {"option_id": "f11", "name": "Плитный фундамент (мелкозаглублённый), без учёта перепада высот", "section": "foundation", "included": false, "sort": 11},
    {"option_id": "fr1", "name": "Одинарная обвязка фундамента — брус непрофилированный 150×200 мм (транспортная влажность)", "section": "frame", "included": true, "sort": 12},
    {"option_id": "fr2", "name": "Лаги пола — строганная доска камерной сушки 45×145 мм с шагом 580 мм", "section": "frame", "included": true, "sort": 13},
    {"option_id": "fr3", "name": "Черновой пол — обрезная доска 40×90 мм (транспортная влажность)", "section": "frame", "included": true, "sort": 14},
    {"option_id": "fr4", "name": "Антисептирование — обработка обвязки и лаг пола", "section": "frame", "included": true, "sort": 15},
    {"option_id": "fr5", "name": "Каркас наружных стен — строганная доска камерной сушки 45×145 мм", "section": "frame", "included": true, "sort": 16},
    {"option_id": "fr6", "name": "Каркас внутренних перегородок — строганная доска камерной сушки 45×95 мм", "section": "frame", "included": true, "sort": 17},
    {"option_id": "fr7", "name": "Клееные столбы на террасе 200×200 мм", "section": "frame", "included": true, "sort": 18},
    {"option_id": "fr8", "name": "Стропильная система — доска сухая строганная 45×145 мм", "section": "frame", "included": true, "sort": 19},
    {"option_id": "fr9", "name": "Обрешётка кровли — доска 25×100 мм", "section": "frame", "included": true, "sort": 20},
    {"option_id": "fr10", "name": "Контробрешётка кровли — доска 50×50 мм", "section": "frame", "included": true, "sort": 21},
    {"option_id": "fr11", "name": "Высота пол/потолок в комнате отдыха — согласно проекту", "section": "frame", "included": true, "sort": 22},
    {"option_id": "fr12", "name": "Материал чистового пола — фанера 21 мм (под стяжку/чистовое покрытие)", "section": "frame", "included": false, "sort": 23},
    {"option_id": "fr13", "name": "Обработка каркаса бани несмываемым антисептиком (огне- и биозащита)", "section": "frame", "included": false, "sort": 24},
    {"option_id": "fr14", "name": "Обработка фасада на зиму консервирующим средством", "section": "frame", "included": false, "sort": 25, "status": "legacy"},
    {"option_id": "fr15", "name": "Заводской комплект поставки усиленного каркаса (антисептированный Неомид)", "section": "frame", "included": false, "sort": 26, "status": "legacy"},
    {"option_id": "fr16", "name": "Поднятие конька (по проекту)", "section": "frame", "included": false, "sort": 27, "status": "legacy"},
    {"option_id": "fr17", "name": "Поднятие стен второго этажа (по проекту)", "section": "frame", "included": false, "sort": 28, "status": "legacy"},
    {"option_id": "fr18", "name": "Защитная сетка от грызунов", "section": "frame", "included": false, "sort": 29},
    {"option_id": "in1", "name": "Утеплитель — минеральная вата KNAUF Aquastatik", "section": "insulation", "included": true, "sort": 30},
    {"option_id": "in2", "name": "Утепление наружных стен — 150 мм", "section": "insulation", "included": true, "sort": 31},
    {"option_id": "in3", "name": "Утепление пола и потолка — 150 мм", "section": "insulation", "included": true, "sort": 32},
    {"option_id": "in4", "name": "Утепление каркасных перегородок — 100 мм", "section": "insulation", "included": true, "sort": 33},
    {"option_id": "in5", "name": "Мембранные плёнки Finka Premium (гидро-, ветрозащита, пароизоляция)", "section": "insulation", "included": true, "sort": 34},
    {"option_id": "in6", "name": "Утепление пола и потолка — 200 мм", "section": "insulation", "included": false, "sort": 35},
    {"option_id": "in7", "name": "Утепление пола и потолка — 250 мм (перекрёстное утепление)", "section": "insulation", "included": false, "sort": 36},
    {"option_id": "in8", "name": "Дополнительная ветро-, шумо- и теплоизоляция (Изоплат/Белтермо)", "section": "insulation", "included": false, "sort": 37},
    {"option_id": "in9", "name": "Утеплитель премиальный KNAUF", "section": "insulation", "included": false, "sort": 38, "status": "legacy"},
    {"option_id": "in10", "name": "Базовая система вентиляции (рекуператор + активная вытяжная)", "section": "insulation", "included": false, "sort": 39},
    {"option_id": "in11", "name": "Дополнительное утепление стен +50 мм (перекрёстное утепление)", "section": "insulation", "included": false, "sort": 40},
    {"option_id": "in12", "name": "Обшивка каркаса плитами OSB (укрепление, ветро- и шумозащита)", "section": "insulation", "included": false, "sort": 41},
    {"option_id": "ex1", "name": "Фасад с вентзазором 50×50 мм", "section": "exterior", "included": true, "sort": 42},
    {"option_id": "ex2", "name": "Обшивка стен фасада — имитация бруса 20×135 мм сорт АВ (горизонтально)", "section": "exterior", "included": true, "sort": 43},
    {"option_id": "ex3", "name": "Декоративные элементы — наличники, плинтусы, нащельник из сухой строганной доски", "section": "exterior", "included": true, "sort": 44},
    {"option_id": "ex4", "name": "Террасная доска — лиственница 28 мм (сорт Б)", "section": "exterior", "included": true, "sort": 45},
    {"option_id": "ex5", "name": "Обшивка стен — имитация бруса 20×185 мм сорт АВ (горизонтально)", "section": "exterior", "included": false, "sort": 46, "status": "legacy"},
    {"option_id": "ex6", "name": "Обшивка стен — имитация бруса 16×135 мм «Карельский профиль»", "section": "exterior", "included": false, "sort": 47, "status": "legacy"},
    {"option_id": "ex7", "name": "Обшивка стен — планкен из сосны 20×140 сорт АВ (горизонтально)", "section": "exterior", "included": false, "sort": 48, "status": "legacy"},
    {"option_id": "ex8", "name": "Обшивка стен — планкен из лиственницы 20×140 «Прима»", "section": "exterior", "included": false, "sort": 49, "status": "legacy"},
    {"option_id": "ex9", "name": "Обшивка стен — фиброцементный сайдинг (на выбор)", "section": "exterior", "included": false, "sort": 50, "status": "legacy"},
    {"option_id": "ex10", "name": "Обшивка стен фасада — имитация бруса 28×185 мм сорт АВ (горизонтально)", "section": "exterior", "included": false, "sort": 51, "status": "legacy"},
    {"option_id": "ex11", "name": "Террасная доска — ДПК UnoDeck Ultra (пустотелая)", "section": "exterior", "included": false, "sort": 52, "status": "formula"},
    {"option_id": "ex12", "name": "Обшивка стен — имитация рейки, профиль TFS (вертикально)", "section": "exterior", "included": false, "sort": 53, "status": "formula"},
    {"option_id": "ex13", "name": "Белтермо 25 мм (дополнительный слой тепло- и шумоизоляции)", "section": "exterior", "included": false, "sort": 54, "status": "formula"},
    {"option_id": "ex14", "name": "Белтермо 35 мм (дополнительный слой тепло- и шумоизоляции)", "section": "exterior", "included": false, "sort": 55, "status": "formula"},
    {"option_id": "ex15", "name": "Обшивка стен — имитация бруса 20×185 сорт АБ (горизонтально)", "section": "exterior", "included": false, "sort": 56, "status": "formula"},
    {"option_id": "ex16", "name": "Обшивка стен — имитация бруса 28×185 сорт АБ (горизонтально)", "section": "exterior", "included": false, "sort": 57, "status": "formula"},
    {"option_id": "ex17", "name": "Вертикальный монтаж имитации бруса (толщина по спецификации)", "section": "exterior", "included": false, "sort": 58, "status": "formula"},
    {"option_id": "ex18", "name": "Обшивка стен — планкен из сосны 140 мм сорт АБ (горизонтально)", "section": "exterior", "included": false, "sort": 59, "status": "formula"},
    {"option_id": "ex19", "name": "Обшивка стен — планкен из сосны 140 мм сорт А (горизонтально)", "section": "exterior", "included": false, "sort": 60, "status": "formula"},
    {"option_id": "ex20", "name": "Обшивка стен — планкен из сосны 140 мм сорт АБ (вертикально)", "section": "exterior", "included": false, "sort": 61, "status": "formula"},
    {"option_id": "ex21", "name": "Обшивка стен — планкен из сосны 140 мм сорт А (вертикально)", "section": "exterior", "included": false, "sort": 62, "status": "formula"},
    {"option_id": "ex22", "name": "Обшивка стен — планкен из лиственницы 140 мм сорт АБ (горизонтально)", "section": "exterior", "included": false, "sort": 63, "status": "formula"},
    {"option_id": "ex23", "name": "Обшивка стен — планкен из лиственницы 140 мм сорт А (горизонтально)", "section": "exterior", "included": false, "sort": 64, "status": "formula"},
    {"option_id": "ex24", "name": "Обшивка стен — планкен из лиственницы 140 мм сорт экстра (горизонтально)", "section": "exterior", "included": false, "sort": 65, "status": "formula"},
    {"option_id": "ex25", "name": "Обшивка стен — планкен из лиственницы 140 мм сорт АБ (вертикально)", "section": "exterior", "included": false, "sort": 66, "status": "formula"},
    {"option_id": "ex26", "name": "Обшивка стен — планкен из лиственницы 140 мм сорт А (вертикально)", "section": "exterior", "included": false, "sort": 67, "status": "formula"},
    {"option_id": "ex27", "name": "Обшивка стен — планкен из лиственницы 140 мм сорт экстра (вертикально)", "section": "exterior", "included": false, "sort": 68, "status": "formula"},
    {"option_id": "ex28", "name": "Обшивка стен — скандинавская доска АБ, 20×185 (поднятый ворс)", "section": "exterior", "included": false, "sort": 69, "status": "formula"},
    {"option_id": "ex29", "name": "Обшивка стен — профлист 0,5 мм глянец", "section": "exterior", "included": false, "sort": 70, "status": "formula"},
    {"option_id": "ex30", "name": "Обшивка стен — кликфальц 0,5 мм глянец", "section": "exterior", "included": false, "sort": 71, "status": "formula"},
    {"option_id": "ex31", "name": "Обшивка стен — БЕТЭКО Вудстон ёлочкой", "section": "exterior", "included": false, "sort": 72, "status": "formula"},
    {"option_id": "ex32", "name": "Обшивка стен — БЕТЭКО Вудстон клик (шип-паз)", "section": "exterior", "included": false, "sort": 73, "status": "formula"},
    {"option_id": "ex33", "name": "Обшивка стен — фиброцемент Каньон", "section": "exterior", "included": false, "sort": 74, "status": "formula"},
    {"option_id": "ex34", "name": "Обшивка стен — штукатурка фасада (на ЦСП)", "section": "exterior", "included": false, "sort": 75, "status": "formula"},
    {"option_id": "w1", "name": "Пластиковые окна Veka WHS 72, 5 камер (с фурнитурой Internika)", "section": "windows", "included": true, "sort": 76},
    {"option_id": "w2", "name": "Двойной стеклопакет с белым профилем, без ламинации", "section": "windows", "included": true, "sort": 77},
    {"option_id": "w3", "name": "Установка стеклопакета по центру каркаса", "section": "windows", "included": true, "sort": 78},
    {"option_id": "w4", "name": "Пластиковые подоконники", "section": "windows", "included": true, "sort": 79},
    {"option_id": "w5", "name": "Входная дверь — металлическая с терморазрывом 900×2000 мм", "section": "windows", "included": true, "sort": 80},
    {"option_id": "w6", "name": "Установка и регулировка базовых окон и дверей", "section": "windows", "included": true, "sort": 81},
    {"option_id": "w7", "name": "Окно в парном отделении — деревянное из липы 500×500 мм", "section": "windows", "included": true, "sort": 82},
    {"option_id": "w8", "name": "Пластиковые окна Veka softline 70, 5 камер, класс стенок А (с фурнитурой Internika)", "section": "windows", "included": false, "sort": 83},
    {"option_id": "w9", "name": "Пластиковые окна Veka softline 82 MD, 7 камер, 3 контура утепления (с фурнитурой Internika)", "section": "windows", "included": false, "sort": 84},
    {"option_id": "w10", "name": "Двойной стеклопакет с ламинацией снаружи (цвет на выбор)", "section": "windows", "included": false, "sort": 85},
    {"option_id": "w11", "name": "Двойной стеклопакет с ламинацией снаружи и внутри (цвет на выбор)", "section": "windows", "included": false, "sort": 86},
    {"option_id": "w12", "name": "Штульповые двери (открывание наружу, с замком)", "section": "windows", "included": false, "sort": 87},
    {"option_id": "w13", "name": "Алюминиевые окна Alumark S70 (индивидуальная комплектация)", "section": "windows", "included": false, "sort": 88},
    {"option_id": "w14", "name": "Входная дверь — стеклянная ПВХ Veka", "section": "windows", "included": false, "sort": 89},
    {"option_id": "w15", "name": "Межкомнатные двери — МДФ (доборы, наличники, ручки), за 1 дверь", "section": "windows", "included": false, "sort": 90},
    {"option_id": "w16", "name": "Энергосберегающие стёкла ClimaGuard (напыление/плёнка)", "section": "windows", "included": false, "sort": 91},
    {"option_id": "r1", "name": "Металлочерепица GrandLine 0,5 мм глянцевая (цвет на выбор)", "section": "roof", "included": true, "sort": 92},
    {"option_id": "r2", "name": "Подшив свесов кровли — сухая строганная доска с зазором 5–8 мм", "section": "roof", "included": true, "sort": 93},
    {"option_id": "r3", "name": "Карнизная, ветровая планки из металла (в цвет кровли)", "section": "roof", "included": true, "sort": 94},
    {"option_id": "r5", "name": "Кровельное покрытие — мягкая черепица Шинглас Кантри", "section": "roof", "included": false, "sort": 95, "status": "legacy"},
    {"option_id": "r6", "name": "Водосточная система (пластик)", "section": "roof", "included": false, "sort": 96},
    {"option_id": "r7", "name": "Водосточная система (металл)", "section": "roof", "included": false, "sort": 97},
    {"option_id": "r8", "name": "Снегозадержатели", "section": "roof", "included": false, "sort": 98},
    {"option_id": "r9", "name": "Материал кровельного покрытия — кликфальц 0,5 мм, глянец (матовый — за доплату)", "section": "roof", "included": false, "sort": 99, "status": "legacy"},
    {"option_id": "r10", "name": "Снегозадержатели трубчатые", "section": "roof", "included": false, "sort": 100, "status": "legacy"},
    {"option_id": "r11", "name": "Снегозадержатели-скоба (шинглас, ЦПЧ)", "section": "roof", "included": false, "sort": 101, "status": "legacy"},
    {"option_id": "r12", "name": "Водосточная система пластик", "section": "roof", "included": false, "sort": 102, "status": "legacy"},
    {"option_id": "r13", "name": "Водосточная система металл", "section": "roof", "included": false, "sort": 103, "status": "legacy"},
    {"option_id": "r14", "name": "Замена водосточки пластик на металл", "section": "roof", "included": false, "sort": 104, "status": "legacy"},
    {"option_id": "r15", "name": "Замена плоской наплавляемой кровли на ПВХ", "section": "roof", "included": false, "sort": 105, "status": "formula"},
    {"option_id": "r16", "name": "Материал кровельного покрытия — Шинглас Кантри", "section": "roof", "included": false, "sort": 106, "status": "formula"},
    {"option_id": "r17", "name": "Материал кровельного покрытия — наплавляемая ТехноНИКОЛЬ", "section": "roof", "included": false, "sort": 107, "status": "formula"},
    {"option_id": "r18", "name": "Материал кровельного покрытия — профлист, глянец (матовый — за доплату)", "section": "roof", "included": false, "sort": 108, "status": "formula"},
    {"option_id": "r19", "name": "Материал кровельного покрытия — кликфальц 0,5 глянец (матовый — за доплату)", "section": "roof", "included": false, "sort": 109, "status": "formula"},
    {"option_id": "r20", "name": "Материал кровельного покрытия — двойной стоячий фальц, глянец (матовый — за доплату)", "section": "roof", "included": false, "sort": 110, "status": "formula"},
    {"option_id": "r21", "name": "Материал кровельного покрытия — ЦПЧ Braas", "section": "roof", "included": false, "sort": 111, "status": "formula"},
    {"option_id": "r22", "name": "Замена профлиста на фальц", "section": "roof", "included": false, "sort": 112, "status": "formula"},
    {"option_id": "r23", "name": "Кровельный вентиляционный выход с колпаком Flow Vilpe (1 шт.)", "section": "roof", "included": false, "sort": 113, "status": "formula"},
    {"option_id": "r24", "name": "Вальмовая кровля", "section": "roof", "included": false, "sort": 114},
    {"option_id": "p1", "name": "Подбор цвета и типа лакокрасочных материалов", "section": "paint", "included": true, "sort": 115},
    {"option_id": "p2", "name": "Обработка деревянного фасада и свесов укрывной краской Tikkurila или аналоги в 2 слоя", "section": "paint", "included": false, "sort": 116, "status": "legacy"},
    {"option_id": "p3", "name": "Обработка наличников и углов другим цветом — укрывная краска Tikkurila или аналоги в 2 слоя", "section": "paint", "included": false, "sort": 117, "status": "legacy"},
    {"option_id": "p4", "name": "Обработка фасада и свесов маслом Osmo или аналоги в 2 слоя", "section": "paint", "included": false, "sort": 118, "status": "legacy"},
    {"option_id": "p5", "name": "Обработка стен и потолка внутри укрывной краской Tikkurila или аналоги в 2 слоя", "section": "paint", "included": false, "sort": 119, "status": "legacy"},
    {"option_id": "p6", "name": "Обработка стен и потолка внутри маслом Osmo или аналоги в 2 слоя", "section": "paint", "included": false, "sort": 120, "status": "legacy"},
    {"option_id": "p7", "name": "Покраска террасной доски маслом G-Nature", "section": "paint", "included": false, "sort": 121, "status": "legacy"},
    {"option_id": "p8", "name": "Обработка парного отделения защитным воском", "section": "paint", "included": false, "sort": 122, "status": "legacy"},
    {"option_id": "p9", "name": "Покраска деревянного пола специальным маслом", "section": "paint", "included": false, "sort": 123, "status": "legacy"},
    {"option_id": "p10", "name": "Покраска террасы в 2 слоя маслом G-Nature (за 1 м²)", "section": "paint", "included": false, "sort": 124, "status": "legacy"},
    {"option_id": "p11", "name": "Заводская покраска фасада укрывной краской, включая декор-элементы (Sikkens, Zobel)", "section": "paint", "included": false, "sort": 125, "status": "legacy"},
    {"option_id": "p12", "name": "Заводская покраска фасада маслом, включая декор-элементы (Sikkens, Zobel)", "section": "paint", "included": false, "sort": 126, "status": "legacy"},
    {"option_id": "p15", "name": "Заводская покраска снаружи (укрывная краска Sikkens, Zobel или аналоги)", "section": "paint", "included": false, "sort": 127, "status": "formula"},
    {"option_id": "p16", "name": "Заводская покраска снаружи маслом (Osmo или аналоги)", "section": "paint", "included": false, "sort": 128, "status": "formula"},
    {"option_id": "p13", "name": "Покраска снаружи (укрывная краска Sikkens, Zobel или аналоги)", "section": "paint", "included": false, "sort": 129, "status": "formula"},
    {"option_id": "p14", "name": "Покраска снаружи маслом со шлифовкой (Osmo или аналоги)", "section": "paint", "included": false, "sort": 130, "status": "formula"},
    {"option_id": "p17", "name": "Покраска клеёного бруса со шлифовкой (укрывная краска Sikkens, Zobel или аналоги)", "section": "paint", "included": false, "sort": 131, "status": "formula"},
    {"option_id": "p18", "name": "Покраска террасной доски маслом G-Nature", "section": "paint", "included": false, "sort": 132, "status": "formula"},
    {"option_id": "i1", "name": "Чистовой пол — доска шпунтованная 27 мм (жилая зона)", "section": "interior", "included": true, "sort": 133},
    {"option_id": "i2", "name": "Обшивка стен — имитация бруса 16×135 мм (сорт АВ)", "section": "interior", "included": true, "sort": 134},
    {"option_id": "i3", "name": "Обшивка потолка — вагонка штиль 16×120 мм (сорт АВ)", "section": "interior", "included": true, "sort": 135},
    {"option_id": "i4", "name": "Дополнительный венец обвязки", "section": "interior", "included": false, "sort": 136},
    {"option_id": "i5", "name": "Материал чистового пола — доска шпунтованная 36 мм", "section": "interior", "included": false, "sort": 137},
    {"option_id": "i6", "name": "Обшивка стен — имитация бруса 16×135 мм «Карельский профиль»", "section": "interior", "included": false, "sort": 138},
    {"option_id": "i7", "name": "Подготовка пола и укладка ламината эконом-класса", "section": "interior", "included": false, "sort": 139},
    {"option_id": "i8", "name": "Подготовка пола и укладка плитки (материал заказчика)", "section": "interior", "included": false, "sort": 140},
    {"option_id": "i9", "name": "Обшивка стен — планкен из лиственницы 20×120 мм (горизонтально)", "section": "interior", "included": false, "sort": 141, "status": "legacy"},
    {"option_id": "i10", "name": "Внутренняя обшивка — два слоя гипсокартона KNAUF 12,5 мм", "section": "interior", "included": false, "sort": 142},
    {"option_id": "i11", "name": "Обшивка санузла ОСБ+ГВЛВ под укладку плитки (пол и стены)", "section": "interior", "included": false, "sort": 143},
    {"option_id": "i12", "name": "Обшивка моечного отделения ОСБ+ГВЛВ под укладку плитки (пол и стены)", "section": "interior", "included": false, "sort": 144},
    {"option_id": "s1", "name": "Теплоизоляция парного отделения — фольгированный материал", "section": "steam", "included": true, "sort": 145},
    {"option_id": "s2", "name": "Вагонка из осины вертикально (сорт АБ), полки из осины", "section": "steam", "included": true, "sort": 146},
    {"option_id": "s3", "name": "Чистовой пол — доска шпунтованная 27 мм (парная)", "section": "steam", "included": true, "sort": 147},
    {"option_id": "s4", "name": "Лежаки в парном отделении — осиновый полок (1–2 уровня)", "section": "steam", "included": true, "sort": 148},
    {"option_id": "s5", "name": "Тип плафона на выбор заказчика — 2 шт.", "section": "steam", "included": true, "sort": 149},
    {"option_id": "s6", "name": "Фасад за печью и в комнате отдыха из минерита", "section": "steam", "included": true, "sort": 150},
    {"option_id": "s7", "name": "Дверь в парную — стеклянная жаропрочная с фурнитурой 700×1900 мм", "section": "steam", "included": true, "sort": 151},
    {"option_id": "s8", "name": "Высота пол/потолок в парном отделении — 2200 мм", "section": "steam", "included": true, "sort": 152},
    {"option_id": "s9", "name": "Увеличение парного до 2500×2500 мм (осина, сорт АБ)", "section": "steam", "included": false, "sort": 153},
    {"option_id": "s10", "name": "Увеличение парного до 2500×3000 мм (осина, сорт АБ)", "section": "steam", "included": false, "sort": 154},
    {"option_id": "s11", "name": "Увеличение парного до 3000×3000 (осина, сорт АБ)", "section": "steam", "included": false, "sort": 155},
    {"option_id": "s12", "name": "Отделка парного — вагонка из липы (экстра) + полок из липы 2500×2000 мм", "section": "steam", "included": false, "sort": 156},
    {"option_id": "s13", "name": "Отделка парного — вагонка из липы (экстра) + полок из липы 2500×2500 мм", "section": "steam", "included": false, "sort": 157},
    {"option_id": "s14", "name": "Отделка парного — вагонка из липы (экстра) + полок из липы 2500×3000 мм", "section": "steam", "included": false, "sort": 158},
    {"option_id": "s15", "name": "Отделка парного — вагонка из липы (экстра) + полок из липы 3000×3000", "section": "steam", "included": false, "sort": 159},
    {"option_id": "s16", "name": "Материал полков — африканский абаш", "section": "steam", "included": false, "sort": 160},
    {"option_id": "s17", "name": "Парящий полок", "section": "steam", "included": false, "sort": 161},
    {"option_id": "s18", "name": "Ограждение для печи из липы", "section": "steam", "included": false, "sort": 162},
    {"option_id": "s19", "name": "Подсветка полков стандарт", "section": "steam", "included": false, "sort": 163},
    {"option_id": "s20", "name": "Подсветка полков LED с пультом", "section": "steam", "included": false, "sort": 164},
    {"option_id": "s21", "name": "Подготовка пола под укладку плитки (парная)", "section": "steam", "included": false, "sort": 165},
    {"option_id": "s22", "name": "Деревянный пол из палубной доски лиственница (парная)", "section": "steam", "included": false, "sort": 166},
    {"option_id": "s23", "name": "Панно из Гималайской соли с подсветкой 300×1500 мм", "section": "steam", "included": false, "sort": 167},
    {"option_id": "s24", "name": "Спилы можжевельника с подсветкой 1000×1000 мм", "section": "steam", "included": false, "sort": 168},
    {"option_id": "s25", "name": "Спилы можжевельника без подсветки 1000×1000 мм", "section": "steam", "included": false, "sort": 169},
    {"option_id": "s26", "name": "Спинки (липа)", "section": "steam", "included": false, "sort": 170},
    {"option_id": "s27", "name": "Подсветка потолка", "section": "steam", "included": false, "sort": 171},
    {"option_id": "s28", "name": "Комбинированные полки (с термолипой), включая спинки", "section": "steam", "included": false, "sort": 172},
    {"option_id": "s29", "name": "Приточно-вытяжная вентиляция в парном отделении с клапаном", "section": "steam", "included": false, "sort": 173},
    {"option_id": "s30", "name": "Пароиспаритель (ПИФ)", "section": "steam", "included": false, "sort": 174},
    {"option_id": "s31", "name": "Покрытие полков и стен маслом для саун", "section": "steam", "included": false, "sort": 175},
    {"option_id": "s32", "name": "Талькохлорит «рваный камень» (фасад за печкой)", "section": "steam", "included": false, "sort": 176},
    {"option_id": "s33", "name": "Деревянный настил (если есть плитка)", "section": "steam", "included": false, "sort": 177},
    {"option_id": "s34", "name": "Сборка премиальной парной (специальная бригада, LED-монтаж)", "section": "steam", "included": false, "sort": 178},
    {"option_id": "st1", "name": "Установка дровяной печи — топка из комнаты отдыха (проходной узел из минерита)", "section": "stove", "included": false, "sort": 179},
    {"option_id": "st6", "name": "Вывод дымохода в крышу (1 этаж, нержавейка, сэндвич, зонт с искрогасителем)", "section": "stove", "included": false, "sort": 180},
    {"option_id": "st12", "name": "Притопочный лист из нержавеющей стали 600×400 мм", "section": "stove", "included": false, "sort": 181},
    {"option_id": "st15", "name": "Пожаростойкий портал из минерита (для последующей облицовки)", "section": "stove", "included": false, "sort": 182},
    {"option_id": "st20", "name": "Камень для печи «Жадеит» 80 кг", "section": "stove", "included": false, "sort": 183},
    {"option_id": "st2", "name": "Установка дровяной печи — топка из парного отделения (проходной узел из минерита)", "section": "stove", "included": false, "sort": 184},
    {"option_id": "st3", "name": "Угловая печь для сауны Harvia Glow Corner TRC 90, 9 кВт", "section": "stove", "included": false, "sort": 185},
    {"option_id": "st4", "name": "Подвесная электрическая печь Sawo Cumulus CML-60NB-P 6 кВт", "section": "stove", "included": false, "sort": 186},
    {"option_id": "st5", "name": "Подвесная электрическая печь Sawo Cumulus CML-60Ni2-P с выносным пультом (талькохлорит)", "section": "stove", "included": false, "sort": 187, "status": "legacy"},
    {"option_id": "st35", "name": "Монтаж электрической печи", "section": "stove", "included": false, "sort": 188},
    {"option_id": "st7", "name": "Вывод дымохода в крышу (2 этажа)", "section": "stove", "included": false, "sort": 189},
    {"option_id": "st8", "name": "Вывод дымохода в стену (1 этаж)", "section": "stove", "included": false, "sort": 190},
    {"option_id": "st9", "name": "Вывод дымохода в стену (2 этажа)", "section": "stove", "included": false, "sort": 191},
    {"option_id": "st10", "name": "Навесной бак на трубу 50 л с краном", "section": "stove", "included": false, "sort": 192, "status": "legacy"},
    {"option_id": "st11", "name": "Выносной бак 50 л с регистром на печь и трубками", "section": "stove", "included": false, "sort": 193, "status": "legacy"},
    {"option_id": "st13", "name": "Фирменный защитный экран Термофор (портал для печи)", "section": "stove", "included": false, "sort": 194},
    {"option_id": "st14", "name": "Кладка портала из специального термостойкого кирпича", "section": "stove", "included": false, "sort": 195},
    {"option_id": "st16", "name": "Печь-каменка Ферингер Малютка до 18 м³", "section": "stove", "included": false, "sort": 196},
    {"option_id": "st17", "name": "Печь Ферингер Квадра до 25 м³", "section": "stove", "included": false, "sort": 197},
    {"option_id": "st18", "name": "Печь Ферингер Оптима до 28 м³", "section": "stove", "included": false, "sort": 198},
    {"option_id": "st19", "name": "Печь Ферингер Уют-18 до 18 м³ (топка внутри парной)", "section": "stove", "included": false, "sort": 199},
    {"option_id": "st21", "name": "Печь Ферингер Малютка «Змеевик Наборный» до 18 м³", "section": "stove", "included": false, "sort": 200},
    {"option_id": "st22", "name": "Печь Ферингер Оптима «Змеевик Наборный» до 28 м³", "section": "stove", "included": false, "sort": 201},
    {"option_id": "st23", "name": "Печь Ферингер Малютка «Окаменевшее дерево» до 18 м³", "section": "stove", "included": false, "sort": 202},
    {"option_id": "st24", "name": "Печь Ферингер Оптима «Окаменевшее дерево» до 23 м³", "section": "stove", "included": false, "sort": 203},
    {"option_id": "st25", "name": "Дровяная банная печь Grill’D Cometa Vega 240 Long Max (до 24 кубов)", "section": "stove", "included": false, "sort": 204},
    {"option_id": "st34", "name": "Печь Изистим Ялта в камне до 25 м³", "section": "stove", "included": false, "sort": 205},
    {"option_id": "st26", "name": "Дымоход Grill’D черный премиальный с увеличенной теплоизоляцией", "section": "stove", "included": false, "sort": 206},
    {"option_id": "st27", "name": "Дымоход Ферингер Экономайзер в металле (кожух)", "section": "stove", "included": false, "sort": 207},
    {"option_id": "st28", "name": "Дымоход Экономайзер Ламели (в ассортименте)", "section": "stove", "included": false, "sort": 208},
    {"option_id": "st29", "name": "Кассеты для печей Ферингер с системой подачи воды — 2 кассеты", "section": "stove", "included": false, "sort": 209},
    {"option_id": "st30", "name": "Кассеты для печей Ферингер — 3 кассеты", "section": "stove", "included": false, "sort": 210},
    {"option_id": "st31", "name": "Пароиспаритель Ферингера (эффект русской бани)", "section": "stove", "included": false, "sort": 211},
    {"option_id": "st32", "name": "Портал для печи Ферингер из камня (змеевик)", "section": "stove", "included": false, "sort": 212},
    {"option_id": "st33", "name": "Портал для печи Ферингер из камня (окаменевшее дерево)", "section": "stove", "included": false, "sort": 213},
    {"option_id": "e1", "name": "Проектирование базового проекта (архитектурное решение + каркас + фундамент)", "section": "extra", "included": true, "sort": 214},
    {"option_id": "e2", "name": "Ступени на террасу или крыльцо — временные", "section": "extra", "included": true, "sort": 215},
    {"option_id": "e3", "name": "Логистика (до 100 км от МКАД)", "section": "extra", "included": true, "sort": 216},
    {"option_id": "e4", "name": "Разгрузка материалов (до 30 метров)", "section": "extra", "included": true, "sort": 217},
    {"option_id": "e5", "name": "Проживание бригады (постройка бытовки на участке)", "section": "extra", "included": false, "sort": 218},
    {"option_id": "e6", "name": "Аренда бытовки с доставкой и установкой на время строительства", "section": "extra", "included": false, "sort": 219},
    {"option_id": "e7", "name": "Аренда биотуалета с обслуживанием на время строительства", "section": "extra", "included": false, "sort": 220},
    {"option_id": "e8", "name": "Бензиновый электрогенератор на время строительства (1 месяц)", "section": "extra", "included": false, "sort": 221},
    {"option_id": "e9", "name": "Сборка лесов (вышка-тура)", "section": "extra", "included": false, "sort": 222},
    {"option_id": "e10", "name": "Устройство открытой террасы 12 м²", "section": "extra", "included": false, "sort": 223},
    {"option_id": "e12", "name": "Вывоз мусора (1 контейнер с грузчиками)", "section": "extra", "included": false, "sort": 224, "price": 37000},
    {"option_id": "e11", "name": "Индивидуальное проектирование (полное архитектурное решение)", "section": "extra", "included": false, "sort": 225, "status": "legacy"},
    {"option_id": "eng1", "name": "Консультация по инженерным коммуникациям", "section": "engineering", "included": true, "sort": 226},
    {"option_id": "eng2", "name": "ПВУ с рекуперацией Zenit Heco V 350 E EPP (до 85 м²)", "section": "engineering", "included": false, "sort": 227, "status": "legacy"},
    {"option_id": "eng3", "name": "ПВУ с рекуперацией Zenit Heco V 550 E (до 150 м²)", "section": "engineering", "included": false, "sort": 228, "status": "legacy"},
    {"option_id": "eng4", "name": "ПВУ с рекуперацией Zenit Heco V 750 E (до 220 м²)", "section": "engineering", "included": false, "sort": 229, "status": "legacy"},
    {"option_id": "eng5", "name": "Охладитель к 350-й модели", "section": "engineering", "included": false, "sort": 230, "status": "legacy"},
    {"option_id": "eng6", "name": "Охладитель к 550-й модели", "section": "engineering", "included": false, "sort": 231, "status": "legacy"},
    {"option_id": "eng7", "name": "Охладитель к 750-й модели", "section": "engineering", "included": false, "sort": 232, "status": "legacy"},
    {"option_id": "eng8", "name": "Увлажнитель к 350-й модели", "section": "engineering", "included": false, "sort": 233, "status": "legacy"},
    {"option_id": "eng9", "name": "Увлажнитель к 550-й модели", "section": "engineering", "included": false, "sort": 234, "status": "legacy"},
    {"option_id": "eng10", "name": "Увлажнитель к 750-й модели", "section": "engineering", "included": false, "sort": 235, "status": "legacy"},
    {"option_id": "eng11", "name": "Внутренние сантехнические работы — ванная/санузел (КАН + ГВС + ХВС)", "section": "engineering", "included": false, "sort": 236},
    {"option_id": "eng12", "name": "Внутренние сантехнические работы — кухня", "section": "engineering", "included": false, "sort": 237, "status": "legacy"},
    {"option_id": "eng13", "name": "Установка сантехники заказчика (унитаз, раковина, душ)", "section": "engineering", "included": false, "sort": 238, "status": "legacy"},
    {"option_id": "eng14", "name": "Септик 5-ка (септик + сбросной колодец + трасса 5 м + монтаж)", "section": "engineering", "included": false, "sort": 239},
    {"option_id": "eng15", "name": "Скрытые электротехнические работы (щит, розетки, выключатели, заземление)", "section": "engineering", "included": false, "sort": 240},
    {"option_id": "eng16", "name": "Наружные электротехнические работы (ретро-кабель с керамическими изоляторами)", "section": "engineering", "included": false, "sort": 241, "status": "legacy"},
    {"option_id": "eng17", "name": "Установка светильников до 10 шт.", "section": "engineering", "included": false, "sort": 242},
    {"option_id": "eng18", "name": "Тёплый пол электрический (включая регулятор) — от 2700 ₽/м²", "section": "engineering", "included": false, "sort": 243, "status": "legacy"},
    {"option_id": "eng19", "name": "Котёл Protherm Скат 6 кВт (отопление до 60 м²)", "section": "engineering", "included": false, "sort": 244, "status": "legacy"},
    {"option_id": "eng20", "name": "Котёл Protherm Скат 9 кВт (отопление до 90 м²)", "section": "engineering", "included": false, "sort": 245, "status": "legacy"},
    {"option_id": "eng21", "name": "Котёл Protherm Скат 12 кВт (отопление до 120 м²)", "section": "engineering", "included": false, "sort": 246, "status": "legacy"}
  ];
  window.__RPC = window.__RPC || {};
  // События пресета — как функция базы preset_events: все строки с кодом
  // пресета, свежие сверху, с именем автора. Проба может подменить её своей.
  if (!window.__RPC.preset_events) window.__RPC.preset_events = function (арг) {
    var т = window.__ТАБЛИЦЫ || {}, имена = {};
    (т.profiles || []).forEach(function (п) { имена[п.id] = [п.first_name, п.last_name].filter(Boolean).join(' ') || null; });
    return (т.events || []).filter(function (е) { return е.details && String(е.details.presetCode) === String(арг.p_code); })
      .map(function (е) { return Object.assign({}, е, { user_name: имена[е.user_id] || null }); })
      .sort(function (а, б) { return String(б.created_at).localeCompare(String(а.created_at)); });
  };

  /* Ответ базы — всегда копия, прошедшая через JSON, как поле jsonb.
     Прежняя заглушка отдавала тот же объект, что положила страница, и проба
     не видела обратной дороги вовсе: на живой базе снимок ссылки возвращается
     переупорядоченным, и сравнение «лист против строки» считало расчёт
     разошедшимся сразу после записи (Константин 23.09.2026). Теперь заглушка
     ходит тем же путём. Ключи вдобавок перемешиваем: jsonb своего порядка не
     обещает, и проба должна падать на сравнении, которое от него зависит. */
  function черезБазу(з) {
    if (Array.isArray(з)) return з.map(черезБазу);
    if (з && typeof з === 'object') {
      var и = {}, ключи = Object.keys(з).slice().reverse();
      ключи.forEach(function (к) { и[к] = черезБазу(з[к]); });
      return и;
    }
    return з;
  }
  function ответ(строки) {
    var копия = строки == null ? строки : JSON.parse(JSON.stringify(черезБазу(строки)));
    return { data: копия, error: null, count: копия ? копия.length : 0 };
  }

  /* Отборы выполняются по-настоящему. Заглушка, отдающая всю таблицу на любой
     запрос, показывает пробе не то, что увидит страница: строка по чужому
     коду попала бы в счёт заходов, а уведомления собрались бы по чужим
     ссылкам. Ровно на этом проба и молчала бы. */
  /* Строки каркаса таблиц пробы ложатся поверх полного списка: название,
     раздел и порядок — из списка, цена, формула и статус — у строки пробы. */
  /* Проба правит строки каркаса, как правят их в базе: __ПРАВКИ_КАРКАСА —
     { id: { name, sort, included, … } }; __БЕЗ_СПИСКА_КАРКАСА — база не
     отдала ни одной строки каркаса. */
  function сОпциямиКаркаса(строки) {
    if (window.__БЕЗ_СПИСКА_КАРКАСА) return строки.filter(function (р) { return р.product !== 'frame'; });
    var правки = window.__ПРАВКИ_КАРКАСА || {};
    var свои = {};
    строки.forEach(function (р) { if (р.product === 'frame') свои[р.option_id] = р; });
    var каркас = ОПЦИИ_КАРКАСА.map(function (о) {
      var р = свои[о.option_id], н = Object.assign({ product: 'frame', price: null, formula: null, status: null }, о);
      if (р) ['price', 'formula', 'status'].forEach(function (к) { if (р[к] !== undefined) н[к] = р[к]; });
      return Object.assign(н, правки[о.option_id] || {});
    });
    return строки.filter(function (р) { return р.product !== 'frame'; }).concat(каркас);
  }
  function запрос(таблица) {
    var строки = (window.__ТАБЛИЦЫ[таблица] || []).slice();
    if (таблица === 'pricing_options') строки = сОпциямиКаркаса(строки);
    var один = false;
    var о = {};
    ['select', 'like', 'ilike', 'not', 'or', 'filter',
     'contains', 'overlaps', 'match', 'abortSignal'].forEach(function (и) {
      о[и] = function () { return о; };
    });
    /* `range` был пустышкой и отдавал всю таблицу на любую страницу. Постраничный
       обход на такой заглушке не проверить вовсе: цикл «пока страница полная»
       никогда не кончается, а ошибка в страницах — что вторая страница повторяет
       первую или теряется — проходит незамеченной. Теперь режет по-настоящему. */
    о.range = function (от, до) {
      строки = строки.slice(Number(от) || 0, (Number(до) || 0) + 1);
      return о;
    };
    /* Сравнения по датам сравнивали как есть: строка с числом сходились по
       алфавиту, и `gte('created_at', …)` пропускал что попало. Даты сводим к
       числу, остальное сравниваем как было. */
    function вес(з) {
      if (з instanceof Date) return з.getTime();
      var д = (typeof з === 'string') && /^\d{4}-\d{2}-\d{2}/.test(з) ? Date.parse(з) : NaN;
      return isNaN(д) ? з : д;
    }
    [['gt', function (a, b) { return a > b; }],
     ['gte', function (a, b) { return a >= b; }],
     ['lt', function (a, b) { return a < b; }],
     ['lte', function (a, b) { return a <= b; }]].forEach(function (п) {
      о[п[0]] = function (поле, знач) {
        строки = строки.filter(function (р) { return п[1](вес(р[поле]), вес(знач)); });
        return о;
      };
    });
    /* `insert` и `upsert` были заглушками и ничего не записывали. Проба,
       которая смотрит, что строка появилась в базе, на такой заглушке зеленела
       бы при полностью сломанной записи: возвращается-то «ошибки нет». Теперь
       строки кладутся в те же таблицы, откуда читаются, — как `update` и
       `delete`, исправленные раньше по тому же поводу. */
    var добавить = null, ключСлияния = null;
    о.insert = function (значения) {
      добавить = Array.isArray(значения) ? значения.slice() : [значения];
      return о;
    };
    /* Без onConflict база сливает по первичному ключу — у наших таблиц это id.
       Заглушка дописывала вторую строку, и правка ручного проекта выглядела
       незаписанной: первая строка оставалась прежней (проба формы кровли,
       17.10.2026). Строка без id сливаться не может — она добавляется. */
    о.upsert = function (значения, наст) {
      добавить = Array.isArray(значения) ? значения.slice() : [значения];
      ключСлияния = (наст && наст.onConflict) ? String(наст.onConflict).split(',')[0].trim() : 'id';
      return о;
    };
    /* `update` и `delete` были заглушками и возвращали себя, ничего не меняя.
       Проба удаления пресета на такой заглушке показывала бы зелёное при любой
       ошибке: строка не менялась, и метку удаления искать было негде. Теперь
       правка запоминается и применяется к тем строкам, что остались после
       фильтров, — порядок в цепочке именно такой: `update(...).eq(...)`. */
    var правка = null, стирать = false;
    о.update = function (значения) { правка = значения || {}; return о; };
    о.delete = function () { стирать = true; return о; };
    /* Ключи, по которым таблица в базе объявлена уникальной. Без этого
       обычная вставка на занятый номер молча клала вторую строку, и проба
       столкновения кодов зеленела бы при сломанной перевыдаче: в жизни база
       отвечает 23505, а заглушка — «ошибки нет». */
    var УНИКАЛЬНО = { preset_links: 'short_code', client_links: 'code', presets: 'id',
                      app_docs: null };
    var сбой = null;
    function применить() {
      if (добавить) {
        var все = window.__ТАБЛИЦЫ[таблица] || (window.__ТАБЛИЦЫ[таблица] = []);
        var уник = УНИКАЛЬНО[таблица];
        if (уник && !ключСлияния) {
          var занят = добавить.filter(function (новая) {
            return все.some(function (р) { return String(р[уник]) === String(новая[уник]); });
          });
          if (занят.length) {
            сбой = { code: '23505', message: 'duplicate key value violates unique constraint "'
                     + таблица + '_pkey"' };
            добавить = null;
            строки = [];
            return;
          }
        }
        добавить.forEach(function (новая) {
          var и = -1;
          if (ключСлияния && новая[ключСлияния] !== undefined) {
            и = все.findIndex(function (р) {
              return String(р[ключСлияния]) === String(новая[ключСлияния]);
            });
          }
          if (и >= 0) { все[и] = Object.assign({}, все[и], новая); } else { все.push(новая); }
        });
        строки = добавить.slice();
      }
      if (правка) {
        строки.forEach(function (р) {
          Object.keys(правка).forEach(function (к) { р[к] = правка[к]; });
        });
      }
      if (стирать) {
        var все = window.__ТАБЛИЦЫ[таблица] || [];
        строки.forEach(function (р) {
          var и = все.indexOf(р);
          if (и >= 0) все.splice(и, 1);
        });
      }
    }
    /* Поле внутри jsonb — `details->>presetCode`: страница так отбирает
       действия одного пресета, и без разбора пути отбор отдавал бы пустоту. */
    function значение(р, поле) {
      var м = /^(\w+)->>(\w+)$/.exec(поле);
      if (!м) return р[поле];
      var в = (р[м[1]] || {})[м[2]];
      return в == null ? null : String(в);
    }
    var продукт = null;
    о.eq = function (поле, знач) {
      if (поле === 'product') продукт = знач;
      строки = строки.filter(function (р) { return String(значение(р, поле)) === String(знач); });
      return о;
    };
    о.neq = function (поле, знач) {
      строки = строки.filter(function (р) { return String(р[поле]) !== String(знач); });
      return о;
    };
    /* `is` заглушкой не был, а страница спрашивает им живые пресеты
       (`.is('deleted_at', null)`): пропущенный фильтр отдавал бы удалённые
       строки, и проба показывала бы не то, что увидит человек. */
    о.is = function (поле, знач) {
      строки = строки.filter(function (р) {
        var в = р[поле];
        if (знач === null) return в === null || в === undefined;
        return в === знач;
      });
      return о;
    };
    о.in = function (поле, список) {
      строки = строки.filter(function (р) { return (список || []).map(String).indexOf(String(р[поле])) >= 0; });
      return о;
    };
    о.order = function (поле, наст) {
      var вверх = !(наст && наст.ascending === false);
      строки.sort(function (a, b) {
        var x = a[поле], y = b[поле];
        if (x === y) return 0;
        return (x > y ? 1 : -1) * (вверх ? 1 : -1);
      });
      return о;
    };
    о.limit = function (н) { строки = строки.slice(0, н); return о; };
    о.single = о.maybeSingle = function () { один = true; return о; };
    /* Задержка сети: `window.__ЗАДЕРЖКА` (мс) заставляет ответ приходить не
       мгновенно. Нужна пробе, которая меряет, что видно человеку ДО ответа
       базы, — на мгновенной заглушке «сразу» и «после ответа» неразличимы. */
    о.then = function (принять, отклонить) {
      применить();
      var р = один ? (строки[0] || null) : строки;
      var итог = сбой ? { data: null, error: сбой }
                      : (один ? { data: р, error: null } : ответ(строки));
      /* `__ЗАДЕРЖКА` может быть и функцией (таблица, технология) → мс: так
         проба делает медленной загрузку одной технологии и быстрой другой —
         гонку двух загрузок цен иначе не воспроизвести. */
      var ждать = typeof window.__ЗАДЕРЖКА === 'function'
        ? Number(window.__ЗАДЕРЖКА(таблица, продукт) || 0)
        : Number(window.__ЗАДЕРЖКА || 0);
      var обещание = ждать > 0
        ? new Promise(function (д) { setTimeout(function () { д(итог); }, ждать); })
        : Promise.resolve(итог);
      return обещание.then(принять, отклонить);
    };
    о.catch = function (ф) { return о.then(null, ф); };
    о.finally = function (ф) { return о.then(ф, ф); };
    return о;
  }

  /* Каналы запоминают, на что подписалась страница: проба чата шлёт по ним
     «новое сообщение» — как пришло бы от базы — и смотрит, что лента его
     показала. Прежний общий канал ничего не помнил. */
  window.__КАНАЛЫ = window.__КАНАЛЫ || [];
  function новыйКанал(имя) {
    var к = { имя: имя, слушатели: [], закрыт: false };
    к.on = function (вид, отбор, об) { к.слушатели.push({ вид: вид, отбор: отбор, об: об }); return к; };
    к.subscribe = function () { return к; };
    к.unsubscribe = function () { к.закрыт = true; return Promise.resolve('ok'); };
    window.__КАНАЛЫ.push(к);
    return к;
  }
  /* Загруженное в хранилище запоминается: проба смотрит путь и тип файла. */
  window.__ЗАГРУЖЕНО = window.__ЗАГРУЖЕНО || [];

  var клиент = {
    from: запрос,
    rpc: function (имя, арг) {
      var д = window.__RPC[имя];
      // Функция может вернуть обещание — так проба задерживает ответ базы.
      // Отказ базы — { __ошибка: 'текст' }: как raise exception в функции.
      return Promise.resolve(typeof д === 'function' ? д(арг) : (д === undefined ? null : д))
        .then(function (з) {
          if (з && typeof з === 'object' && з.__ошибка) return { data: null, error: { message: String(з.__ошибка) } };
          return { data: з, error: null };
        });
    },
    channel: function (имя) { return новыйКанал(имя); },
    removeChannel: function (к) { if (к) к.закрыт = true; return Promise.resolve('ok'); },
    storage: { from: function (корзина) { return {
      upload: function (путь, файл, наст) {
        window.__ЗАГРУЖЕНО.push({ корзина: корзина, путь: путь, тип: (наст && наст.contentType) || (файл && файл.type) || '', размер: файл && файл.size });
        if (typeof window.__СБОЙ_ЗАГРУЗКИ === 'string') return Promise.resolve({ data: null, error: { message: window.__СБОЙ_ЗАГРУЗКИ } });
        return Promise.resolve({ data: { path: путь }, error: null });
      },
      remove: function () { return Promise.resolve({ data: [], error: null }); },
      getPublicUrl: function (п) { return { data: { publicUrl: '/assets/logo-bmsk-dark.png' } }; },
      createSignedUrl: function (путь, срок, наст) { return Promise.resolve({ data: { signedUrl: '/assets/logo-bmsk-dark.png?p=' + encodeURIComponent(путь) + (наст && наст.download ? '&download=' + encodeURIComponent(наст.download) : '') }, error: null }); },
      createSignedUrls: function (пути) { return Promise.resolve({ data: (пути || []).map(function (п) { return { path: п, signedUrl: '/assets/logo-bmsk-dark.png?p=' + encodeURIComponent(п), error: null }; }), error: null }); },
    }; } },
    auth: {
      getSession: function () { return Promise.resolve({ data: { session: СЕССИЯ }, error: null }); },
      getUser: function () { return Promise.resolve({ data: { user: ПОЛЬЗОВАТЕЛЬ }, error: null }); },
      refreshSession: function () { return Promise.resolve({ data: { session: СЕССИЯ, user: ПОЛЬЗОВАТЕЛЬ }, error: null }); },
      setSession: function () { return Promise.resolve({ data: { session: СЕССИЯ, user: ПОЛЬЗОВАТЕЛЬ }, error: null }); },
      signInWithPassword: function () { return Promise.resolve({ data: { session: СЕССИЯ, user: ПОЛЬЗОВАТЕЛЬ }, error: null }); },
      signOut: function () { return Promise.resolve({ error: null }); },
      onAuthStateChange: function (об) {
        setTimeout(function () { try { об('SIGNED_IN', СЕССИЯ); } catch (e) {} }, 0);
        return { data: { subscription: { unsubscribe: function () {} } } };
      },
    },
  };
  window.supabase = { createClient: function () { return клиент; } };
})();
