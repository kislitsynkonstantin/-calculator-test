(function () {
  var МК = window.МК, б = document.body, к = document.documentElement;
  var с = { glass: true, ui: б.classList.contains('ui-light') ? 'light' : 'blank', dark: б.classList.contains('dark'), tone: к.dataset.tone || 'teal' };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function тост(т) {
    var e = $('#mkToast'); e.textContent = т; e.classList.add('on');
    clearTimeout(тост.т); тост.т = setTimeout(function () { e.classList.remove('on'); }, 2200);
  }

  // ── Галочка «Стекло» в настройках — там, где она будет в калькуляторе ──
  (function () {
    var ряд = $$('#settingsBody .st-row').filter(function (р) { return р.querySelector('.st-ui-btn'); })[0];
    if (!ряд) return;
    var н = document.createElement('div');
    н.className = 'st-row'; н.id = 'mkGlassRow';
    н.innerHTML = '<div><div class="st-label">Стекло</div><div class="st-sub">Панели, окна и полоска итога — из матового стекла поверх цветного фона</div></div>' +
      '<label class="st-toggle"><input type="checkbox" id="mkGlassToggle" checked><span class="st-toggle-slider"></span></label>';
    ряд.parentNode.insertBefore(н, ряд.nextSibling);
  })();

  function применить() {
    б.classList.toggle('ui-glass', с.glass);
    б.classList.toggle('ui-blank', с.ui === 'blank');
    б.classList.toggle('ui-light', с.ui === 'light');
    б.classList.toggle('dark', с.dark);
    if (с.tone === 'teal') delete к.dataset.tone; else к.dataset.tone = с.tone;
    var л = МК.лого[с.tone] || МК.лого.teal, img = $('#headerLogo');
    if (img && л) img.src = с.dark ? л.light : л.dark;
    $$('.mk-seg').forEach(function (г) {
      var v = г.dataset.k === 'dark' ? (с.dark ? '1' : '0') : с[г.dataset.k];
      $$('button', г).forEach(function (кн) { var on = кн.dataset.v === v; кн.classList.toggle('on', on); кн.setAttribute('aria-pressed', on); });
    });
    ['mkGlass', 'mkGlassToggle'].forEach(function (ид) { var e = document.getElementById(ид); if (e) e.checked = с.glass; });
    $$('#settingsBody .st-theme-btn[data-mode]').forEach(function (кн) { кн.classList.toggle('active', кн.dataset.mode === (с.dark ? 'dark' : 'light')); });
    $$('#settingsBody .st-ui-btn').forEach(function (кн) { кн.classList.toggle('active', кн.dataset.ui === с.ui); });
    var sel = $('#stToneSelect'); if (sel) sel.value = с.tone;
    var мета = $('meta[name="theme-color"]'); if (мета) мета.setAttribute('content', с.dark ? '#111' : '#fff');
  }

  // ── Окна ──
  function восстановить(e, st) {
    if (st.style == null) e.removeAttribute('style'); else e.setAttribute('style', st.style);
    e.className = st.cls || '';
  }
  function закрыть() {
    Object.keys(МК.окна).forEach(function (и) { var о = МК.окна[и], e = document.getElementById(о.id); if (e) восстановить(e, о.closed); });
    б.style.overflow = '';
  }
  function открыть(имя) {
    закрыть();
    var о = МК.окна[имя], e = о && document.getElementById(о.id);
    if (!e) return;
    восстановить(e, о.open);
    e.scrollTop = 0;
    $$('*', e).forEach(function (х) { if (х.scrollTop) х.scrollTop = 0; });
    б.style.overflow = 'hidden';
  }

  var КНОПКИ = { presetsBtn: 'presets', paymentPlanBtn: 'plan', settingsBtn: 'settings', actionLogBtn: 'log' };
  document.addEventListener('click', function (ev) {
    var т = ev.target;
    var окноМакета = т.closest('.mk-wins button[data-w]');
    if (окноМакета) { открыть(окноМакета.dataset.w); return; }
    var сег = т.closest('.mk-seg button');
    if (сег) {
      var g = сег.parentNode.dataset.k;
      if (g === 'dark') с.dark = сег.dataset.v === '1'; else с[g] = сег.dataset.v;
      применить(); return;
    }
    if (т.closest('#mkFab')) { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    // Панель кнопок калькулятора
    var кн = т.closest('#headerBtns button, #printPreviewWrap');
    if (кн && !т.closest('.mk')) {
      var ид = кн.id;
      if (КНОПКИ[ид]) { открыть(КНОПКИ[ид]); return; }
      if (кн.closest('#printPreviewWrap')) { открыть('print'); return; }
      if (ид === 'darkModeBtn') { с.dark = !с.dark; применить(); return; }
      тост('В макете открываются пять окон: пресеты, платёжный план, настройки, журнал, печать');
      return;
    }
    // Закрыть окно: крестик или подложка
    var оверлей = Object.keys(МК.окна).map(function (и) { return document.getElementById(МК.окна[и].id); })
      .filter(function (e) { return e && e.contains(т); })[0];
    if (оверлей) {
      if (т === оверлей || т.closest('.ovl-x, [aria-label="Закрыть"], [title="Закрыть"]')) { закрыть(); return; }
      // Вкладки пресетов
      var вк = т.closest('.ptab');
      if (вк) {
        var имя = вк.id.replace('ptab-', '');
        ['my', 'shared', 'code'].forEach(function (x) {
          var b = document.getElementById('ptab-' + x), c = document.getElementById('ptab-content-' + x);
          if (b) b.classList.toggle('ptab-active', x === имя);
          if (c) c.style.display = x === имя ? 'flex' : 'none';
        });
        return;
      }
      // Настройки: тема, стиль
      var реж = т.closest('#settingsBody .st-theme-btn[data-mode]');
      if (реж) { с.dark = реж.dataset.mode === 'dark' || (реж.dataset.mode === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches); применить(); return; }
      var стиль = т.closest('#settingsBody .st-ui-btn');
      if (стиль) { с.ui = стиль.dataset.ui; применить(); return; }
    }
  });
  document.addEventListener('change', function (ev) {
    if (ev.target.id === 'mkGlass' || ev.target.id === 'mkGlassToggle') { с.glass = ev.target.checked; применить(); }
    if (ev.target.id === 'stToneSelect') { с.tone = ev.target.value; применить(); }
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') закрыть(); });

  // ── Прокрутка: панель кнопок прилипает, полоска итога выезжает ──
  var hb = $('#headerBtns'), ts = $('#totalStrip'), rc = $('#resultCard'), fab = $('#mkFab'), intro = $('#mkIntro');
  var место = document.createElement('div'); hb.parentNode.insertBefore(место, hb.nextSibling);
  function прокрутка() {
    var липко = hb.classList.contains('sticky');
    var верх = (липко ? место : hb).getBoundingClientRect().top;
    var надо = верх < 0;
    if (надо !== липко) {
      место.style.height = надо ? hb.offsetHeight + 'px' : '0';
      hb.classList.toggle('sticky', надо); б.classList.toggle('sticky-active', надо);
    }
    var on = rc.getBoundingClientRect().bottom < 0;
    ts.classList.toggle('on', on); б.classList.toggle('total-strip-on', on);
    fab.classList.toggle('on', intro.getBoundingClientRect().bottom < 0);
  }
  window.addEventListener('scroll', прокрутка, { passive: true });
  window.addEventListener('resize', прокрутка);
  применить(); прокрутка();
})();
