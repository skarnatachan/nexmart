from django.contrib import admin
from .models import Product, Review, Tax

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'category', 'size', 'color', 'price', 'stock', 'is_available', 'updated_at')
    list_filter = ('size', 'color', 'category', 'is_available')

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'created_at')
    list_filter = ('product',)
    search_fields = ('name', 'comment')

class TaxAdmin(admin.ModelAdmin):
    list_display = ('tax_value', 'is_active', 'updated_at')
    list_filter = ('is_active',)

admin.site.register(Product, ProductAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Tax, TaxAdmin)
