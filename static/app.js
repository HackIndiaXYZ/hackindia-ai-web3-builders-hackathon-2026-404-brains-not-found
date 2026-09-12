/* ═══════════════════════════════════════════════════════════════
   TrafficGuard Pro — Shared Utilities
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── Content Visibility (Immediate, No Staggered AI Slop Fade) ── */
  function initReveal() {
    var els = document.querySelectorAll('.reveal');
    els.forEach(function (el) { el.classList.add('visible'); });
  }

  /* ── Theme Toggle ── */
  function initTheme() {
    var stored = localStorage.getItem('tg_theme');
    if (stored) {
      document.documentElement.setAttribute('data-theme', stored);
    }
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('tg_theme', next);
      });
    });
  }

  /* ── Clock ── */
  function initClock() {
    var el = document.getElementById('live-clock');
    if (!el) return;
    function tick() {
      var now = new Date();
      var h = String(now.getHours()).padStart(2, '0');
      var m = String(now.getMinutes()).padStart(2, '0');
      var s = String(now.getSeconds()).padStart(2, '0');
      el.textContent = h + ':' + m + ':' + s + ' IST';
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ── i18n ── */
  var translations = {
    en: {},
    hi: {
      dashboard: 'डैशबोर्ड',
      violations: 'उल्लंघन',
      analytics: 'विश्लेषण',
      officers: 'अधिकारी',
      settings: 'सेटिंग्स',
      login: 'लॉग इन',
      logout: 'लॉग आउट',
      search: 'खोजें',
      submit: 'जमा करें',
      cancel: 'रद्द करें',
      save: 'सहेजें',
      delete: 'हटाएं',
      edit: 'संपादित करें',
      close: 'बंद करें',
      total: 'कुल',
      active: 'सक्रिय',
      pending: 'लंबित',
      resolved: 'हल',
      paid: 'भुगतान किया',
      unpaid: 'अवैतनिक'
    },
    pb: {
      dashboard: 'ਡੈਸ਼ਬੋਰਡ',
      violations: 'ਉਲੰਘਣਾਵਾਂ',
      analytics: 'ਵਿਸ਼ਲੇਸ਼ਣ',
      officers: 'ਅਧਿਕਾਰੀ',
      settings: 'ਸੈਟਿੰਗਾਂ',
      login: 'ਲੌਗ ਇਨ',
      logout: 'ਲੌਗ ਆਊਟ',
      search: 'ਖੋਜ',
      submit: 'ਜਮ੍ਹਾ ਕਰੋ',
      cancel: 'ਰੱਦ ਕਰੋ',
      save: 'ਸੰਭਾਲੋ',
      delete: 'ਮਿਟਾਓ',
      edit: 'ਸੋਧੋ',
      close: 'ਬੰਦ ਕਰੋ',
      total: 'ਕੁੱਲ',
      active: 'ਸਰਗਰਮ',
      pending: 'ਲੰਬਿਤ',
      resolved: 'ਹੱਲ',
      paid: 'ਭੁਗਤਾਨ',
      unpaid: 'ਅਵੈਤਨਿਕ'
    }
  };

  function applyLang(lang) {
    var dict = translations[lang] || translations.en;
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (dict[key]) el.textContent = dict[key];
    });
  }

  function initI18n() {
    var stored = localStorage.getItem('tg_lang') || 'en';
    applyLang(stored);
    document.querySelectorAll('[data-lang]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var lang = btn.getAttribute('data-lang');
        localStorage.setItem('tg_lang', lang);
        applyLang(lang);
      });
    });
  }

  /* ── Init all ── */
  function init() {
    initReveal();
    initTheme();
    initClock();
    initI18n();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.TG = { init: init, applyLang: applyLang };
})();
