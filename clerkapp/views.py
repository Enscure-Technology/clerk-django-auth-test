import json
from django.http import JsonResponse, HttpResponseRedirect
from django.conf import settings
from clerk_backend_api import Clerk
from clerkapp.auth import jwt_required, role_required, require_permission
from .models import BreakGlassUser
clerk_client = Clerk(bearer_auth=settings.CLERK_API_SECRET_KEY)

@jwt_required
def root_router(request):
    role = getattr(request.user, "clerk_org_role", "")
    if role in ["admin", "super_admin"]:
        return HttpResponseRedirect("/index.html")
    elif role == "member":
        return HttpResponseRedirect("/member.html")
    return JsonResponse({"detail": "Invalid role or unauthorized"}, status=403)

@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def configure_sso(request):
    return JsonResponse({"message": "Configure SSO endpoint (Super Admin only)"})

@jwt_required
@role_required(["admin", "super_admin"])
def list_org_members(request):
    try:
        org_id = getattr(request.user, "clerk_org_id", None)
        print("DEBUG: Org ID →", org_id)

        if not org_id:
            return JsonResponse({"detail": "Organization ID missing from user"}, status=400)

        response = clerk_client.organization_memberships.list(organization_id=org_id)
        members = response.data  # ✅ use the .data attribute

        print("DEBUG: Fetched", len(members), "members")

        user_data = [
            {
                "user_id": m.public_user_data.user_id,
                "email": m.public_user_data.identifier,
                "role": m.role,
            }
            for m in members
        ]

        return JsonResponse({"members": user_data})

    except Exception as e:
        print("❌ ERROR in list_org_members:", str(e))
        return JsonResponse({"error": str(e)}, status=500)

@jwt_required
def clerk_jwt(request):
    user = request.user
    return JsonResponse({
        "user_id": user.username,
        "email": user.email,
        "full_name": getattr(user, "full_name", ""),
        "org_id": getattr(user, "clerk_org_id", ""),
        "role": getattr(user, "clerk_org_role", ""),
        "permissions": getattr(user, "clerk_permissions", []),
    })

@jwt_required
@role_required(["admin", "super_admin"])
def settings_view(request):
    return JsonResponse({"message": "Settings landing page"})

from django.views.decorators.csrf import csrf_exempt

# ─────────────── SAML CONFIG ───────────────

@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def list_saml_connections(request):
    try:
        response = clerk_client.saml_connections.list()
        connections = response.data

        base_url = "https://clerk.accounts.dev"  # Replace when you deploy

        detailed = []
        for conn in connections:
            connection_id = getattr(conn, "id", "")

            # Build SP URLs
            sp_metadata_url = f"{base_url}/saml/sso/{connection_id}/metadata"
            acs_url = f"{base_url}/saml/sso/{connection_id}/acs"
            initiate_login_url = f"{base_url}/saml/sso/{connection_id}/login"

            # Safe access to attribute mapping
            mapping = getattr(conn, "attribute_mapping", None)
            attr_map = {
                "email": getattr(mapping, "email", "") if mapping else "",
                "first_name": getattr(mapping, "first_name", "") if mapping else "",
                "last_name": getattr(mapping, "last_name", "") if mapping else "",
            }

            detailed.append({
                "id": connection_id,
                "name": getattr(conn, "name", ""),
                "domain": getattr(conn, "domain", ""),
                "created_at": getattr(conn, "created_at", None),
                "service_provider": {
                    "entity_id": sp_metadata_url,
                    "acs_url": acs_url,
                    "metadata_url": sp_metadata_url,
                    "initiate_login_url": initiate_login_url,
                },
                "identity_provider": {
                    "metadata_url": getattr(conn, "metadata_url", ""),
                    "entity_id": getattr(conn, "idp_entity_id", ""),
                    "sso_url": getattr(conn, "idp_sso_url", ""),
                    "certificate": getattr(conn, "idp_certificate", ""),
                },
                "attribute_mapping": attr_map,
            })

        return JsonResponse({"connections": detailed})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

import requests

@csrf_exempt
@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def create_saml_connection(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body)
        metadata_url = body.get("metadata_url")

        if not metadata_url:
            return JsonResponse({"detail": "metadata_url is required"}, status=400)

        headers = {
            "Authorization": f"Bearer {settings.CLERK_API_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "metadata_url": metadata_url
        }

        res = requests.post(
            "https://api.clerk.com/v1/saml_connections",
            headers=headers,
            json=payload
        )

        if res.status_code >= 400:
            return JsonResponse({"error": res.json()}, status=res.status_code)

        return JsonResponse(res.json())

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def delete_saml_connection(request, conn_id):
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        clerk_client.saml_connections.delete(id=conn_id)
        return JsonResponse({"status": "deleted"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def list_break_glass_users(request):
    org_id = getattr(request.user, "clerk_org_id", "")
    users = BreakGlassUser.objects.filter(organization_id=org_id, is_active=True)
    return JsonResponse({
        "users": [{"email": user.email} for user in users]
    })

@csrf_exempt
@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def create_break_glass_user(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body)
        email = body.get("email", "").strip()
        org_id = getattr(request.user, "clerk_org_id", "")

        if not email:
            return JsonResponse({"detail": "Email is required"}, status=400)

        user, created = BreakGlassUser.objects.get_or_create(
            email=email,
            organization_id=org_id,
            defaults={"is_active": True},
        )

        if not created:
            user.is_active = True
            user.save()

        return JsonResponse({"status": "added", "email": email})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@csrf_exempt
@jwt_required  # or use a public route if email-only is fine
def is_break_glass_user(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip().lower()
        if not email:
            return JsonResponse({"detail": "Email required"}, status=400)

        # Check across all orgs or infer from domain if needed
        exists = BreakGlassUser.objects.filter(email=email, is_active=True).exists()
        return JsonResponse({"is_break_glass": exists})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)