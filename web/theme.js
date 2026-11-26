/* The theme switch in the site header. Loaded in <head>, before the page paints, so a reader
   who chose a theme never sees the other one first.

   With no choice stored the page follows the system (prefers-color-scheme). A choice is stored
   in this browser only, and only the theme: nothing about what the reader looked at. Without
   script the switch stays hidden and the system theme applies. Declares no global. */
(function () {
  'use strict';
  var KEY = 'galactico-theme';
  var root = document.documentElement;
  var system = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function stored() {
    try { return window.localStorage.getItem(KEY); } catch (error) { return null; }
  }
  function store(value) {
    try { window.localStorage.setItem(KEY, value); } catch (error) { /* private mode */ }
  }
  function dark() {
    var chosen = root.getAttribute('data-theme');
    if (chosen === 'dark' || chosen === 'light') return chosen === 'dark';
    return Boolean(system && system.matches);
  }

  var choice = stored();
  if (choice === 'dark' || choice === 'light') root.setAttribute('data-theme', choice);

  function wire() {
    var toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) return;
    var sync = function () { toggle.setAttribute('aria-pressed', String(dark())); };
    toggle.hidden = false;
    sync();
    toggle.addEventListener('click', function () {
      var next = dark() ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      store(next);
      sync();
    });
    if (system && system.addEventListener) system.addEventListener('change', sync);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
