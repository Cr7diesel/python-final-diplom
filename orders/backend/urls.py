from .views import (
    ShopView,
    CategoryView,
    PartnerState,
    PartnerUpdate,
    PartnerOrders,
    RegisterAccount,
    ConfirmAccount,
    AccountDetails,
    ContactView,
    LoginAccount,
    ProductInfoView,
    BasketView,
    OrderView,
    ThanksForOrder,
)
from django.urls import path
from django_rest_passwordreset.views import (
    reset_password_request_token,
    reset_password_confirm,
)
from rest_framework.routers import DefaultRouter

app_name = "backend"

r = DefaultRouter()
r.register("shops", ShopView, basename="shops",)
r.register("categories", CategoryView, basename="categories",)
r.register("partner/state", PartnerState, basename="partner-state",)


urlpatterns = [
    path("partner/update", PartnerUpdate.as_view(), name="partner-update"),
    path("partner/orders", PartnerOrders.as_view(), name="partner-orders"),
    path("user/register", RegisterAccount.as_view(), name="user-register"),
    path(
        "user/register/confirm", ConfirmAccount.as_view(),
        name="user-register-confirm"
    ),
    path("user/details", AccountDetails.as_view(), name="user-details"),
    path("user/contact", ContactView.as_view(), name="user-contact"),
    path("user/login", LoginAccount.as_view(), name="user-login"),
    path("user/password_reset", reset_password_request_token,
         name="password-reset"),
    path(
        "user/password_reset/confirm",
        reset_password_confirm,
        name="password-reset-confirm",
    ),
    path("products", ProductInfoView.as_view(), name="shops"),
    path("basket", BasketView.as_view(), name="basket"),
    path("order", OrderView.as_view(), name="order"),
    path("thanks", ThanksForOrder.as_view(), name="thanks"),
] + r.urls
