// PayPal Smart Buttons: the server creates and captures the order, the browser only approves it.
(function () {
    var container = document.getElementById('paypal-button-container');
    var message = document.getElementById('paypal-message');
    if (!container) return;

    function showError(text) {
        if (!message) return;
        message.textContent = text;
        message.classList.remove('hidden');
    }

    function post(url, body) {
        var token = document.querySelector('input[name=csrfmiddlewaretoken]').value;
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
            body: JSON.stringify(body || {})
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) throw new Error(data.error || 'Something went wrong.');
                return data;
            });
        });
    }

    if (typeof paypal === 'undefined') {
        showError('PayPal could not be loaded. Please check your connection and reload the page.');
        return;
    }

    paypal.Buttons({
        style: {layout: 'vertical', shape: 'rect', color: 'gold', label: 'paypal', height: 45, tagline: false},
        createOrder: function () {
            if (message) message.classList.add('hidden');
            return post(container.dataset.createUrl).then(function (data) { return data.id; });
        },
        onApprove: function (data) {
            return post(container.dataset.captureUrl, {orderID: data.orderID}).then(function (result) {
                window.location.href = result.redirect;
            });
        },
        onCancel: function () {
            showError('Payment cancelled. You can try again when you are ready.');
        },
        onError: function (err) {
            showError((err && err.message) || 'The PayPal payment failed. Please try again.');
        }
    }).render('#paypal-button-container');
})();
