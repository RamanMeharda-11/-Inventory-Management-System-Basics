import csv

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum, F, ProtectedError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal

from .models import Product, Sale, Coupon

LOGIN_ATTEMPT_SESSION_KEY = "login_attempts"
MAX_LOGIN_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def signup_view(request):
    errors = []

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append("That username is already taken.")

        if len(password1) < 6:
            errors.append("Password must be at least 6 characters.")
        elif password1 != password2:
            errors.append("Passwords do not match.")

        if not errors:
            user = User.objects.create_user(username=username, password=password1)
            login(request, user)
            return redirect("dashboard")

        return render(request, "signup.html", {"errors": errors, "username": username})

    return render(request, "signup.html")


def login_view(request):
    attempts = request.session.get(LOGIN_ATTEMPT_SESSION_KEY, 0)

    if attempts >= MAX_LOGIN_ATTEMPTS:
        messages.error(request, "Too many failed attempts. Please try again later.")
        return render(request, "login.html", {"locked": True})

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            request.session[LOGIN_ATTEMPT_SESSION_KEY] = 0
            login(request, user)
            return redirect("dashboard")

        request.session[LOGIN_ATTEMPT_SESSION_KEY] = attempts + 1
        return render(request, "login.html", {"form": {"errors": True}})

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not request.user.check_password(old_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
        elif len(new_password) < 6:
            messages.error(request, "New password must be at least 6 characters.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password updated successfully.")

    return render(request, "change_password.html")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    products = Product.objects.all()
    context = {
        "total_products": products.count(),
        "total_categories": products.values("category").distinct().count(),
        "total_inventory_value": sum(p.stock_value for p in products),
        "low_stock_count": sum(1 for p in products if p.is_low_stock),
        "recent_products": products.order_by("-created_at")[:5],
    }
    return render(request, "dashboard.html", context)


# ---------------------------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------------------------

@login_required
def add_product(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id", "").strip()

        if Product.objects.filter(product_id=product_id).exists():
            messages.error(request, f"Product ID {product_id} already exists.")
            return render(request, "add_product.html")

        Product.objects.create(
            product_id=product_id,
            name=request.POST.get("name", "").strip(),
            category=request.POST.get("category", "").strip(),
            brand=request.POST.get("brand", "").strip(),
            purchase_price=request.POST.get("purchase_price") or 0,
            selling_price=request.POST.get("selling_price") or 0,
            quantity=request.POST.get("quantity") or 0,
            gst_slab=request.POST.get("gst_slab") or 18,
        )
        messages.success(request, "Product added successfully.")
        return redirect("view_products")

    return render(request, "add_product.html")


@login_required
def view_products(request):
    products = Product.objects.all()
    return render(request, "view_products.html", {"products": products})


@login_required
def update_product(request, pk):
    product = get_object_or_404(Product, product_id=pk)

    if request.method == "POST":
        product.name = request.POST.get("name", "").strip()
        product.category = request.POST.get("category", "").strip()
        product.brand = request.POST.get("brand", "").strip()
        product.purchase_price = request.POST.get("purchase_price") or 0
        product.selling_price = request.POST.get("selling_price") or 0
        product.quantity = request.POST.get("quantity") or 0
        product.save()
        messages.success(request, "Product updated successfully.")
        return redirect("view_products")

    return render(request, "update_product.html", {"product": product})


@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            product.delete()
            messages.success(request, "Product deleted.")
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete '{product.name}' — it has past sales recorded against it. "
                "Set its quantity to 0 instead of deleting it."
            )
    return redirect("view_products")


@login_required
def search_product(request):
    query = request.GET.get("q", "").strip()
    search_by = request.GET.get("search_by", "id")
    results = None

    if query:
        if search_by == "id":
            results = Product.objects.filter(product_id__icontains=query)
        elif search_by == "name":
            results = Product.objects.filter(name__icontains=query)
        else:
            results = Product.objects.filter(category__icontains=query)

    return render(request, "search_product.html", {
        "query": query,
        "search_by": search_by,
        "results": results,
    })


# ---------------------------------------------------------------------------
# Selling / billing
# ---------------------------------------------------------------------------

@login_required
def sell_product(request):
    bill = None

    if request.method == "POST":
        product_id = request.POST.get("product_id", "").strip()
        quantity = int(request.POST.get("quantity") or 0)
        gst_slab = int(request.POST.get("gst_slab") or 18)
        coupon_code = request.POST.get("coupon_code", "").strip()

        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product Not Found.")
            return render(request, "sell_product.html")

        if quantity <= 0 or quantity > product.quantity:
            messages.error(request, "Not enough stock available for this quantity.")
            return render(request, "sell_product.html")

        subtotal = product.selling_price * quantity
        gst_amount = round(subtotal * (Decimal(gst_slab) / 100), 2)

        discount_amount = 0
        if coupon_code:
            coupon = Coupon.objects.filter(code__iexact=coupon_code, active=True).first()
            if coupon:
                discount_amount = coupon.discount_for(subtotal)
            else:
                messages.error(request, "Coupon code not valid.")

        grand_total = subtotal + gst_amount - discount_amount

        product.quantity = F("quantity") - quantity
        product.save()
        product.refresh_from_db()

        sale = Sale.objects.create(
            product=product,
            quantity=quantity,
            unit_price=product.selling_price,
            gst_slab=gst_slab,
            gst_amount=gst_amount,
            discount_amount=discount_amount,
            coupon_code=coupon_code,
            grand_total=grand_total,
            sold_by=request.user,
        )

        bill = {
            "product_name": product.name,
            "price": product.selling_price,
            "quantity": quantity,
            "subtotal": subtotal,
            "gst_amount": gst_amount,
            "discount": discount_amount,
            "grand_total": grand_total,
        }

    return render(request, "sell_product.html", {"bill": bill})


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@login_required
def low_stock_report(request):
    low_stock_products = [p for p in Product.objects.all() if p.is_low_stock]
    return render(request, "low_stock_report.html", {
        "low_stock_products": low_stock_products,
    })


@login_required
def inventory_summary(request):
    products = Product.objects.all()
    category_breakdown = (
        products.values("category")
        .annotate(
            product_count=Count("id"),
            total_stock=Sum("quantity"),
            stock_value=Sum(F("selling_price") * F("quantity")),
        )
        .order_by("category")
    )

    context = {
        "total_products": products.count(),
        "total_categories": products.values("category").distinct().count(),
        "total_stock": products.aggregate(total=Sum("quantity"))["total"] or 0,
        "total_inventory_value": sum(p.stock_value for p in products),
        "category_breakdown": [
            {
                "category": row["category"],
                "product_count": row["product_count"],
                "total_stock": row["total_stock"],
                "stock_value": row["stock_value"],
            }
            for row in category_breakdown
        ],
    }
    return render(request, "inventory_summary.html", context)


@login_required
def sales_report(request):
    sales = Sale.objects.all()
    top_products = (
        Sale.objects.values("product__name")
        .annotate(units_sold=Sum("quantity"), revenue=Sum("grand_total"))
        .order_by("-units_sold")[:10]
    )

    context = {
        "total_sales": sales.count(),
        "products_sold": sales.aggregate(total=Sum("quantity"))["total"] or 0,
        "revenue_generated": sales.aggregate(total=Sum("grand_total"))["total"] or 0,
        "range": request.GET.get("range", "daily"),
        "top_products": [
            {"name": row["product__name"], "units_sold": row["units_sold"], "revenue": row["revenue"]}
            for row in top_products
        ],
    }
    return render(request, "sales_report.html", context)


@login_required
def export_sales_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Sale ID", "Product", "Quantity", "Unit Price", "GST", "Discount", "Grand Total", "Sold At"])

    for sale in Sale.objects.select_related("product").all():
        writer.writerow([
            sale.pk, sale.product.name, sale.quantity, sale.unit_price,
            sale.gst_amount, sale.discount_amount, sale.grand_total, sale.sold_at,
        ])

    return response