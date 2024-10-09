from rest_framework import permissions

# The `IsOwnerOrSharedWith` class defines a custom permission in Django REST framework that checks if
# the requesting user is the owner of an object or if the object is shared with the user.
class IsOwnerOrSharedWith(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
    # SAFE_METHODS are GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user or request.user in obj.shared_with.all()
        # Write permissions are only allowed to the owner
        return obj.user == request.user

class IsOwnerCategory(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user