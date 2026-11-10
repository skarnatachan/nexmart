// Password show/hide toggle for Django admin pages. The admin's templates
// aren't ours, so instead of rendering a button in the template (as
// the site's templates do) this wraps every password
// input at load time. Styles: static/css/admin-password-toggle.css.
(function () {
  const ICONS = {
    show:
      '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">' +
      '<path stroke="currentColor" stroke-width="2" d="M21 12c0 1.2-4.03 6-9 6s-9-4.8-9-6c0-1.2 4.03-6 9-6s9 4.8 9 6Z"/>' +
      '<path stroke="currentColor" stroke-width="2" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg>',
    hide:
      '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">' +
      '<path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" ' +
      'd="M3.933 13.909A4.357 4.357 0 0 1 3 12c0-1 4-6 9-6m7.6 3.8A5.068 5.068 0 0 1 21 12c0 1-3 6-9 6-.314 0-.62-.014-.918-.04M5 19 19 5m-4 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg>',
  };

  function enhance(input) {
    if (input.closest(".password-toggle")) return; // already wrapped

    const wrapper = document.createElement("span");
    wrapper.className = "password-toggle";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle-button";
    if (input.id) button.setAttribute("aria-controls", input.id);
    wrapper.appendChild(button);

    function render() {
      const visible = input.type === "text";
      button.innerHTML = visible ? ICONS.hide : ICONS.show;
      button.setAttribute("aria-pressed", String(visible));
      button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
      button.title = visible ? "Hide password" : "Show password";
    }

    button.addEventListener("click", () => {
      input.type = input.type === "password" ? "text" : "password";
      render();
      input.focus({ preventScroll: true });
    });

    // Re-mask before submitting so browsers and password managers treat the
    // value as a password.
    input.form?.addEventListener("submit", () => {
      input.type = "password";
      render();
    });

    render();
  }

  document.querySelectorAll('input[type="password"]').forEach(enhance);
})();
