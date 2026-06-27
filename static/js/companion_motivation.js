/**
 * companion_motivation.js — 智慧星学习激励与情感陪伴
 */
(function () {
  'use strict';

  var MESSAGES = [
    { title: '欢迎回来！', text: '今天也要加油哦，我在旁边陪你～' },
    { title: '实验小提示', text: '拍照时保持激光稳定，可以获得更精确的条纹数据。' },
    { title: '做得不错！', text: '每完成一个步骤，你对物理的理解又深了一层。' },
    { title: '休息一下？', text: '长时间盯着屏幕会累的，站起来活动活动吧～' },
    { title: '好奇心是最好的老师', text: '如果有疑问，随时问我，我会尽力帮你解答！' }
  ];

  function showToast(msg) {
    var existing = document.querySelector('.companion-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.className = 'companion-toast';
    toast.innerHTML =
      '<div class="companion-toast-icon"><i class="fa fa-comments"></i></div>' +
      '<div class="companion-toast-body">' +
      '<div class="companion-toast-title">' + msg.title + '</div>' +
      '<div class="companion-toast-text">' + msg.text + '</div>' +
      '</div>' +
      '<button type="button" class="companion-toast-close" aria-label="关闭"><i class="fa fa-times"></i></button>';

    document.body.appendChild(toast);

    toast.querySelector('.companion-toast-close').addEventListener('click', function () {
      toast.classList.add('hide');
      setTimeout(function () { toast.remove(); }, 300);
    });

    setTimeout(function () {
      if (toast.parentNode) {
        toast.classList.add('hide');
        setTimeout(function () { toast.remove(); }, 300);
      }
    }, 8000);
  }

  // Show a random greeting after 5 seconds on home page
  document.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('.home-hero')) {
      setTimeout(function () {
        var idx = Math.floor(Math.random() * MESSAGES.length);
        showToast(MESSAGES[idx]);
      }, 5000);
    }
  });
})();
