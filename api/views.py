from rest_framework import generics, status, permissions,filters
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import *
from django.contrib.auth import login, authenticate
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from .permissions import *
from django.db.models import Count, Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]  
    serializer_class = UserRegisterSerializer
    #The @swagger_auto_schema decorator is used to define how the API documentation should appear for each view.
    @swagger_auto_schema(
        request_body=UserRegisterSerializer,
        responses={
            201: openapi.Response('User registered successfully', UserRegisterSerializer),
            400: 'Bad Request'
        }
    )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Prepare response data
        data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'refresh': str(refresh),
            'access': str(access_token),
        }

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: openapi.Response('Login successful', LoginSerializer),
            401: 'Unauthorized'
        }
    )
    
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful", 
                 'user_id': user.id,
                "token": token.key,
                "username" : username})
        else:
            return Response({"error": "Invalid credentials."}, status=401)
        

class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).annotate(notes_count=models.Count('notes'))

   

class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerCategory]  

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).annotate(notes_count=models.Count('notes'))

    def perform_destroy(self, instance):
        if instance.notes.exists():
            raise ValidationError("Cannot delete a category that has associated notes.")
        instance.delete()        

class NoteListCreateView(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'category']
    ordering_fields = ['created_at', 'updated_at', 'due_date']

    def get_queryset(self):
        return Note.objects.filter(
            models.Q(user=self.request.user) |
            models.Q(shared_with=self.request.user)
        ).distinct().order_by('-updated_at')

   


class NoteRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSharedWith]

    def get_queryset(self):
        return Note.objects.filter(
            models.Q(user=self.request.user) |
            models.Q(shared_with=self.request.user)
        ).distinct().select_related('user').prefetch_related('shared_with')

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise ValidationError("You do not have permission to delete this note.")
        instance.delete()      
        
        
class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'category__name', 'description']
    ordering_fields = ['due_date', 'created_at', 'updated_at']

    def get_queryset(self):
        return Task.objects.filter(
            models.Q(user=self.request.user) |
            models.Q(shared_with=self.request.user)
        ).distinct().order_by('-due_date')



class TaskRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSharedWith]

    def get_queryset(self):
        return Task.objects.filter(
            models.Q(user=self.request.user) |
            models.Q(shared_with=self.request.user)
        ).distinct().select_related('user').prefetch_related('shared_with')

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise ValidationError("You do not have permission to delete this task.")
        instance.delete()  

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()  # Delete the user's token
            return Response({"message": "Successfully logged out."}, status=200)
        except (AttributeError, Token.DoesNotExist):
            return Response({"message": "Logout failed."}, status=400)
