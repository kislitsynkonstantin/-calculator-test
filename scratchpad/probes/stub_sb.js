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
    }],
    client_link_visits: [
      { code: 'adkv8q5j', seen_at: '2026-09-16T14:22:00Z', version_at: '2026-09-16T10:00:00Z' },
      { code: 'adkv8q5j', seen_at: '2026-09-15T18:03:00Z', version_at: '2026-09-16T10:00:00Z' },
      { code: 'adkv8q5j', seen_at: '2026-09-15T11:40:00Z', version_at: '2026-09-12T08:00:00Z' },
    ],
  };
  window.__RPC = window.__RPC || {};

  function ответ(строки) { return { data: строки, error: null, count: строки ? строки.length : 0 }; }

  function запрос(таблица) {
    var строки = (window.__ТАБЛИЦЫ[таблица] || []).slice();
    var один = false;
    var о = {};
    ['select', 'insert', 'update', 'upsert', 'delete', 'eq', 'neq', 'in', 'is', 'gt', 'gte',
     'lt', 'lte', 'like', 'ilike', 'not', 'or', 'filter', 'order', 'limit', 'range',
     'contains', 'overlaps', 'match', 'abortSignal'].forEach(function (и) {
      о[и] = function () { return о; };
    });
    о.single = о.maybeSingle = function () { один = true; return о; };
    о.then = function (принять, отклонить) {
      var р = один ? (строки[0] || null) : строки;
      return Promise.resolve(один ? { data: р, error: null } : ответ(строки)).then(принять, отклонить);
    };
    о.catch = function (ф) { return о.then(null, ф); };
    о.finally = function (ф) { return о.then(ф, ф); };
    return о;
  }

  var канал = { on: function () { return канал; }, subscribe: function () { return канал; },
                unsubscribe: function () { return Promise.resolve('ok'); } };

  var клиент = {
    from: запрос,
    rpc: function (имя, арг) {
      var д = window.__RPC[имя];
      return Promise.resolve({ data: typeof д === 'function' ? д(арг) : (д === undefined ? null : д), error: null });
    },
    channel: function () { return канал; },
    removeChannel: function () { return Promise.resolve('ok'); },
    storage: { from: function () { return {
      upload: function () { return Promise.resolve({ data: { path: 'проба' }, error: null }); },
      remove: function () { return Promise.resolve({ data: [], error: null }); },
      getPublicUrl: function (п) { return { data: { publicUrl: '/assets/logo-bmsk-dark.png' } }; },
      createSignedUrl: function () { return Promise.resolve({ data: { signedUrl: '/assets/logo-bmsk-dark.png' }, error: null }); },
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
