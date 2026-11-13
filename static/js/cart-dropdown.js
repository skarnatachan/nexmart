// Keep the navbar cart dropdown open after +/- quantity buttons reload the page.
(function () {
    var KEY = 'reopenCartDropdown';
    var dropdown = document.getElementById('cartDropdown1');
    var button = document.getElementById('cartDropdownButton1');
    if (!dropdown || !button) return;

    dropdown.querySelectorAll('form[action*="/cart/add/"], form[action*="/cart/remove/"]').forEach(function (form) {
        form.addEventListener('submit', function () {
            try { sessionStorage.setItem(KEY, '1'); } catch (e) {}
        });
    });

    window.addEventListener('load', function () {
        var flag = null;
        try { flag = sessionStorage.getItem(KEY); sessionStorage.removeItem(KEY); } catch (e) {}
        if (flag) button.click();
    });
})();
