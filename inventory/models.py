from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    """One row per product. product_id is the human-facing unique code
    used throughout the UI (e.g. '101'), separate from Django's internal pk."""

    GST_CHOICES = [
        (0, "0%"),
        (5, "5%"),
        (12, "12%"),
        (18, "18%"),
        (28, "28%"),
    ]

    product_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80)
    brand = models.CharField(max_length=80, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    gst_slab = models.PositiveSmallIntegerField(choices=GST_CHOICES, default=18)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_id"]

    def __str__(self):
        return f"{self.product_id} — {self.name}"

    @property
    def is_low_stock(self):
        return self.quantity < self.low_stock_threshold

    @property
    def stock_value(self):
        return self.selling_price * self.quantity


class Coupon(models.Model):
    """Simple flat/percentage discount coupon used on the Sell Product page."""

    KIND_CHOICES = [("flat", "Flat amount"), ("percent", "Percentage")]

    code = models.CharField(max_length=30, unique=True)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="percent")
    value = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def discount_for(self, subtotal):
        if not self.active:
            return 0
        if self.kind == "percent":
            return round(subtotal * (self.value / 100), 2)
        return min(self.value, subtotal)


class Sale(models.Model):
    """One row per completed sale — mirrors an entry in the console app's
    sales.json / printed bill."""

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_slab = models.PositiveSmallIntegerField(default=18)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sold_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sold_at"]

    def __str__(self):
        return f"Sale #{self.pk} — {self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity