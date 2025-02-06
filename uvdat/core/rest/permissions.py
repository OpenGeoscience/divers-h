from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAdminUser, IsAuthenticated


class IsReadOnlyEndpoint(BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS


DefaultPermission = IsAuthenticated & (IsReadOnlyEndpoint | IsAdminUser)
