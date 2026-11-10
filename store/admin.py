from django.contrib import admin
from .models import Product, Review

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'category', 'size', 'color', 'price', 'stock', 'is_available', 'updated_at')
    list_filter = ('size', 'color', 'category', 'is_available')
    prepopulated_fields = {'slug': ('product_name',)}

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'created_at')
    list_filter = ('product',)
    search_fields = ('name', 'comment')

admin.site.register(Product, ProductAdmin)
admin.site.register(Review, ReviewAdmin)
