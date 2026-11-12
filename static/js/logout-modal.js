// Auto-opens the logout confirmation modal (templates/base.html) on page
// load. Flowbite's own data-modal-* wiring only runs on the window "load"
// event, which can fire after this script, so we instantiate and control
// the Modal directly instead of clicking a trigger button or relying on
// Flowbite's declarative data-modal-hide bindings. The Modal class itself
// (unlike the deferred auto-discovery) is assigned to window.Modal as soon
// as flowbite.min.js runs, so it's already available here.
(function () {
  const modalEl = document.getElementById("logout-modal");
  if (!modalEl || typeof window.Modal !== "function") return;

  const modal = new window.Modal(modalEl);
  modal.show();

  modalEl.querySelectorAll('[data-modal-hide="logout-modal"]').forEach((button) => {
    button.addEventListener("click", () => modal.hide());
  });
})();
