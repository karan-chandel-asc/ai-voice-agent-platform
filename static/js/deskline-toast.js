/**
 * Shared Deskline toaster — use showToast(message, type, duration)
 * types: success | error | info
 */
(function (global) {
  function ensureContainer() {
    var el = document.getElementById('toast-container');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'toast-container';
    document.body.appendChild(el);
    return el;
  }

  var ICONS = {
    success: '<svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
    error:   '<svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
    info:    '<svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>',
  };

  function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration == null ? 4000 : duration;
    if (!ICONS[type]) type = 'info';

    var container = ensureContainer();
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML = ICONS[type];

    var text = document.createElement('span');
    text.style.whiteSpace = 'pre-line';
    text.textContent = message == null ? '' : String(message);
    toast.appendChild(text);
    container.appendChild(toast);

    setTimeout(function () {
      toast.style.animation = 'desklineToastOut 0.25s ease forwards';
      setTimeout(function () { toast.remove(); }, 250);
    }, duration);
  }

  global.showToast = showToast;
})(window);
