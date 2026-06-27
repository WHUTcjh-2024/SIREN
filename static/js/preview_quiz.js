/**
 * preview_quiz.js — 预习测验逻辑
 */
(function () {
  'use strict';

  var QUIZ_KEY = 'siren_quiz_result';

  function setQuizPassed() {
    try { localStorage.setItem(QUIZ_KEY, JSON.stringify({ passed: true, at: new Date().toISOString() })); } catch (e) {}
    if (window.ExperimentSession) {
      window.ExperimentSession.markStepDone('quiz');
    }
  }

  function isQuizPassed() {
    try {
      var r = JSON.parse(localStorage.getItem(QUIZ_KEY));
      return r && r.passed;
    } catch (e) { return false; }
  }

  // Expose
  window.PreviewQuiz = { setQuizPassed: setQuizPassed, isQuizPassed: isQuizPassed };
})();
