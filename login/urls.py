from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
    path("", lambda request: redirect("login"), name="home"),
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
    path("chat/", views.chat, name="chat"),
    path("create-group/", views.create_group, name="create_group"),
    path("send-message/", views.send_message, name="send_message"),
    path("add-reaction/", views.add_reaction, name="add_reaction"),
    path("campus-map/", views.campus_map, name="campus_map"),
    path("lost-and-found/", views.lost_and_found, name="lost_and_found"),
    path("add-lost-and-found/", views.add_lost_and_found, name="add_lost_and_found"),
    path("lost-and-found-map/", views.lost_and_found_map, name="lost_and_found_map"),
]