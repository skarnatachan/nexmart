from decimal import Decimal

from django import template

register = template.Library()


@register.inclusion_tag('store/_stars.html')
def stars(rating, size='h-4 w-4'):
    """Render a read-only 5-star display; supports half stars."""
    value = Decimal(rating or 0)
    states = []
    for i in range(1, 6):
        if value >= i:
            states.append('full')
        elif value >= i - Decimal('0.5'):
            states.append('half')
        else:
            states.append('empty')
    return {'states': states, 'size': size, 'rating': value}
