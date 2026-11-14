// Interactive star picker with half-star support (click the left half of a star for x.5).
(function () {
    var widget = document.getElementById('star-rating');
    if (!widget) return;
    var input = document.getElementById('id_rating');
    var text = document.getElementById('rating-text');
    var slots = widget.querySelectorAll('.star-slot');
    var value = parseFloat(input.value) || 0;

    function paint(rating) {
        slots.forEach(function (slot, i) {
            var fill = slot.querySelector('.star-fill');
            var portion = Math.max(0, Math.min(1, rating - i));
            fill.style.width = (portion * 100) + '%';
        });
        text.textContent = rating ? rating.toFixed(1) + ' / 5' : '';
    }

    function set(rating) {
        value = Math.max(0.5, Math.min(5, rating));
        input.value = value.toFixed(1);
        widget.setAttribute('aria-valuenow', value);
        paint(value);
    }

    function valueAt(slot, event) {
        var rect = slot.getBoundingClientRect();
        var index = parseInt(slot.dataset.star, 10);
        return (event.clientX - rect.left) < rect.width / 2 ? index - 0.5 : index;
    }

    slots.forEach(function (slot) {
        slot.addEventListener('mousemove', function (e) { paint(valueAt(slot, e)); });
        slot.addEventListener('click', function (e) { set(valueAt(slot, e)); });
    });
    widget.addEventListener('mouseleave', function () { paint(value); });
    widget.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { e.preventDefault(); set((value || 0) + 0.5); }
        if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { e.preventDefault(); set((value || 1) - 0.5); }
    });
    document.getElementById('review-form').addEventListener('submit', function (e) {
        if (!value) {
            e.preventDefault();
            text.textContent = 'Please choose a rating';
            widget.focus();
        }
    });
    paint(value);
})();
