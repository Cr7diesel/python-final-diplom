from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from ujson import loads as load_json

from .models import (
    ConfirmEmailToken,
    Category,
    Shop,
    ProductInfo,
    Order,
    OrderItem,
    Contact,
    User,
)
from .permissions import IsShop, IsOwner
from .serializers import (
    UserSerializer,
    CategorySerializer,
    ShopSerializer,
    ProductInfoSerializer,
    OrderSerializer,
    OrderItemSerializer,
    ContactSerializer,
)
from .tasks import do_import, new_user_registered, new_order


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    def post(self, request, *args, **kwargs):
        if {
            "first_name",
            "last_name",
            "email",
            "password",
            "company",
            "position",
        }.issubset(request.data):
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse(
                    {"Status": False, "Errors": {"password": error_array}}
                )
            else:
                request.data.copy()
                request.data.update({})
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data["password"])
                    user.save()
                    new_user_registered.delay(sender=self.__class__,
                                              user_id=user.id)
                    return JsonResponse({"Status": True})
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": user_serializer.errors}
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    throttle_classes = (AnonRateThrottle,)

    def post(self, request, *args, **kwargs):
        if {"email", "token"}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(
                user__email=request.data["email"], key=request.data["token"]
            ).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({"Status": True})
            else:
                return JsonResponse(
                    {"Status": False,
                     "Errors": "Неправильно указан токен или email"}
                )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class AccountDetails(APIView):
    """
    Класс для работы с данными пользователя
    """

    permission_classes = (IsAuthenticated, IsOwner)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if "password" in request.data:
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse(
                    {"Status": False, "Errors": {"password": error_array}}
                )
            else:
                request.user.set_password(request.data["password"])

        user_serializer = UserSerializer(request.user, data=request.data,
                                         partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({"Status": True})
        else:
            return JsonResponse({"Status": False,
                                 "Errors": user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    throttle_classes = (AnonRateThrottle,)

    def post(self, request, *args, **kwargs):
        if {"email", "password"}.issubset(request.data):
            user = authenticate(
                request,
                username=request.data["email"],
                password=request.data["password"],
            )

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({"Status": True, "Token": token.key})

            return JsonResponse({"Status": False,
                                 "Errors": "Не удалось авторизовать"})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class CategoryView(ReadOnlyModelViewSet):
    """
    Класс для просмотра категорий
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ReadOnlyModelViewSet):
    """
    Класс для просмотра списка магазинов
    """

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
    Класс для поиска товаров
    """

    throttle_classes = (AnonRateThrottle,)

    @extend_schema(responses=ProductInfoSerializer)
    def get(self, request, *args, **kwargs):
        query = Q(shop__state=True)
        shop_id = request.query_params.get("shop_id")
        category_id = request.query_params.get("category_id")

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        queryset = (
            ProductInfo.objects.filter(query)
            .select_related("shop", "product__category")
            .prefetch_related("product_parameters__parameter")
            .distinct()
        )

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    @extend_schema(responses=OrderSerializer)
    def get(self, request, *args, **kwargs):
        basket = (
            Order.objects.filter(user_id=request.user.id, state="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    @extend_schema(responses=OrderItemSerializer)
    def post(self, request, *args, **kwargs):
        items_sting = request.data.get("items")
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse(
                    {"Status": False, "Errors": "Неверный формат запроса"}
                )
            else:
                basket, _ = Order.objects.get_or_create(
                    user_id=request.user.id, state="basket"
                )
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({"order": basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({"Status": False,
                                                 "Errors": str(error)})
                        else:
                            objects_created += 1

                    else:
                        return JsonResponse(
                            {"Status": False, "Errors": serializer.errors}
                        )

                return JsonResponse(
                    {"Status": True, "Создано объектов": objects_created}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    @extend_schema()
    def delete(self, request, *args, **kwargs):
        items_sting = request.data.get("items")
        if items_sting:
            items_list = items_sting.split(",")
            basket, _ = Order.objects.get_or_create(
                user_id=request.user.id, state="basket"
            )
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({"Status": True,
                                     "Удалено объектов": deleted_count})
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    @extend_schema()
    def put(self, request, *args, **kwargs):
        items_sting = request.data.get("items")
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse(
                    {"Status": False, "Errors": "Неверный формат запроса"}
                )
            else:
                basket, _ = Order.objects.get_or_create(
                    user_id=request.user.id, state="basket"
                )
                objects_updated = 0
                for order_item in items_dict:
                    if (
                        all([type(order_item["id"]),
                             type(order_item["quantity"])])
                        == int
                    ):
                        objects_updated += OrderItem.objects.filter(
                            order_id=basket.id, id=order_item["id"]
                        ).update(quantity=order_item["quantity"])

                return JsonResponse(
                    {"Status": True, "Обновлено объектов": objects_updated}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика

    """

    permission_classes = (
        IsAuthenticated,
        IsShop,
    )
    throttle_classes = (UserRateThrottle,)

    def post(self, request, *args, **kwargs):
        url = request.data.get("url")
        if url:
            try:
                do_import.delay(url, request.user.id)
            except IntegrityError as error:
                return JsonResponse(
                    {"Status": False, "Errors": f"Integrity error: {error}"}
                )
            return JsonResponse({"Status": True})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class PartnerState(ModelViewSet):
    """
    Класс для работы со статусом поставщика
    """

    permission_classes = (
        IsAuthenticated,
        IsShop,
    )
    throttle_classes = (UserRateThrottle,)
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """

    permission_classes = (
        IsAuthenticated,
        IsShop,
    )
    throttle_classes = (UserRateThrottle,)

    def get(self, request, *args, **kwargs):
        order = (
            Order.objects.filter(
                ordered_items__product_info__shop__user_id=request.user.id
            )
            .exclude(state="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
    Класс для работы с контактами покупателей
    """

    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, *args, **kwargs):
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {"city", "street", "phone"}.issubset(request.data):
            request.data._mutable = True
            request.data.update({"user": request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({"Status": True})
            else:
                return JsonResponse({"Status": False,
                                     "Errors": serializer.errors})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def delete(self, request, *args, **kwargs):
        items_sting = request.data.get("items")
        if items_sting:
            items_list = items_sting.split(",")
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({"Status": True,
                                     "Удалено объектов": deleted_count})
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def put(self, request, *args, **kwargs):
        if "id" in request.data:
            if request.data["id"].isdigit():
                contact = Contact.objects.filter(
                    id=request.data["id"], user_id=request.user.id
                ).first()
                print(contact)
                if contact:
                    serializer = ContactSerializer(
                        contact, data=request.data, partial=True
                    )
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({"Status": True})
                    else:
                        return JsonResponse(
                            {"Status": False, "Errors": serializer.errors}
                        )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class OrderView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    """

    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    @extend_schema(responses=OrderSerializer)
    def get(self, request, *args, **kwargs):
        order = (
            Order.objects.filter(user_id=request.user.id)
            .exclude(state="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    @extend_schema()
    def post(self, request, *args, **kwargs):
        if {"id", "contact"}.issubset(request.data):
            if request.data["id"].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data["id"]
                    ).update(contact_id=request.data["contact"], state="new")
                except IntegrityError as error:
                    print(error)
                    return JsonResponse(
                        {"Status": False,
                         "Errors": "Неправильно указаны аргументы"}
                    )
                else:
                    if is_updated:
                        new_order.delay(sender=self.__class__,
                                        user_id=request.user.id)
                        return JsonResponse({"Status": True})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class ThanksForOrder(APIView):
    """
    Класс спасибо за заказ
    """

    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        user_id = request.user.id
        if user_id:
            user = User.objects.get(id=user_id)
            message = f"{user.username}, Спасибо за ваш заказ!"
            return JsonResponse({"Status": True, "Message": f'{message}'})
        return JsonResponse({"Status": False,
                             "Errors": "Пользователь не найден"})
