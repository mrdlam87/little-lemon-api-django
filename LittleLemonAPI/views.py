from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from datetime import date
from .models import Category, MenuItem, Cart, Order
from .serializers import CategorySerializer, MenuItemSerializer, UserSerializer, CartSerializer, OrderSerializer, OrderItemSerializer
from .paginations import StandardResultsSetPagination


# Create your views here.

class CatergoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if (self.request.method == 'GET'):
            return [IsAuthenticated()]

        return [IsAdminUser()]


class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['price', 'title']
    search_fields = ['title']
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if (self.request.method == 'GET'):
            return [IsAuthenticated()]

        return [IsAdminUser()]

    def get_queryset(self):
        queryset = MenuItem.objects.all()
        featured = self.request.query_params.get("featured")
        category = self.request.query_params.get("category")
        perpage = self.request.query_params.get("perpage")
        if featured:
            queryset = queryset.filter(featured=featured)
        if category:
            queryset = queryset.filter(category__title=category)
        if perpage:
            self.pagination_class.page_size = perpage

        return queryset


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if (self.request.method == 'GET'):
            return [IsAuthenticated()]

        return [IsAdminUser()]


class ManagerUsersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        managers = User.objects.filter(groups__name='manager').all()
        serializer = UserSerializer(managers, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        username = request.data['username']
        if username:
            user = get_object_or_404(User, username=username)
            managers = Group.objects.get(name="manager")
            managers.user_set.add(user)
            return Response({"message": "ok"})

        return Response({"message": "error"}, status.HTTP_400_BAD_REQUEST)


class SingleManagerUserView(APIView):
    def delete(self, request, pk, *args, **kwargs):
        if pk:
            user = get_object_or_404(User, id=pk)
            managers = Group.objects.get(name="manager")
            managers.user_set.remove(user)
            return Response({"message": "ok"})

        return Response({"message": "error"}, status.HTTP_400_BAD_REQUEST)


class DeliveryUsersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        managers = User.objects.filter(groups__name='delivery crew').all()
        serializer = UserSerializer(managers, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        username = request.data['username']
        if username:
            user = get_object_or_404(User, username=username)
            managers = Group.objects.get(name="delivery crew")
            managers.user_set.add(user)
            return Response({"message": "ok"})

        return Response({"message": "error"}, status.HTTP_400_BAD_REQUEST)


class SingleDeliveryUserView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk, *args, **kwargs):
        if pk:
            user = get_object_or_404(User, id=pk)
            delivery_crew = Group.objects.get(name="delivery crew")
            delivery_crew.user_set.remove(user)
            return Response({"message": "ok"})

        return Response({"message": "error"}, status.HTTP_400_BAD_REQUEST)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        carts = Cart.objects.filter(user_id=user.id)

        serializer = CartSerializer(carts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        menuitem = MenuItem.objects.get(id=request.data.get("menuitem_id"))
        quantity = int(request.data.get("quantity"))
        data = {
            "user_id": request.user.id,
            "menuitem_id": menuitem.id,
            "unit_price": menuitem.price,
            "price": menuitem.price * quantity,
            "quantity": quantity
        }

        serializer = CartSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        user = request.user
        Cart.objects.filter(user_id=user.id).delete()
        return Response({"message": "ok"}, status=status.HTTP_200_OK)


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        orders = []
        if user.groups.filter(
                name="manager").exists():
            orders = Order.objects.all()
        elif user.groups.filter(
                name="delivery crew").exists():
            orders = Order.objects.filter(delivery_crew_id=user.id)
        else:
            orders = Order.objects.filter(user_id=user.id)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = request.user
        cart_items = Cart.objects.filter(user_id=user.id)

        if not cart_items.exists():
            return Response({"message": "cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        order_data = {
            "user_id": user.id,
            "total": sum([int(n) for n in cart_items.values_list("price", flat=True)]),
            "date": date.today()
        }

        order_serializer = OrderSerializer(data=order_data)
        if order_serializer.is_valid():
            order = order_serializer.save()

            for item in cart_items:
                data = {
                    "order_id": order.id,
                    "menuitem_id": item.menuitem.pk,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "price": item.price
                }
                serializer = OrderItemSerializer(data=data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            cart_items.delete()
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)

        return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SingleOrderView(APIView):
    def is_in_group(self, user_id, group_name):
        try:
            return Group.objects.get(name=group_name).user_set.filter(id=user_id).exists()
        except Group.DoesNotExist:
            return None

    def get_permissions(self):
        if (self.request.method == 'DELETE' or self.request.method == 'PUT'):
            return [IsAdminUser()]

        return [IsAuthenticated()]

    def get(self, request, pk, *args, **kwargs):
        user = request.user
        user_orders = Order.objects.filter(user_id=user.id)
        order = get_object_or_404(user_orders, id=pk)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk, *args, **kwargs):
        user = request.user
        if not self.is_in_group(user.id, "manager") and not self.is_in_group(user.id, "delivery crew"):
            return Response({"message": "not from correct user group"}, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=pk)
        data = {
            "status": request.data.get("status")
        }

        serializer = OrderSerializer(instance=order, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order, id=pk)
        delivery_crew_id = request.data.get("delivery_crew_id")
        status_value = request.data.get("status")
        data = {}

        if delivery_crew_id:
            if not self.is_in_group(delivery_crew_id, "delivery crew"):
                return Response({"message": "not a valid delivery crew"}, status=status.HTTP_400_BAD_REQUEST)
            data["delivery_crew_id"] = delivery_crew_id
        if status_value:
            data["status"] = status_value

        serializer = OrderSerializer(instance=order, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order, id=pk)
        order.delete()
        return Response({"message": "ok"}, status=status.HTTP_200_OK)
