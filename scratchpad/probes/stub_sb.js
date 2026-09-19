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
  window.__RPC = window.__RPC || {};

  function ответ(строки) { return { data: строки, error: null, count: строки ? строки.length : 0 }; }

  /* Отборы выполняются по-настоящему. Заглушка, отдающая всю таблицу на любой
     запрос, показывает пробе не то, что увидит страница: строка по чужому
     коду попала бы в счёт заходов, а уведомления собрались бы по чужим
     ссылкам. Ровно на этом проба и молчала бы. */
  function запрос(таблица) {
    var строки = (window.__ТАБЛИЦЫ[таблица] || []).slice();
    var один = false;
    var о = {};
    ['select', 'gt', 'gte',
     'lt', 'lte', 'like', 'ilike', 'not', 'or', 'filter', 'range',
     'contains', 'overlaps', 'match', 'abortSignal'].forEach(function (и) {
      о[и] = function () { return о; };
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
    о.upsert = function (значения, наст) {
      добавить = Array.isArray(значения) ? значения.slice() : [значения];
      ключСлияния = (наст && наст.onConflict) ? String(наст.onConflict).split(',')[0].trim() : null;
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
          if (ключСлияния) {
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
    о.eq = function (поле, знач) {
      строки = строки.filter(function (р) { return String(р[поле]) === String(знач); });
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
      var ждать = Number(window.__ЗАДЕРЖКА || 0);
      var обещание = ждать > 0
        ? new Promise(function (д) { setTimeout(function () { д(итог); }, ждать); })
        : Promise.resolve(итог);
      return обещание.then(принять, отклонить);
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
