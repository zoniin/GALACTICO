/* What every page of the site shares once it runs, written once (ADR-0033). Loaded in <head>
   after the theme switch, so a page's own script can use it.

   Text in a drawing. An SVG scales its text with its viewBox: a label set at 2 units on a pitch
   100 units wide is 7 px on a phone. Every visible <text> is kept at 12 px or more on screen,
   the site's smallest type: its size in the drawing's own units is raised to 12 px over the
   drawing's scale, and put back when the drawing grows again. A drawing a page redraws is
   followed (new text is fitted on the next frame), and so is a change of width or a panel that
   opens. A page that would rather show a label elsewhere on a small screen hides it there.

   The archive, missing. Site.archiveMissing() is what an archive page says when the server
   has no 2017/18 archive installed (any 503): a sentence a reader can act on, never the
   server's own detail, which is written for whoever runs it. The setup steps are linked only
   for the reader of their own install, on a loopback address.

   A mark on a pitch. Site.focusRing(x, y, r) is the focus ring of a mark a reader can select
   (a player, a shot): two rings, dark inside light, like every focus ring of the site, drawn
   only while the mark has keyboard focus, so focus is never the chalk of a mark or the gold
   of the selected one. Site.hitArea(x, y) widens what a pointer can hit to 24 px on screen at
   any scale of the drawing. Both are rounded rects, so no rule for a mark's circle reaches
   them; a page's sheet (labs.css) draws them.

   Declares one global, Site. */
(function () {
  'use strict';
  var MIN = 12;
  var ARCHIVE_MISSING = "The 2017/18 archive isn't installed on this server.";
  var SETUP = 'https://github.com/zoniin/GALACTICO#running-it';
  var natural = new WeakMap();
  var queued = 0;

  function fit() {
    queued = 0;
    var texts = document.querySelectorAll('svg text');
    var i, text, size, matrix, scale;
    // The size each label was drawn at, read before any is changed.
    for (i = 0; i < texts.length; i++) {
      if (!natural.has(texts[i])) {
        natural.set(texts[i], parseFloat(window.getComputedStyle(texts[i]).fontSize) || 0);
      }
    }
    for (i = 0; i < texts.length; i++) {
      text = texts[i];
      size = natural.get(text);
      matrix = text.getClientRects().length ? text.getScreenCTM() : null;
      if (!size || !matrix) continue;
      // The vertical scale: the height of a letter, even in a drawing stretched sideways.
      scale = Math.sqrt(matrix.c * matrix.c + matrix.d * matrix.d);
      if (!scale) continue;
      if (size * scale < MIN) text.style.fontSize = (MIN / scale) + 'px';
      else text.style.removeProperty('font-size');
    }
  }

  function queue() {
    if (!queued) queued = window.requestAnimationFrame(fit);
  }

  function watch() {
    queue();
    window.addEventListener('resize', queue);
    if (window.MutationObserver) {
      new MutationObserver(queue).observe(document.body, {
        childList: true, subtree: true, attributes: true,
        attributeFilter: ['class', 'hidden', 'open', 'aria-selected'],
      });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch);
  else watch();

  function local() {
    return /^(localhost|127(\.\d{1,3}){3}|\[::1\])$/.test(window.location.hostname);
  }

  // One sentence, and on a reader's own install a link to the steps that install the archive.
  function archiveMissing() {
    return ARCHIVE_MISSING.replace(/'/g, '&#39;') + (local()
      ? ' <a href="' + SETUP + '">How to install it</a>.'
      : '');
  }

  function rect(cls, x, y, r) {
    return '<rect class="' + cls + '" x="' + (x - r) + '" y="' + (y - r) + '" width="' + 2 * r +
      '" height="' + 2 * r + '" rx="' + r + '"/>';
  }
  function focusRing(x, y, r) { return rect('ring', +x, +y, +r) + rect('ring core', +x, +y, +r); }
  function hitArea(x, y) { return rect('hit', +x, +y, 0.01); }

  window.Site = Object.freeze({
    archiveMissing: archiveMissing, fitText: fit, focusRing: focusRing, hitArea: hitArea,
    ARCHIVE_MISSING: ARCHIVE_MISSING,
  });
})();
