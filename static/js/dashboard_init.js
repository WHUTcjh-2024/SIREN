/**
 * dashboard_init.js — 仪表板初始化
 * 侧边栏切换、导航高亮、通用交互
 */
(function () {
  'use strict';

  // Sidebar toggle (mobile)
  var toggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('app-sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('is-open');
    });
    document.addEventListener('click', function (e) {
      if (sidebar.classList.contains('is-open') &&
          !sidebar.contains(e.target) &&
          e.target !== toggle) {
        sidebar.classList.remove('is-open');
      }
    });
  }

  // Export button
  var exportBtns = document.querySelectorAll('[data-export-report]');
  exportBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      alert('报告导出功能即将上线，敬请期待！');
    });
  });
})();
