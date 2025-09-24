from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
    path("", lambda request: redirect("login")),
    path("register/", views.register, name="register"),
    path("login/", views.login_request, name="login"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("shop/", views.shop, name="shop"),
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart, name="cart"),
    path("remove-from-cart/<int:cart_item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("add-product/", views.add_product, name="add_product"),
    path("delete-product/<int:product_id>/", views.delete_product, name="delete_product"),
    path("logout/", views.logout, name="logout"),
    path("payment/", views.payment, name="payment"),
    path("process-payment/", views.process_payment, name="process_payment"),
    path("payment-success/<int:order_id>/", views.payment_success, name="payment_success"),
    path("payment-failure/", views.payment_failure, name="payment_failure"),
    path("return-request/", views.return_request, name="return_request"),
    path("approve-orders/", views.approve_orders, name="approve_orders"),
]