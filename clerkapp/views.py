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
        org_id = getattr(request.user, "clerk_org_id", None)
        print("DEBUG: Listing SAML connections for org_id:", org_id)
        
        if not org_id:
            print("DEBUG: No org_id found in user")
            return JsonResponse({"error": "Organization ID not found"}, status=400)

        # Get all connections for the organization
        try:
            response = clerk_client.saml_connections.list()
            connections = response.data
            print("DEBUG: Total connections found:", len(connections))

            # Filter connections for the current organization
            org_connections = [
                conn for conn in connections 
                if getattr(conn, "organization_id", "") == org_id
            ]
            print("DEBUG: Connections for current org:", len(org_connections))

            base_url = "https://square-alpaca-17.clerk.accounts.dev"

            detailed = []
            for conn in org_connections:
                connection_id = getattr(conn, "id", "")
                print(f"DEBUG: Processing connection {connection_id}")

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
                    "active": getattr(conn, "active", False),
                    "organization_id": getattr(conn, "organization_id", ""),
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

            print("DEBUG: Returning detailed connections:", len(detailed))
            return JsonResponse({"connections": detailed}, content_type="application/json")

        except Exception as e:
            print(f"Error fetching connections: {str(e)}")
            return JsonResponse({"error": "Failed to fetch SAML connections"}, status=500)

    except Exception as e:
        print(f"Unexpected error in list_saml_connections: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)

import requests

@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
@csrf_exempt
def create_saml_connection(request):
    import requests
    import traceback
    import xml.etree.ElementTree as ET
    from clerk_backend_api.sdk import Clerk

    def parse_saml_metadata(metadata_url):
        try:
            response = requests.get(metadata_url)
            response.raise_for_status()
            xml_content = response.content

            root = ET.fromstring(xml_content)
            ns = {
                "md": "urn:oasis:names:tc:SAML:2.0:metadata",
                "ds": "http://www.w3.org/2000/09/xmldsig#"
            }

            entity_id = root.attrib.get("entityID")
            sso_url = root.find(".//md:IDPSSODescriptor/md:SingleSignOnService", ns).attrib.get("Location")
            cert_element = root.find(".//ds:X509Certificate", ns)
            cert = cert_element.text if cert_element is not None else None

            return {
                "entity_id": entity_id,
                "sso_url": sso_url,
                "certificate": cert
            }
        except Exception as e:
            return {"error": str(e)}

    def get_attribute_mapping(provider):
        if provider == "entra":
            return {
                "user_id": "http://schemas.microsoft.com/identity/claims/objectidentifier",
                "email_address": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
            }
        elif provider == "google":
            return {
                "user_id": "nameid",
                "email_address": "email",
                "first_name": "first_name",
                "last_name": "last_name"
            }
        elif provider == "okta":
            return {
                "user_id": "nameid",
                "email_address": "user.email",
                "first_name": "user.firstName",
                "last_name": "user.lastName"
            }
        return {
            "user_id": "nameid",
            "email_address": "mail",
            "first_name": "givenName",
            "last_name": "surname"
        }

    try:
        data = json.loads(request.body)
        name = data.get("name")
        domain = data.get("domain")
        metadata_url = data.get("metadata_url")
        provider_input = data.get("provider")  # entra / okta / google / custom
        org_id = getattr(request.user, "clerk_org_id", None)

        if not all([name, domain, metadata_url, provider_input, org_id]):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        if provider_input not in ["entra", "google", "okta", "custom"]:
            return JsonResponse({"error": "Invalid provider"}, status=400)

        metadata_info = parse_saml_metadata(metadata_url)
        if "error" in metadata_info:
            return JsonResponse({"error": f"Metadata parsing failed: {metadata_info['error']}"}, status=400)

        attribute_mapping = get_attribute_mapping(provider_input)

        clerk = Clerk(bearer_auth=settings.CLERK_API_SECRET_KEY)
        result = clerk.saml_connections.create(request={
            "name": name,
            "domain": domain,
            "provider": "saml_custom",  # Still required by Clerk
            "organization_id": org_id,
            "idp_entity_id": metadata_info["entity_id"],
            "idp_sso_url": metadata_info["sso_url"],
            "idp_certificate": metadata_info["certificate"],
            "attribute_mapping": attribute_mapping
        })

        return JsonResponse({
            "id": result.id,
            "name": result.name,
            "domain": result.domain,
            "organization_id": result.organization_id,
            "created_at": result.created_at
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
    
@csrf_exempt
@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def delete_saml_connection(request, conn_id):
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    
    try:
        org_id = getattr(request.user, "clerk_org_id", None)
        print(f"DEBUG: Attempting to delete connection {conn_id} for org {org_id}")
        
        if not org_id:
            print("DEBUG: No org_id found in user")
            return JsonResponse({"detail": "Organization ID not found"}, status=400)

        # Get all connections to find the specific one
        try:
            print(f"DEBUG: Fetching all connections")
            all_connections = clerk_client.saml_connections.list()
            connection = next(
                (conn for conn in all_connections.data if getattr(conn, "id", "") == conn_id),
                None
            )
            
            if not connection:
                print(f"DEBUG: Connection {conn_id} not found in available connections")
                return JsonResponse({"detail": "SAML connection not found"}, status=404)
                
            print(f"DEBUG: Found connection: {connection}")
            print(f"DEBUG: Connection org_id: {getattr(connection, 'organization_id', '')}")
            print(f"DEBUG: User org_id: {org_id}")

            # Verify the connection belongs to the organization
            if getattr(connection, "organization_id", "") != org_id:
                print(f"DEBUG: Organization mismatch. Connection org: {getattr(connection, 'organization_id', '')}, User org: {org_id}")
                return JsonResponse({"detail": "Unauthorized to delete this connection"}, status=403)

            # Delete the connection using the SDK's delete method
            print(f"DEBUG: Attempting to delete connection {conn_id}")
            try:
                # Create a new instance of the SDK with the connection ID
                delete_client = clerk_client.saml_connections
                delete_client.delete(conn_id)
                print(f"DEBUG: Successfully deleted connection {conn_id}")
                return JsonResponse({"status": "deleted"})
            except Exception as delete_error:
                print(f"DEBUG: Error during deletion: {str(delete_error)}")
                # Try alternative deletion method
                try:
                    headers = {
                        "Authorization": f"Bearer {settings.CLERK_API_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                    response = requests.delete(
                        f"https://api.clerk.com/v1/saml_connections/{conn_id}",
                        headers=headers
                    )
                    if response.ok:
                        print(f"DEBUG: Successfully deleted connection {conn_id} using API")
                        return JsonResponse({"status": "deleted"})
                    else:
                        print(f"DEBUG: API deletion failed: {response.text}")
                        return JsonResponse({"detail": "Failed to delete connection"}, status=500)
                except Exception as api_error:
                    print(f"DEBUG: API deletion error: {str(api_error)}")
                    return JsonResponse({"detail": "Failed to delete connection"}, status=500)

        except Exception as e:
            print(f"DEBUG: Error during connection operations: {str(e)}")
            return JsonResponse({"detail": "Failed to delete connection"}, status=500)

    except Exception as e:
        print(f"DEBUG: Unexpected error in delete_saml_connection: {str(e)}")
        return JsonResponse({"detail": "Internal server error"}, status=500)

@csrf_exempt
@jwt_required
@role_required(["super_admin"])
@require_permission("org:settings:sso")
def toggle_saml_connection(request, conn_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    
    try:
        org_id = getattr(request.user, "clerk_org_id", None)
        if not org_id:
            return JsonResponse({"detail": "Organization ID not found"}, status=400)

        try:
            body = json.loads(request.body)
            active = body.get("active", False)
            print(f"DEBUG: Toggling connection {conn_id} to active={active}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON in request body"}, status=400)

        # Verify the connection belongs to the organization
        try:
            response = clerk_client.saml_connections.list()
            connections = response.data
            connection = next(
                (conn for conn in connections if getattr(conn, "id", "") == conn_id and 
                 getattr(conn, "organization_id", "") == org_id),
                None
            )

            if not connection:
                return JsonResponse({"detail": "SAML connection not found or not authorized"}, status=404)

            # Update the connection status using the SDK
            try:
                print(f"DEBUG: Attempting to update connection {conn_id} status to {active}")
                update_client = clerk_client.saml_connections
                update_client.update(conn_id, active=active)
                print(f"DEBUG: Successfully updated connection {conn_id}")
                return JsonResponse({"status": "updated", "active": active})
            except Exception as sdk_error:
                print(f"DEBUG: SDK update failed: {str(sdk_error)}")
                # Try alternative update method using direct API call
                try:
                    headers = {
                        "Authorization": f"Bearer {settings.CLERK_API_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                    response = requests.patch(
                        f"https://api.clerk.com/v1/saml_connections/{conn_id}",
                        headers=headers,
                        json={"active": active}
                    )
                    if response.ok:
                        print(f"DEBUG: Successfully updated connection {conn_id} using API")
                        return JsonResponse({"status": "updated", "active": active})
                    else:
                        print(f"DEBUG: API update failed: {response.text}")
                        return JsonResponse({"detail": "Failed to update connection"}, status=500)
                except Exception as api_error:
                    print(f"DEBUG: API update error: {str(api_error)}")
                    return JsonResponse({"detail": "Failed to update connection"}, status=500)

        except Exception as e:
            print(f"DEBUG: Error during connection operations: {str(e)}")
            return JsonResponse({"detail": "Failed to update connection"}, status=500)

    except Exception as e:
        print(f"DEBUG: Unexpected error in toggle_saml_connection: {str(e)}")
        return JsonResponse({"detail": "Internal server error"}, status=500)

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