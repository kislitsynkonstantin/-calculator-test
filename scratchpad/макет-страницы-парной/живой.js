// Расчёт страницы «Парная» в макете. Модель цен — по книге Excel v2.4 с
// поправками от 26.10.2026; на размерах 3 × 4 × 2,3 м совпадает с ней до рубля.
(() => {
  const $ = s => document.querySelector(s);
  const все = (s, к = document) => [...к.querySelectorAll(s)];
  const р = ч => Math.round(ч).toLocaleString('ru-RU').replace(/ | /g, ' ') + ' ₽';
  const ч1 = ч => (Math.round(ч * 100) / 100).toLocaleString('ru-RU', { maximumFractionDigits: 2 });
  const К = 0.944615;                 // множитель маржи книги при 35 %

  const М = { L: 3, W: 4, H: 2.3, комн: 'stone', polki: 3.75, plaf: 2, klap: 2, podsv: 2, panno: 1, okno: 1, kamni: 80, dost: 50, brig: null };
  const ВКЛ = new Set(['olha', 'polkiOlha', 'podsv', 'spinki', 'parya', 'panno', 'okno', 'maslo', 'nastil', 'yalta', 'talk', 'econ']);
  const БАЗА_СНЯТА = new Set();
  const ПРЕМИУМ = ['podsv', 'parya', 'panno', 'okno', 'zvezd'];
  const ПЕЧИ = { yalta: [25, 35, 208425], optima: [16, 28, 64400] };
  const ШАГ = { polki: [0.25, 1], plaf: [1, 1], klap: [1, 1], podsv: [1, 1], panno: [0.5, 0.5], okno: [0.5, 0.5], kamni: [10, 20], dost: [10, 0], brig: [1, 5] };
  const ТИП = { stone: 'Камень: кирпич, блок, бетон', frame: 'Каркасный дом', log: 'Сруб или брус' };

  const геом = () => {
    const { L, W, H } = М;
    return { отд: 2 * (L + W) * H + L * W, пол: L * W, объём: L * W * H };
  };
  const дниАвто = г => Math.ceil(г.отд / 3.5 + М.polki / 1.5 + 4);
  const премиумN = () => ПРЕМИУМ.filter(к => ВКЛ.has(к)).length;
  const премиум = n => n ? Math.min(240000, 120000 + 30000 * (n - 1)) : 0;

  // Цены строк сверх базы
  const цены = г => ({
    olha: 209250 / 44.2 * г.отд, polkiOlha: 10138 / 3.75 * М.polki, podsv: 100365 / 2 * М.podsv,
    spinki: 14169, parya: 24182, panno: (М.panno * 35000 + 15000) / 0.7 * К, okno: 84959 * М.okno,
    maslo: 17853, nastil: 8974, premium: премиум(премиумN()), polList: 62458 / 12 * г.пол, plitka: 32646 / 12 * г.пол, zvezd: 53135,
    yalta: 208425, talk: 69807, econ: 30946, optima: 64400, bak: 12124,
  });
  // База разделов
  const базы = г => {
    const каркас = М.комн !== 'frame', утепл = М.комн === 'stone';
    const дни = М.brig || дниАвто(г);
    return {
      st: 178213 + 6518 * М.plaf + 2579 * М.klap + 15000 * М.polki + (9116.98 + (каркас ? 3041.66 : 0) + (утепл ? 2108.85 : 0)) * г.отд,
      pech: 199673 + 387.29 * М.kamni,
      log: 30228 + Math.max(0, М.dost - 50) * 100 + дни * (2 * 425.08 + 2456) + 14736 + 26922 + 5271,
    };
  };
  const РАЗДЕЛ = { st: 'st', pech: 'pech', log: 'log' };
  const раздел_строки = к => все('#list_' + к + ' .opt-item');

  function пересчёт() {
    const г = геом(), ц = цены(г), б = базы(г);
    // Сборка премиальной — сама
    const n = премиумN();
    if (n) ВКЛ.add('premium'); else ВКЛ.delete('premium');
    // Печь — одна
    const печь = ['yalta', 'optima'].find(к => ВКЛ.has(к));
    // Строки
    let всего = 0, база = 0, позиций = 0;
    const суммы = {};
    for (const с of Object.keys(РАЗДЕЛ)) {
      const снята = БАЗА_СНЯТА.has(с);
      let сумма = снята ? 0 : б[с]; if (!снята) база += б[с];
      let пор = 0, вкл = 0, выкл = 0;
      раздел_строки(с).forEach(эл => {
        const к = эл.dataset.k, базовая = !эл.querySelector('.opt-price');
        const на = базовая ? !снята && !(к === 'karkas' && М.комн === 'frame') && !(к === 'utepl' && М.комн !== 'stone') : ВКЛ.has(к);
        эл.classList.toggle('active', на);
        эл.querySelector('input[type=checkbox]').checked = на;
        эл.querySelector('.opt-pos').textContent = на ? ++пор : '';
        if (на) { вкл++; позиций++; } else выкл++;
        if (!базовая) {
          $('#optprice_' + к).textContent = р(ц[к]);
          if (на) сумма += ц[к];
        }
      });
      суммы[с] = сумма; всего += сумма;
      $('#sec_total_' + с).textContent = р(сумма);
      $('#sec_note_t_' + с).textContent = вкл + ' ' + склон(вкл, 'позиция', 'позиции', 'позиций') + ' в договоре · ' + выкл + ' доступно к добавлению';
      $('#sec_base_' + с).textContent = снята ? 'Вернуть базу' : 'Снять базу';
    }
    // Поля строк
    все('.dim-in').forEach(и => { if (document.activeElement !== и) и.value = ч1(М[и.dataset.dim]).replace('.', ','); });
    $('#name_dims').textContent = 'Парное отделение ' + [М.L, М.W, М.H].map(ч => ч1(ч)).join(' × ') + ' м';
    for (const к of Object.keys(ШАГ)) { const в = $('#qtyval_' + к); if (в) в.textContent = ч1(к === 'brig' ? (М.brig || дниАвто(г)) : М[к]); }
    подпись('dims', ч1(г.объём) + ' м³ · стены и потолок ' + ч1(г.отд) + ' м² · пол ' + ч1(г.пол) + ' м² — от них считаются цены строк раздела');
    почему('karkas', М.комн === 'frame' ? 'не нужен: стены — каркас' : 'сам: стены — ' + (М.комн === 'stone' ? 'камень' : 'сруб'));
    почему('utepl', М.комн === 'stone' ? 'само: стены — камень' : 'не нужно: ' + (М.комн === 'frame' ? 'каркасный дом' : 'сруб или брус'));
    подпись('obr', ч1(г.отд) + ' м²'); подпись('par', ч1(г.отд) + ' м²'); подпись('osina', ч1(г.отд) + ' м²');
    подпись('vent', 'в цене базы — 64 000 ₽ с работами');
    подпись('olha', ч1(г.отд) + ' м² · разница с осиной'); подпись('polkiOlha', ч1(М.polki) + ' м² · разница с осиной');
    подпись('panno', 'по умолчанию 1000 × 1000 мм · цена от площади, как в калькуляторе опций');
    подпись('premium', 'шкала 120 000 → 240 000 ₽: первая премиальная опция — 120 000 ₽, каждая следующая +30 000 ₽');
    почему('premium', n ? 'сама: ' + n + ' ' + склон(n, 'премиальная опция', 'премиальные опции', 'премиальных опций') : 'нет премиальных опций');
    подпись('polList', ч1(г.пол) + ' м²'); подпись('plitka', ч1(г.пол) + ' м²');
    for (const [к, [от, до]] of Object.entries(ПЕЧИ)) {
      const в = г.объём, ок = в >= от && в <= до;
      почему(к, ок ? 'подходит: парная ' + ч1(в) + ' м³' : (в > до ? 'мала' : 'велика') + ': парная ' + ч1(в) + ' м³', !ок);
      подпись(к, 'цена поставщика × 1,05');
    }
    подпись('brig', М.brig ? 'срок вписан вручную · по расчёту — ' + дниАвто(г) + ' дн.' : 'срок — от площади отделки и полков');
    // Итоги
    const пр = Number($('#discountPctInput').value) || 0;
    const соСкидкой = всего * (1 - пр / 100);
    $('#totalDisplay').textContent = р(всего);
    $('#baseDisplay').textContent = 'База ' + р(база) + ' · ' + позиций + ' ' + склон(позиций, 'позиция', 'позиции', 'позиций');
    $('#discountDisplay').textContent = р(соСкидкой);
    $('#resultProjectName').textContent = 'Парная ' + [М.L, М.W, М.H].map(ч => ч1(ч)).join(' × ') + ' м · ' + ТИП[М.комн].split(':')[0];
    $('#bd_base .bd-amt').textContent = р(база);
    for (const с of Object.keys(РАЗДЕЛ)) {
      const ряд = $('#bd_' + с); ряд.classList.toggle('bd-zero', !суммы[с]);
      ряд.querySelector('.bd-pct').textContent = всего ? Math.round(суммы[с] / всего * 100) + '%' : '0%';
      ряд.querySelector('.bd-amt').textContent = р(суммы[с]);
    }
    $('#bd_total .bd-pct').textContent = '100%'; $('#bd_total .bd-amt').textContent = р(всего);
    $('#chip_dims strong').textContent = [М.L, М.W, М.H].map(ч => ч1(ч)).join(' × ') + ' м';
    $('#chip_vol strong').textContent = ч1(г.объём) + ' м³';
    $('#chip_fin strong').textContent = ч1(г.отд) + ' м²';
    $('#chip_floor strong').textContent = ч1(г.пол) + ' м²';
    $('#chip_base strong').textContent = р(база);
    $('#chip_m3 strong').textContent = р(всего / г.объём);
    $('#tsVal').textContent = р(соСкидкой);
    $('#tsSub').textContent = 'База ' + р(база) + ' · ' + позиций + ' ' + склон(позиций, 'позиция', 'позиции', 'позиций');
    $('#tsDisc').textContent = пр ? '−' + ч1(пр) + '%' : '';
  }
  function склон(n, а, б, в) { const д = n % 10, с = n % 100; return д === 1 && с !== 11 ? а : д >= 2 && д <= 4 && (с < 12 || с > 14) ? б : в; }
  function подпись(к, т) { const е = $('#calc_' + к); if (е) { е.textContent = т; е.hidden = !т; } }
  function почему(к, т, тревога) { const е = $('#why_' + к); if (е) { е.textContent = т; е.hidden = !т; е.classList.toggle('warn', !!тревога); } }

  // ── Нажатия ──
  document.addEventListener('click', e => {
    const ш = e.target.closest('.opt-qty-btn');
    if (ш) {
      e.stopPropagation();
      const к = ш.closest('.opt-qty-stepper').dataset.k, [шаг, мин] = ШАГ[к];
      const знак = ш.textContent.includes('+') ? 1 : -1;
      const было = к === 'brig' ? (М.brig || дниАвто(геом())) : М[к];
      М[к] = Math.max(мин, Math.round((было + знак * шаг) * 100) / 100);
      пересчёт(); return;
    }
    const снять = e.target.closest('.sec-base-btn');
    if (снять) { const с = снять.dataset.sec; БАЗА_СНЯТА.has(с) ? БАЗА_СНЯТА.delete(с) : БАЗА_СНЯТА.add(с); пересчёт(); return; }
    const тех = e.target.closest('#techSelectTrigger');
    if (тех) { const д = $('#techSelectDropdown'); д.style.display = д.style.display === 'block' ? 'none' : 'block'; return; }
    const тип = e.target.closest('#projectSelectTrigger');
    if (тип) { const д = $('#projectSelectDropdown'); д.style.display = д.style.display === 'block' ? 'none' : 'block'; return; }
    const комн = e.target.closest('[data-room]');
    if (комн) {
      М.комн = комн.dataset.room; $('#projectSelectLabel').textContent = ТИП[М.комн];
      все('[data-room]').forEach(о => о.classList.toggle('selected', о === комн));
      $('#projectSelectDropdown').style.display = 'none'; пересчёт(); return;
    }
    if (e.target.closest('#techSelectDropdown .custom-select-option')) { $('#techSelectDropdown').style.display = 'none'; return; }
    if (!e.target.closest('#projectSelectWrap')) $('#projectSelectDropdown').style.display = 'none';
    if (!e.target.closest('#techSelectWrap')) $('#techSelectDropdown').style.display = 'none';
    if (e.target.closest('#darkModeBtn')) { document.body.classList.toggle('dark'); return; }
    const стр = e.target.closest('.opt-item');
    if (!стр || e.target.closest('button, input, .opt-dims')) return;
    const к = стр.dataset.k;
    if (!стр.querySelector('.opt-price') || к === 'premium') return;
    if (ВКЛ.has(к)) ВКЛ.delete(к); else {
      ВКЛ.add(к);
      if (к in ПЕЧИ) Object.keys(ПЕЧИ).forEach(о => о !== к && ВКЛ.delete(о));
      if (к === 'polList') ВКЛ.delete('plitka'); if (к === 'plitka') ВКЛ.delete('polList');
    }
    пересчёт();
  });
  document.addEventListener('input', e => {
    const и = e.target.closest('.dim-in');
    if (и) { const ч = parseFloat(и.value.replace(',', '.')); if (ч > 0.5 && ч < 10) { М[и.dataset.dim] = ч; пересчёт(); } return; }
    if (e.target.id === 'discountPctInput') пересчёт();
  });
  document.addEventListener('focusout', e => { if (e.target.closest('.dim-in')) пересчёт(); });
  // Полоска итога — пока карточка итога выше экрана
  const полоска = () => { const к = $('#resultCard').getBoundingClientRect(); $('#totalStrip').classList.toggle('on', к.bottom < 0); };
  addEventListener('scroll', полоска, { passive: true });
  пересчёт(); полоска();
})();
