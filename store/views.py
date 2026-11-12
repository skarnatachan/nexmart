from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404
from .models import Product, Review
from category.models import Category
from carts.models import Cart

def _one_per_product_name(products_qs):
    """Collapse variant rows sharing a product_name into a single representative,
    preferring an in-stock variant so the listing doesn't lead with a dead end."""
    seen = set()
    representatives = []
    for product in products_qs.order_by('product_name', '-stock', 'id'):
        if product.product_name in seen:
            continue
        seen.add(product.product_name)
        representatives.append(product)
    return representatives

def _best_variant(matches):
    return max(matches, key=lambda v: v.stock, default=None)

def _variant_links(product, variants):
    color_links = []
    for value, label in Product.COLOR_CHOICES:
        matches = [v for v in variants if v.color == value]
        same_size = [v for v in matches if v.size == product.size]
        color_links.append((value, label, _best_variant(same_size) or _best_variant(matches)))

    size_links = []
    for value, label in Product.SIZE_CHOICES:
        matches = [v for v in variants if v.size == value]
        same_color = [v for v in matches if v.color == product.color]
        size_links.append((value, label, _best_variant(same_color) or _best_variant(matches)))

    return color_links, size_links

def _cart_quantities(request):
    session_key = request.session.session_key
    if not session_key:
        return {}
    cart_obj = Cart.objects.filter(cart_id=session_key).first()
    if not cart_obj:
        return {}
    return dict(cart_obj.items.filter(is_active=True).values_list('product_id', 'quantity'))

def home(request):
    products = _one_per_product_name(Product.objects.filter(is_available=True))
    quantities = _cart_quantities(request)
    for product in products:
        product.cart_quantity = quantities.get(product.id, 0)
    context = {'products': products}
    return render(request, 'store/home.html', context)

def _parse_price(raw):
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None

def store(request, category_slug=None):
    products = Product.objects.filter(is_available=True)

    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        selected_categories = [category_slug]
    else:
        selected_categories = request.GET.getlist('category')
        if selected_categories:
            products = products.filter(category__slug__in=selected_categories)

    price_min_raw = request.GET.get('price_min', '')
    price_max_raw = request.GET.get('price_max', '')
    price_min = _parse_price(price_min_raw)
    price_max = _parse_price(price_max_raw)
    if price_min is not None:
        products = products.filter(price__gte=price_min)
    if price_max is not None:
        products = products.filter(price__lte=price_max)

    selected_sizes = request.GET.getlist('size')
    if selected_sizes:
        products = products.filter(size__in=selected_sizes)

    representatives = _one_per_product_name(products)
    quantities = _cart_quantities(request)
    for rep in representatives:
        rep.cart_quantity = quantities.get(rep.id, 0)

    categories = Category.objects.all()
    context = {
        'products': representatives,
        'categories': categories,
        'category': category,
        'selected_categories': selected_categories,
        'selected_sizes': selected_sizes,
        'price_min': price_min_raw,
        'price_max': price_max_raw,
    }
    return render(request, 'store/store.html', context)

def product_detail(request, category_slug=None, product_slug=None):
    product = get_object_or_404(
        Product, slug=product_slug, category__slug=category_slug, is_available=True
    )
    reviews = product.reviews.all()
    variants = [v for v in product.variants() if v.stock > 0]
    color_links, size_links = _variant_links(product, variants)

    cart_quantity = _cart_quantities(request).get(product.id, 0)

    context = {
        'product': product,
        'reviews': reviews,
        'color_links': color_links,
        'size_links': size_links,
        'cart_quantity': cart_quantity,
    }
    return render(request, 'store/product_detail.html', context)