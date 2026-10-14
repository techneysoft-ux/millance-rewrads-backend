"""
Test if the franchise endpoints exist
Run on VPS: python test_endpoints.py
"""
from main import app

print("=" * 60)
print("TESTING FRANCHISE ENDPOINTS")
print("=" * 60)

# Get all routes
routes = []
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        for method in route.methods:
            routes.append(f"{method} {route.path}")

# Filter franchise routes
franchise_routes = [r for r in routes if '/franchise' in r]

print(f"\n📋 Found {len(franchise_routes)} franchise routes:")
for route in sorted(franchise_routes):
    print(f"  {route}")

# Check specific endpoints
print(f"\n🔍 Checking specific endpoints:")
endpoints_to_check = [
    ("GET", "/api/franchise/stats"),
    ("GET", "/api/franchise/plans"),
    ("POST", "/api/franchise/plans"),
    ("GET", "/api/franchise/prize-pools"),
    ("POST", "/api/franchise/prize-pools"),
    ("GET", "/api/franchise/groups"),
    ("POST", "/api/franchise/groups"),
    ("GET", "/api/franchise/enrollments"),
]

for method, path in endpoints_to_check:
    found = f"{method} {path}" in routes
    status = "✅" if found else "❌"
    print(f"  {status} {method:6} {path}")

print("\n" + "=" * 60)
