/**
 * experiment_session.js — 实验会话管理
 * 管理实验进度、步骤状态、活动日志
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'siren_experiment_session';
  var STEPS = ['quiz', 'capture', 'process', 'dynamic_capture', 'dynamic_process'];
  var STEP_LABELS = {
    quiz: '预习测验',
    capture: '静态图像采集',
    process: '静态数据处理',
    dynamic_capture: '动态图像采集',
    dynamic_process: '动态数据处理'
  };

  function getSession() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveSession(data) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) { /* ignore */ }
  }

  function initSession() {
    var s = getSession();
    if (!s) {
      s = {
        started: new Date().toISOString(),
        steps: {},
        activity: []
      };
      saveSession(s);
    }
    return s;
  }

  function markStepDone(step) {
    var s = initSession();
    if (!s.steps) s.steps = {};
    s.steps[step] = { done: true, at: new Date().toISOString() };
    addActivity('完成: ' + (STEP_LABELS[step] || step));
    saveSession(s);
  }

  function isStepDone(step) {
    var s = getSession();
    return s && s.steps && s.steps[step] && s.steps[step].done;
  }

  function isQuizPassed() {
    return isStepDone('quiz') || document.cookie.indexOf('demo_mode=1') !== -1;
  }

  function getProgress() {
    var done = 0;
    STEPS.forEach(function (step) {
      if (isStepDone(step)) done++;
    });
    return { done: done, total: STEPS.length, percent: Math.round((done / STEPS.length) * 100) };
  }

  function addActivity(msg) {
    var s = initSession();
    if (!s.activity) s.activity = [];
    s.activity.unshift({ msg: msg, time: new Date().toISOString() });
    if (s.activity.length > 50) s.activity = s.activity.slice(0, 50);
    saveSession(s);
  }

  function getActivity() {
    var s = getSession();
    return (s && s.activity) || [];
  }

  function renderActivityLog(listId) {
    var el = document.getElementById(listId);
    if (!el) return;
    var items = getActivity().slice(0, 8);
    if (items.length === 0) {
      el.innerHTML = '<li style="padding:12px 0;font-size:12px;color:#94a3b8;text-align:center;">暂无记录</li>';
      return;
    }
    el.innerHTML = items.map(function (item) {
      var t = new Date(item.time);
      var timeStr = (t.getMonth() + 1) + '/' + t.getDate() + ' ' +
        String(t.getHours()).padStart(2, '0') + ':' + String(t.getMinutes()).padStart(2, '0');
      return '<li><span style="color:#64748b;">' + item.msg + '</span><span style="font-size:11px;color:#94a3b8;white-space:nowrap;">' + timeStr + '</span></li>';
    }).join('');
  }

  function applyProgressUI() {
    var p = getProgress();
    // Home page metrics
    var stepsEl = document.getElementById('hero-metric-steps');
    var pctEl = document.getElementById('hero-metric-pct');
    if (stepsEl) stepsEl.textContent = p.done + '/' + p.total;
    if (pctEl) pctEl.textContent = p.percent + '%';

    // Rail progress
    var railPct = document.getElementById('exp-total-percent');
    var railBar = document.getElementById('exp-total-progress');
    if (railPct) railPct.textContent = p.percent + '%';
    if (railBar) railBar.style.width = p.percent + '%';

    // Badges
    var badges = document.querySelectorAll('[data-exp-badge]');
    badges.forEach(function (badge) {
      var item = badge.closest('[data-exp-step]');
      if (item) {
        var step = item.getAttribute('data-exp-step');
        if (isStepDone(step)) {
          badge.textContent = '已完成';
          badge.className = 'app-badge app-badge-green';
        }
      }
    });

    // Quiz badge in sidebar
    var quizPill = document.getElementById('sidebar-quiz-pill');
    if (quizPill) {
      if (isQuizPassed()) {
        quizPill.textContent = '已通过';
        quizPill.className = 'app-nav-pill';
        quizPill.style.background = 'rgba(16,185,129,.15)';
        quizPill.style.color = '#10b981';
      } else {
        quizPill.hidden = false;
      }
    }
  }

  // Public API
  window.ExperimentSession = {
    init: initSession,
    markStepDone: markStepDone,
    isStepDone: isStepDone,
    isQuizPassed: isQuizPassed,
    getProgress: getProgress,
    addActivity: addActivity,
    getActivity: getActivity,
    renderActivityLog: renderActivityLog,
    applyProgressUI: applyProgressUI
  };

  // Auto-init
  document.addEventListener('DOMContentLoaded', function () {
    initSession();
    document.dispatchEvent(new CustomEvent('experiment-session-ready'));
  });
})();
