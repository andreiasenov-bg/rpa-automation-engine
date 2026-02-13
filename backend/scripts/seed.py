"""Database seed script — creates default org, admin user, roles, and permissions.

Run: python -m scripts.seed
"""

import asyncio
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def seed():
    """Seed the database with default data."""
    from db.database import init_db
    from db.database import AsyncSessionLocal
    from db.models.organization import Organization
    from db.models.user import User
    from db.models.role import Role
    from db.models.permission import Permission
    from core.security import hash_password
    from core.utils import generate_slug
    from sqlalchemy import select

    # Initialize DB tables
    await init_db()

    async with AsyncSessionLocal() as db:
        # 1. Create default organization
        result = await db.execute(
            select(Organization).where(Organization.slug == "default")
        )
        org = result.scalar_one_or_none()

        if not org:
            org = Organization(
                name="Default Organization",
                slug="default",
                subscription_plan="enterprise",
                is_active=True,
                settings={
                    "timezone": "Europe/Sofia",
                    "language": "bg",
                    "max_workflows": 100,
                    "max_agents": 10,
                    "max_executions_per_day": 1000,
                },
            )
            db.add(org)
            await db.flush()
            print(f"[seed] Created organization: {org.name} ({org.id})")
        else:
            print(f"[seed] Organization exists: {org.name}")

        # 2. Create default permissions
        permission_defs = [
            # Workflows
            ("workflows:read", "View workflows"),
            ("workflows:write", "Create and edit workflows"),
            ("workflows:delete", "Delete workflows"),
            ("workflows:execute", "Execute workflows"),
            ("workflows:publish", "Publish workflows"),
            # Executions
            ("executions:read", "View executions"),
            ("executions:cancel", "Cancel executions"),
            ("executions:retry", "Retry executions"),
            # Agents
            ("agents:read", "View agents"),
            ("agents:write", "Manage agents"),
            # Credentials
            ("credentials:read", "View credentials"),
            ("credentials:write", "Manage credentials"),
            # Triggers
            ("triggers:read", "View triggers"),
            ("triggers:write", "Manage triggers"),
            # Integrations
            ("integrations:read", "View integrations"),
            ("integrations:write", "Manage integrations"),
            # Users
            ("users:read", "View users"),
            ("users:write", "Manage users"),
            # Analytics
            ("analytics:read", "View analytics"),
            # Settings
            ("settings:read", "View settings"),
            ("settings:write", "Manage settings"),
            # AI
            ("ai:use", "Use AI features"),
            # Notifications
            ("notifications:read", "View notifications"),
            ("notifications:write", "Manage notifications"),
            # Audit
            ("audit:read", "View audit logs"),
        ]

        permissions = {}
        for code, description in permission_defs:
            result = await db.execute(
                select(Permission).where(Permission.code == code)
            )
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(
                    organization_id=org.id,
                    code=code,
                    description=description,
                )
                db.add(perm)
            permissions[code] = perm

        await db.flush()
        print(f"[seed] {len(permissions)} permissions ready")

        # 3. Create default roles
        role_defs = {
            "admin": {
                "name": "Administrator",
                "description": "Full access to all features",
                "permissions": list(permissions.keys()),
            },
            "developer": {
                "name": "Developer",
                "description": "Create and manage workflows and integrations",
                "permissions": [
                    "workflows:read", "workflows:write", "workflows:execute", "workflows:publish",
                    "executions:read", "executions:cancel", "executions:retry",
                    "agents:read", "credentials:read",
                    "triggers:read", "triggers:write",
                    "integrations:read", "integrations:write",
                    "analytics:read", "ai:use",
                    "notifications:read",
                ],
            },
            "operator": {
                "name": "Operator",
                "description": "Execute and monitor workflows",
                "permissions": [
                    "workflows:read", "workflows:execute",
                    "executions:read", "executions:cancel",
                    "agents:read",
                    "triggers:read",
                    "analytics:read",
                    "notifications:read",
                ],
            },
            "viewer": {
                "name": "Viewer",
                "description": "Read-only access",
                "permissions": [
                    "workflows:read", "executions:read",
                    "agents:read", "analytics:read",
                    "notifications:read",
                ],
            },
        }

        roles = {}
        for slug, role_def in role_defs.items():
            result = await db.execute(
                select(Role).where(Role.slug == slug, Role.organization_id == org.id)
            )
            role = result.scalar_one_or_none()
            if not role:
                role = Role(
                    organization_id=org.id,
                    name=role_def["name"],
                    slug=slug,
                    description=role_def["description"],
                )
                db.add(role)
                await db.flush()
                # Assign permissions
                for perm_code in role_def["permissions"]:
                    if perm_code in permissions:
                        role.permissions.append(permissions[perm_code])
            roles[slug] = role

        await db.flush()
        print(f"[seed] {len(roles)} roles ready")

        # 4. Create admin user
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@rpa-engine.local")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123!")

        result = await db.execute(
            select(User).where(User.email == admin_email)
        )
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                organization_id=org.id,
                email=admin_email,
                password_hash=hash_password(admin_password),
                first_name="Admin",
                last_name="User",
                is_active=True,
                is_superadmin=True,
            )
            db.add(admin_user)
            await db.flush()

            # Assign admin role
            if "admin" in roles:
                admin_user.roles.append(roles["admin"])

            print(f"[seed] Created admin user: {admin_email} (password: {admin_password})")
        else:
            print(f"[seed] Admin user exists: {admin_email}")

        await db.commit()
        print("[seed] Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
