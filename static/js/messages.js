// Auto-close django.contrib.messages alerts (templates/partials/alert.html)
// after data-auto-dismiss milliseconds. The countdown pauses while the alert
// is hovered or has keyboard focus, and restarts in full afterwards, so a
// message never disappears while someone is reading or interacting with it.
(function () {
  function hide(alert) {
    // Use Flowbite's Dismiss instance (same fade as the close button) when
    // it's registered; otherwise just remove the element.
    const dismiss = window.FlowbiteInstances?.getInstance("Dismiss", alert.id);
    if (dismiss) {
      dismiss.hide();
    } else {
      alert.remove();
    }
  }

  document.querySelectorAll("[data-auto-dismiss]").forEach((alert) => {
    const delay = Number(alert.dataset.autoDismiss) || 5000;
    let timer = null;
    let hovered = false;
    let focused = false;

    function start() {
      clearTimeout(timer);
      timer = setTimeout(() => hide(alert), delay);
    }

    function pause() {
      clearTimeout(timer);
    }

    function resumeIfIdle() {
      if (!hovered && !focused) start();
    }

    alert.addEventListener("mouseenter", () => { hovered = true; pause(); });
    alert.addEventListener("mouseleave", () => { hovered = false; resumeIfIdle(); });
    alert.addEventListener("focusin", () => { focused = true; pause(); });
    alert.addEventListener("focusout", (event) => {
      if (!alert.contains(event.relatedTarget)) {
        focused = false;
        resumeIfIdle();
      }
    });

    start();
  });
})();
