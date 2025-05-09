from functools import wraps
from django.contrib.auth import authenticate
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from clerk_backend_api import Clerk, AuthenticateRequestOptions
from django.conf import settings

clerk_client = Clerk(bearer_auth=settings.CLERK_API_SECRET_KEY)

class JwtAuthBackend(BaseBackend):
    def authenticate(self, request, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            request.error_message = "No Authorization token found"
            return None

        try:
            request_state = clerk_client.authenticate_request(
                request,
                AuthenticateRequestOptions(
                    authorized_parties=settings.CLERK_AUTHORIZED_PARTIES
                )
            )

            if not request_state.is_signed_in:
                request.error_message = request_state.message or "Not signed in"
                return None

            payload = request_state.payload
            user = AnonymousUser()
            user.username = payload.get("user_id") or payload.get("sub")
            user.email = payload.get("email", "")
            user.full_name = payload.get("full_name", "")
            user.image_url = payload.get("image_url", "")
            user.clerk_org_id = payload.get("org_id") or payload.get("o", {}).get("id", "")

            # ✅ Normalize role: remove "org:" prefix if present
            raw_role = payload.get("org_role") or payload.get("o", {}).get("rol", "")
            user.clerk_org_role = raw_role.replace("org:", "")  # => "admin", "super_admin", etc.

            user.clerk_permissions = (
                payload.get("user_permissions") or
                payload.get("org_permissions") or
                []
            )

            return user
        except Exception as e:
            request.error_message = f"Unable to authenticate user: {str(e)}"
            return None

    def get_user(self, user_id):
        return None

from .models import BreakGlassUser

def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = authenticate(request)
        if not user:
            return JsonResponse({'detail': getattr(request, 'error_message', 'Unauthorized')}, status=401)

        org_id = getattr(user, "clerk_org_id", "")
        email = getattr(user, "email", "")
        role = getattr(user, "clerk_org_role", "")

        is_exception = (
            role == "super_admin"
            or BreakGlassUser.objects.filter(organization_id=org_id, email=email, is_active=True).exists()
        )

        user.is_break_glass = is_exception
        request.user = user
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def role_required(roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            role = getattr(request.user, "clerk_org_role", None)
            if role not in roles:
                return JsonResponse({"detail": "Forbidden: insufficient role"}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_permission(required_permission):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            permissions = getattr(request.user, "clerk_permissions", [])
            if required_permission not in permissions:
                return JsonResponse({"detail": "Forbidden: insufficient permission"}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator