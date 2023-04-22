import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from orders.backend.models import User, Shop, Order, Category, Product, ProductInfo
from orders.backend.serializers import ShopSerializer, CategorySerializer


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(client):
    data = {
        'username': 'user1',
        'email': 'test_email@mail.ru',
        'password': 'test1234'
    }
    user = User.objects.create_user(**data)
    client.force_login(user)
    return user


@pytest.fixture
def token(client, user):
    Token.objects.create(user=user)
    token = Token.objects.get(user=user)
    return token


@pytest.fixture
def auth_client(client, user, token):
    client.force_authenticate(user=user, token=token)
    return client


@pytest.fixture
def partner(client):
    data = {
        'email': 'partner_email@mail.ru',
        'password': 'partner_pass',
        'user_type': 'shop'
    }
    partner = User.objects.create_user(**data)
    client.force_login(partner)
    return partner


@pytest.fixture
def partner_token(client, partner):
    Token.objects.create(user=partner)
    token_partner = Token.objects.get(user=partner)
    return token_partner


@pytest.fixture
def auth_partner(client, partner, partner_token):
    client.force_authenticate(user=partner, token=partner_token)
    return client


@pytest.fixture
def shop_factory(partner):
    def factory(**kwargs):
        return baker.make(Shop, user=partner, **kwargs)
    return factory


@pytest.fixture
def order_factory():
    def factory(**kwargs):
        return baker.make(Order, **kwargs)
    return factory


@pytest.fixture
def category_factory():
    def factory(**kwargs):
        return baker.make(Category, **kwargs)
    return factory


@pytest.fixture
def product_info_factory():
    def factory(**kwargs):
        category = baker.make(Category, **kwargs)
        product = baker.make(Product, category_id=category.id, **kwargs)
        shop = baker.make(Shop, **kwargs)
        return baker.make(ProductInfo, product_id=product.id, shop_id=shop.id, **kwargs)
    return factory


@pytest.mark.django_db
def test_get_basket(user, auth_client, order_factory):
    order_factory(make_m2m=True, user=user)
    url = reverse('basket')
    response = auth_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_into_basket(user, auth_client, order_factory, product_info_factory):
    product = product_info_factory(make_m2m=True)
    order_factory(make_m2m=True, user=user)
    url = reverse('basket')
    response = auth_client.post(
        url, {'products': f'({{"product_info": {product.id}, "quantity": "1"}})'})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json['Status'] is True


@pytest.mark.django_db
def test_get_partner_status(auth_partner, shop_factory):
    shop = shop_factory(make_m2m=True)
    url = reverse('partner-state')
    response = auth_partner.get(url)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json['id'] == shop.id
    assert response_json['state'] == shop.state


@pytest.mark.django_db
def test_partner_update_status(auth_partner, shop_factory):
    shop_factory(make_m2m=True)
    url = reverse('partner-state')
    response = auth_partner.post(url, {'state': True})
    response_json = response.json()
    assert response.status_code == 200
    assert response_json['Status'] is True


@pytest.mark.django_db
def test_get_shop(client, shop_factory):
    shop = shop_factory(make_m2m=True)
    url = reverse('shops')
    response = client.get(url)
    response_json = response.json()
    serializer_data = ShopSerializer(shop, many=True).data
    assert response.status_code == 200
    assert response_json.data == serializer_data


@pytest.mark.django_db
def test_get_categories(client, category_factory):
    category = category_factory(make_m2m=True)
    url = reverse('categories')
    response = client.get(url)
    response_json = response.json()
    serializer_data = CategorySerializer(category, many=True).data
    assert response.status_code == 200
    assert response_json.data == serializer_data


@pytest.mark.django_db
def test_thanks(auth_client):
    url = reverse('thanks')
    response = auth_client.get(url)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json['Message'] == 'user1, Спасибо за ваш заказ!'
