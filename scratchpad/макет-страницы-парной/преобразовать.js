// Превращает живую страницу каркаса в страницу технологии «Парная».
// Разметку строк, разделов и карточек берёт у самого калькулятора — клонирует,
// чтобы вид совпадал один в один. Расчёт навешивает живой.js.
async () => {
  const $ = s => document.querySelector(s);
  const все = (s, к = document) => [...к.querySelectorAll(s)];

  // ── Шаблоны строк ──
  const строки = все('#optionSections .opt-item');
  const Т_БАЗА = строки.find(r => r.querySelector('.opt-included-row') && !r.querySelector('.opt-qty-stepper')).cloneNode(true);
  const Т_ЦЕНА = строки.find(r => r.querySelector('.opt-price') && !r.querySelector('.opt-qty-stepper') && !r.querySelector('input.manual-price-input, .manual-price-input')).cloneNode(true);
  const Т_ШАГИ = строки.find(r => r.querySelector('.opt-qty-stepper')).querySelector('.opt-qty-stepper').cloneNode(true);
  const Т_РАЗДЕЛ = $('#optionSections').children[0].cloneNode(true);
  const Т_ПРИМ = $('#optionSections .note-item').cloneNode(true);

  // ── Шапка и технология ──
  $('#techTitle').textContent = 'Парное отделение';
  $('#techSelectLabel').textContent = 'Парная';
  const тд = $('#techSelectDropdown');
  все('.custom-select-option', тд).forEach(о => о.classList.remove('selected'));
  const пар = все('.custom-select-option', тд)[1].cloneNode(true);
  пар.textContent = 'Парная'; пар.dataset.tech = 'steam'; пар.classList.add('selected');
  все('.custom-select-option', тд)[1].after(пар);

  // ── Левая карточка: «Парная в доме заказчика» ──
  const лев = $('.two-col > .card');
  const заг = лев.querySelector('.card-title'); заг.lastChild.textContent = 'Парная в доме заказчика';
  const поля = все(':scope > .field', лев);
  поля[0].remove();                                   // поиск
  поля[2].remove();                                   // толщина утепления
  $('#kbAreasWrap') && $('#kbAreasWrap').remove();
  $('#editProjectForm') && $('#editProjectForm').remove();
  все('button, div', лев).filter(е => /Добавить проект вручную/.test(е.textContent) && е.children.length < 4).forEach(е => е.remove());
  поля[1].querySelector('label').textContent = 'Тип помещения';
  $('#projectSelectLabel').textContent = 'Камень: кирпич, блок, бетон';
  $('#projectSelectBadge') && ($('#projectSelectBadge').innerHTML = '');
  $('#projectSelect') && $('#projectSelect').remove();
  const пд = $('#projectSelectDropdown'); пд.innerHTML = '';
  [['stone', 'Камень: кирпич, блок, бетон'], ['frame', 'Каркасный дом'], ['log', 'Сруб или брус']].forEach(([к, т], и) => {
    const о = document.createElement('div'); о.className = 'custom-select-option' + (и ? '' : ' selected'); о.dataset.room = к;
    о.innerHTML = '<span class="cso-name">' + т + '</span>'; пд.appendChild(о);
  });
  const инфо = $('#projectInfo'); все('.info-chip', инфо).forEach(е => е.remove());
  const кн = инфо.querySelector('.btn-edit-project');
  [['dims', 'Размеры'], ['vol', 'Объём'], ['fin', 'Стены и потолок'], ['floor', 'Пол'], ['base', 'Цена базы'], ['m3', 'Цена за м³']].forEach(([к, т]) => {
    const ч = document.createElement('div'); ч.className = 'info-chip'; ч.id = 'chip_' + к;
    if (к === 'm3') ч.setAttribute('style', 'color:var(--green-dark);border-color:var(--green-mid);');
    ч.innerHTML = '<span class="ic-k">' + т + '</span><strong></strong>'; инфо.insertBefore(ч, кн);
  });

  // ── Карточка итога ──
  $('#resultProjectName').textContent = 'Парная';
  $('#discountPctInput').value = 0;

  // ── Разделы ──
  const ПАРНАЯ = [
    ['dims', 'b', 'Парное отделение'],
    ['karkas', 'b', 'Несущий каркас по стенам помещения под отделку'],
    ['obr', 'b', 'Обрешётка 50 × 50 и контробрешётка с вентиляционным зазором'],
    ['utepl', 'b', 'Утепление базальтом для саун 50 мм'],
    ['par', 'b', 'Пароизоляция — фольга 80 мкм с проклейкой лентой'],
    ['osina', 'b', 'Вагонка из осины (сорт АБ), стены и потолок, доборы и плинтус'],
    ['polki', 'b', 'Полки из осины, 2 яруса', 'м²'],
    ['door', 'b', 'Дверь стеклянная 700 × 1900, бронза, с установкой'],
    ['plaf', 'b', 'Плафоны термостойкие +150 °C и электромонтаж', 'шт.'],
    ['vent', 'b', 'Вентиляция КуБасту вертикальная с монтажом'],
    ['klap', 'b', 'Клапаны вентиляционные деревянные «Флама»', 'шт.'],
    ['prop', 'b', 'Пропитки и огнезащитная обработка'],
    ['olha', 'p', 'Вагонка из ольхи (сорт Экстра) вместо осины'],
    ['polkiOlha', 'p', 'Полки из ольхи (сорт Экстра) вместо осины'],
    ['podsv', 'p', 'Подсветка полков', 'уровня'],
    ['spinki', 'p', 'Спинки и подспинники'],
    ['parya', 'p', 'Парящий полок'],
    ['panno', 'p', 'Можжевеловое панно 3D с подсветкой', 'м²'],
    ['okno', 'p', 'Панорамное окно с подогревом', 'м²'],
    ['maslo', 'p', 'Покрытие полков и стен маслом для саун'],
    ['nastil', 'p', 'Деревянный настил на пол'],
    ['premium', 'p', 'Сборка премиальной парной с монтажом электрики'],
    ['polList', 'p', 'Пол — доска шпунтованная лиственница 27 мм'],
    ['plitka', 'p', 'Подготовка пола под укладку плитки'],
    ['zvezd', 'p', 'Подсветка потолка «звёздное небо»'],
  ];
  const ПЕЧЬ = [
    ['ust', 'b', 'Установка дровяной печи — топка из комнаты отдыха'],
    ['dym', 'b', 'Вывод дымохода в крышу (1 этаж)'],
    ['mineri', 'b', 'Пожаростойкий портал из минерита'],
    ['kamni', 'b', 'Камень для печи «Жадеит»', 'кг'],
    ['list', 'b', 'Притопочный лист из нержавеющей стали 600 × 400 мм'],
    ['pusk', 'b', 'Пусконаладка печи, первый протоп, инструктаж'],
    ['yalta', 'p', 'Печь Изистим Ялта 35 в камне, 25–35 м³'],
    ['talk', 'p', 'Портал — талькохлорит «рваный камень», угловой, вместо минерита'],
    ['econ', 'p', 'Экономайзер Д-120, 6 плит, талькохлорит'],
    ['optima', 'p', 'Печь Ферингер Оптима, 16–28 м³'],
    ['bak', 'p', 'Навесной бак на трубу 50 л с краном'],
  ];
  const ЛОГ = [
    ['dost', 'b', 'Доставка материалов и оборудования', 'км от МКАД'],
    ['brig', 'b', 'Бригада 2 человека — суточные и проживание', 'дней'],
    ['nakl', 'b', 'Накладные и расходные материалы монтажа'],
    ['uborka', 'b', 'Уборка объекта по завершении работ'],
  ];
  const строка = ([к, вид, имя, ед]) => {
    const р = (вид === 'b' ? Т_БАЗА : Т_ЦЕНА).cloneNode(true);
    р.id = 'lbl_' + к; р.dataset.optId = к; р.dataset.k = к; р.style.order = 0;
    р.classList.toggle('active', вид === 'b');
    р.querySelector('input[type=checkbox]').id = 'chk_' + к;
    р.querySelector('.opt-pos').id = 'pos_' + к;
    р.querySelector('.opt-name').textContent = имя;
    р.querySelector('.opt-name').id = 'name_' + к;
    const цена = р.querySelector('.opt-price'); if (цена) { цена.id = 'optprice_' + к; цена.textContent = ''; }
    const ряд = вид === 'b' ? р.querySelector('.opt-included-row') : (цена && цена.parentElement);
    if (ед) {
      const ш = Т_ШАГИ.cloneNode(true); ш.dataset.k = к;
      ш.querySelector('.opt-qty-val').id = 'qtyval_' + к;
      const е = document.createElement('span'); е.className = 'opt-unit'; е.textContent = ед;
      const после = вид === 'b' ? ряд.querySelector('.opt-included') : цена;
      после.after(ш); ш.after(е);
    }
    if (к === 'dims') {
      const д = document.createElement('span'); д.className = 'opt-dims';
      д.innerHTML = ['L', 'W', 'H'].map((о, и) => '<input class="dim-in" data-dim="' + о + '" inputmode="decimal" aria-label="' + ['Длина', 'Ширина', 'Высота'][и] + ', м">').join('<i>×</i>') + '<span class="opt-unit">м</span>';
      ряд.querySelector('.opt-included').after(д);
    }
    const почему = document.createElement('span'); почему.className = 'opt-why'; почему.id = 'why_' + к; почему.hidden = true;
    (вид === 'b' ? ряд.querySelector('.opt-included') : цена).after(почему);
    const расч = document.createElement('div'); расч.className = 'opt-calc'; расч.id = 'calc_' + к; расч.hidden = true;
    р.querySelector('.opt-info').appendChild(расч);
    все('[id]', р).forEach(е => { if (/^(hl|gift|tochat|star|eye)_/.test(е.id)) е.id = е.id.replace(/_.*/, '_' + к); });
    return р;
  };
  const раздел = (номер, ключ, имя, список, примечания) => {
    const с = Т_РАЗДЕЛ.cloneNode(true); с.dataset.sec = ключ;
    с.querySelector('.section-header > span').innerHTML = '<span class="sec-no"><span class="sec-no-0">0</span>' + номер + '</span><span class="sec-dot">.&nbsp;</span>' + имя;
    const итог = с.querySelector('.section-total'); итог.id = 'sec_total_' + ключ; итог.textContent = '';
    const зам = с.querySelector('.section-note'); зам.id = 'sec_note_' + ключ;
    зам.querySelector('.sec-note-t').id = 'sec_note_t_' + ключ;
    const снять = зам.querySelector('.sec-base-btn'); снять.id = 'sec_base_' + ключ; снять.dataset.sec = ключ;
    const сп = с.querySelector('.opts-list'); сп.id = 'list_' + ключ; сп.innerHTML = '';
    список.forEach(р => сп.appendChild(строка(р)));
    const пр = с.querySelector('[id^="notesArea_"]'); пр.id = 'notesArea_' + ключ; пр.innerHTML = '';
    (примечания || []).forEach(т => { const п = Т_ПРИМ.cloneNode(true); п.removeAttribute('id'); п.querySelector('.note-item-text').textContent = т; пр.appendChild(п); });
    return с;
  };
  const все_р = $('#optionSections'); все_р.innerHTML = '';
  все_р.appendChild(раздел(1, 'st', 'Парное отделение', ПАРНАЯ, []));
  все_р.appendChild(раздел(2, 'pech', 'Печь и комплектующие', ПЕЧЬ, []));
  все_р.appendChild(раздел(3, 'log', 'Логистика', ЛОГ, ['Демонтаж старой парной не входит в расчёт']));

  // ── Итоги по разделам ──
  const бд = $('#breakdownTable'); все('.bd-row:not(.bd-head)', бд).forEach(е => е.remove());
  [['base', 'Базовая стоимость комплектации'], ['st', '1. Парное отделение'], ['pech', '2. Печь и комплектующие'], ['log', '3. Логистика'], ['total', 'Общая стоимость']].forEach(([к, т]) => {
    const р = document.createElement('div'); р.className = 'bd-row' + (к === 'total' ? ' bd-total' : ''); р.id = 'bd_' + к;
    р.innerHTML = '<span class="bd-name">' + т + '</span><span class="bd-pct">' + (к === 'base' ? '—' : '') + '</span><span class="bd-amt"></span>'; бд.appendChild(р);
  });

  // ── Лишнее: оверлеи, окна, скрытые панели ──
  все('body > *').forEach(е => { if (!е.matches('.page-wrap, #totalStrip, #presetChipCard, #presetChip, style, link')) е.remove(); });
  все('.page-wrap > *').forEach(е => { if (е.getBoundingClientRect().height === 0 && !е.matches('#breakdownCard, #resultCard')) е.remove(); });
  все('script, noscript, template').forEach(е => е.remove());
  return { строк: все('#optionSections .opt-item').length };
}
