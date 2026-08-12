# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Product, Sale, Coupon


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "name", "category", "brand", "selling_price", "quantity")
    search_fields = ("product_id", "name", "category")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "quantity", "grand_total", "sold_at")
    list_filter = ("sold_at",)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "kind", "value", "active")