from django.urls import path
from clerkapp.views import (
    root_router,
    settings_view,
    list_org_members,
    configure_sso,
    clerk_jwt,
    list_saml_connections,
    create_saml_connection,
    delete_saml_connection,
    toggle_saml_connection,
    list_break_glass_users,
    create_break_glass_user,
    is_break_glass_user,
)

urlpatterns = [
    path('', root_router, name='root_router'),
    path('settings/', settings_view, name='settings_view'),
    path('settings/org-members/', list_org_members, name='list_org_members'),
    path('settings/configure-sso/', configure_sso, name='configure_sso'),
    path('clerk_jwt/', clerk_jwt, name='clerk_jwt'),
    path('settings/sso/', list_saml_connections, name='list_saml_connections'),
    path('settings/sso/create/', create_saml_connection, name='create_saml_connection'),
    path('settings/sso/delete/<str:conn_id>/', delete_saml_connection, name='delete_saml_connection'),
    path('settings/sso/<str:conn_id>/toggle/', toggle_saml_connection, name='toggle_saml_connection'),
    path("settings/break-glass/", list_break_glass_users, name="list_break_glass_users"),
    path("settings/break-glass/create/", create_break_glass_user, name="create_break_glass_user"),
    path("is-break-glass/", is_break_glass_user, name="is_break_glass_user"),
]