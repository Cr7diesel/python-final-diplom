from rest_framework import serializers
from .models import (
    Contact,
    User,
    Category,
    Shop,
    Product,
    ProductParameter,
    ProductInfo,
    OrderItem,
    Order,
)


class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализуем контакты
    """

    class Meta:
        model = Contact
        fields = "__all__"
        read_only_fields = ("id",)
        extra_kwargs = {"user": {"write_only": True}}


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализуем пользователей
    """

    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "position",
            "contacts",
        )
        read_only_fields = ("id",)


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализуем категории
    """

    class Meta:
        model = Category
        fields = ("id", "name")
        read_only_fields = ("id",)


class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализуем магазины
    """

    state = serializers.BooleanField(default=True)
    name = serializers.StringRelatedField(required=False)
    url = serializers.URLField(required=False)

    class Meta:
        model = Shop
        fields = ("id", "name", "url", "state")
        read_only_fields = ("id",)


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализуем продукты
    """

    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ("name", "category")


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализуем параметры продуктов
    """

    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ("parameter", "value")


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Сериализуем информацию о продуктах
    """

    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = (
            "id",
            "model",
            "product",
            "shop",
            "quantity",
            "price",
            "price_rrc",
            "product_parameters",
        )
        read_only_fields = ("id",)


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализуем товары в заказе
    """

    class Meta:
        model = OrderItem
        fields = "__all__"
        read_only_fields = ("id",)
        extra_kwargs = {"order": {"write_only": True}}


class OrderItemCreateSerializer(OrderItemSerializer):
    """
    Сериализуем создание продуктов в заказе
    """

    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализуем заказ
    """

    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ("id", "ordered_items", "state", "created_at",
                  "total_sum", "contact")
