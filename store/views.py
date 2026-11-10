from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404
from .models import Product, Review
from category.models import Category

def home(request):
    products = Product.objects.all().filter(is_available=True)
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

    categories = Category.objects.all()
    context = {
        'products': products,
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
    context = {
        'product': product,
        'reviews': reviews,
        'sizes': Product.SIZE_CHOICES,
        'colors': Product.COLOR_CHOICES,
    }
    return render(request, 'store/product_detail.html', context)