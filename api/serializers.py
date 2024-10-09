from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from .models import *
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

class ReminoUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email'] 


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label="Confirm Password",
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(
        required=True,
        validators=[EmailValidator()]
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2')
        extra_kwargs = {
            'username': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        Token.objects.create(user=user) 
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=True,
        write_only=True,
        max_length=150
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    token = serializers.CharField(
        read_only=True
    )
    user_id = serializers.IntegerField(
        read_only=True
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid username or password.")
        else:
            raise serializers.ValidationError("Both username and password are required.")

        attrs['user'] = user
        return attrs
    

   
class CategorySerializer(serializers.ModelSerializer):
    user = ReminoUserSerializer(read_only=True)
    notes_count = serializers.IntegerField(source='notes.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'user', 'name', 'description', 'notes_count', 'created_at']
        read_only_fields = ['id', 'user', 'notes_count', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError({"user": "User must be provided."})
        user = request.user
        return Category.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        # Prevent updating the 'user' field
        validated_data.pop('user', None)
        return super().update(instance, validated_data)


# The `NoteSerializer` class in Python is used to serialize and deserialize Note objects, handling
# fields related to user, sharing, and creation/update operations.
class NoteSerializer(serializers.ModelSerializer):
    user = ReminoUserSerializer(read_only=True)
    shared_with = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        required=False
    )
    shared_users = ReminoUserSerializer(source='shared_with', many=True, read_only=True)

    class Meta:
        model = Note
        fields = [
            'id', 'user', 'title', 'content', 'category',
            'image', 'file', 'is_shared', 'shared_with',
            'shared_users', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'shared_users', 'created_at', 'updated_at']

    def create(self, validated_data):
        shared_with_emails = validated_data.pop('shared_with', [])
        users = User.objects.filter(email__in=shared_with_emails)
        invalid_emails = set(shared_with_emails) - set(users.values_list('email', flat=True))
        if invalid_emails:
            raise serializers.ValidationError({
                "shared_with": f"The following emails are not registered users: {', '.join(invalid_emails)}"
            })
        note = Note.objects.create(**validated_data, user=self.context['request'].user)
        
        if users.exists():
            note.shared_with.set(users)
            note.is_shared = True
            note.save()
            
          # Construct the absolute URL to the note
        request = self.context.get('request')
        if request:
            note_detail_path = reverse('api:note-detail', kwargs={'pk': note.pk})
            note_url = request.build_absolute_uri(note_detail_path)
        else:
           
            note_url = f"{settings.SITE_URL}/api/notes/{note.pk}/"
            
        
        for user in users:
            send_mail(
                subject=f"{self.context['request'].user.username} from REMINO shared a note with you",
                message=f"You have been granted access to the note titled '{note.title}'. You can view the note here: {note_url}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
        return note

    def update(self, instance, validated_data):
        shared_with_emails = validated_data.pop('shared_with', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if shared_with_emails is not None:
            users = User.objects.filter(email__in=shared_with_emails)
            invalid_emails = set(shared_with_emails) - set(users.values_list('email', flat=True))

            if invalid_emails:
                raise serializers.ValidationError({
                    "shared_with": f"The following emails are not registered users: {', '.join(invalid_emails)}"
                })

            if users.exists():
                instance.shared_with.set(users)
                instance.is_shared = True
                
                  # Construct the absolute URL to the note
                request = self.context.get('request')
                if request:
                    note_detail_path = reverse('api:note-detail', kwargs={'pk': instance.pk})
                    note_url = request.build_absolute_uri(note_detail_path)
                else:
                    # Fallback to a default URL if request is not available
                    note_url = f"{settings.SITE_URL}/api/notes/{instance.pk}/"


                # Optionally, send notification emails to new shared users
                for user in users:
                    send_mail(
                        subject=f"{self.context['request'].user.username} shared a note with you",
                        message=f"You have been granted access to the note titled '{instance.title}'.",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
            else:
                instance.shared_with.clear()
                instance.is_shared = False

        instance.save()
        return instance



class TaskSerializer(serializers.ModelSerializer):
    user = ReminoUserSerializer(read_only=True)
    shared_with = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        required=False
    )
    shared_users = ReminoUserSerializer(source='shared_with', many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'user', 'title', 'description', 'due_date', 'is_completed', 'shared_with',
            'shared_users', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'shared_users', 'created_at', 'updated_at']

    def create(self, validated_data):
        shared_with_emails = validated_data.pop('shared_with', [])
        users = User.objects.filter(email__in=shared_with_emails)
        invalid_emails = set(shared_with_emails) - set(users.values_list('email', flat=True))
        if invalid_emails:
            raise serializers.ValidationError({
                "shared_with": f"The following emails are not registered users: {', '.join(invalid_emails)}"
            })
        # Create the task and associate it with the authenticated user
        task = Task.objects.create(**validated_data, user=self.context['request'].user)

        if users.exists():
            task.shared_with.set(users)
            task.is_shared = True
            task.save()

        # Construct the absolute URL to the task detail view
        request = self.context.get('request')
        if request:
            task_detail_path = reverse('api:task-detail', kwargs={'pk': task.pk})
            task_url = f"{settings.SITE_URL}{task_detail_path}"
        else:
            # Fallback to a default URL if request is not available
            task_url = f"{settings.SITE_URL}/api/tasks/{task.pk}/"

        # Send notification emails with the task link
        for user in users:
            send_mail(
                subject=f"{self.context['request'].user.username} from REMINO shared a task with you",
                message=(
                    f"You have been granted access to the task titled '{task.title}'.\n\n"
                    f"You can view the task here: {task_url}"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
        return task

    def update(self, instance, validated_data):
        shared_with_emails = validated_data.pop('shared_with', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if shared_with_emails is not None:
            users = User.objects.filter(email__in=shared_with_emails)
            invalid_emails = set(shared_with_emails) - set(users.values_list('email', flat=True))

            if invalid_emails:
                raise serializers.ValidationError({
                    "shared_with": f"The following emails are not registered users: {', '.join(invalid_emails)}"
                })

            if users.exists():
                instance.shared_with.set(users)
                instance.is_shared = True
                instance.save()

                # Construct the absolute URL to the task detail view
                request = self.context.get('request')
                if request:
                    task_detail_path = reverse('api:task-detail', kwargs={'pk': instance.pk})
                    task_url = f"{settings.SITE_URL}{task_detail_path}"
                else:
                    # Fallback to a default URL if request is not available
                    task_url = f"{settings.SITE_URL}/api/tasks/{instance.pk}/"

                # Optionally, send notification emails to new shared users
                for user in users:
                    send_mail(
                        subject=f"{self.context['request'].user.username} shared a task with you",
                        message=(
                            f"You have been granted access to the task titled '{instance.title}'.\n\n"
                            f"You can view the task here: {task_url}"
                        ),
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
            else:
                instance.shared_with.clear()
                instance.is_shared = False
                instance.save()

        instance.save()
        return instance
    
    
    
    
"""""
UserSerializer: Nested serializer to display user information.

NoteSerializer:

user: Read-only field representing the owner of the note.
shared_with: Write-only field that accepts a list of email addresses to share the note with.
shared_users: Read-only nested serializer to display shared users' details.
create: Overridden to handle sharing logic based on provided email addresses.
update: Similarly handles updates to the shared users.
"""""

