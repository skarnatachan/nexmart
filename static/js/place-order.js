// Prevent double submits while the order / payment is being processed.
(function () {
    [['checkout-form', 'place-order-btn', 'Placing order...'], ['payment-form', 'pay-btn', 'Processing payment...']]
        .forEach(function (ids) {
            var form = document.getElementById(ids[0]);
            var btn = document.getElementById(ids[1]);
            if (!form || !btn) return;
            form.addEventListener('submit', function () {
                btn.disabled = true;
                btn.textContent = ids[2];
            });
        });
})();
