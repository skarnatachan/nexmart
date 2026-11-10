// Show/hide toggle for password inputs rendered with a data-password-toggle button in the page templates.
(function () {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        const input = document.getElementById(button.dataset.passwordToggle);
        if (!input) return;

        function render() {
            const visible = input.type === "text";
            button.querySelector("[data-password-icon=show]").classList.toggle("hidden", visible);
            button.querySelector("[data-password-icon=hide]").classList.toggle("hidden", !visible);
            button.setAttribute("aria-pressed", String(visible));
            button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
        }

        button.addEventListener("click", () => {
            input.type = input.type === "password" ? "text" : "password";
            render();
            // Keep the caret where the user was typing.
            input.focus({preventScroll: true});
        });

        // Re-mask before submitting so browsers and password managers treat the
        // value as a password (and don't offer to save it as plain text).
        input.form?.addEventListener("submit", () => {
            input.type = "password";
            render();
        });
        button.classList.replace("hidden", "inline-flex");
    });
})();
