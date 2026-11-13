from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'size', 'color', 'price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'full_name', 'total', 'payment_method', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'email', 'first_name', 'last_name')
    list_editable = ('status', 'payment_status')
    readonly_fields = ('order_number', 'paypal_order_id', 'transaction_id', 'subtotal', 'tax_total', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
