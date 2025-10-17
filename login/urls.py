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

    path("decrement-cart/<int:cart_item_id>/", views.decrement_cart, name="decrement_cart"),
    path("increment-cart/<int:product_id>/", views.increment_cart, name="increment_cart"),

    path("lost-found/", views.lost_found, name="lost_found"),
    path("lost-found/report/", views.report_item, name="report_item"),
    path("lost-found/<int:item_id>/claim/", views.submit_claim, name="submit_claim"),

    path('campus-map/', views.campus_map, name='campus_map'),

    # APIs
    path('api/graph/<int:floor>/', views.api_graph, name='api_graph'),
    path('api/route/', views.api_route, name='api_route'),
    path('api/save-location/', views.api_save_location, name='api_save_location'),

    path("", lambda request: redirect("login"), name="home"),
    path("events/", views.events, name="events"),
    path("events/delete/<int:pin_id>/", views.delete_pin, name="delete_pin"),

    # Legacy APIs for compatibility
    path("api/my-saved-locations/", views.api_my_saved_locations, name="api_my_saved_locations"),
     path("api/chatbot/", views.gemini_chat_api, name="gemini_chat_api"),
    path("chatbot/", views.chatbot_page, name="chatbot_page"),

    # Add to urlpatterns in urls.py
    
  

    path('lostfound/approve/', views.approve_lostfound_list, name='approve_lostfound_list'),
    path('lostfound/approve/<int:report_id>/<str:action>/', views.approve_lostfound_action, name='approve_lostfound_action'),
]