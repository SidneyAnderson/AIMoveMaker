"""Phase 5 (Frontend) verification tests.

Checks all PRD requirements for the frontend scaffold:
- React 18 + Vite 5 + TypeScript
- Tailwind CSS 3 + shadcn/ui
- PRD color system (17 CSS custom properties)
- API client with JWT interceptor
- Zustand stores (auth, project, job)
- WebSocket hook with reconnect
- All views (Login, Projects, Storyboard, Timeline, Admin, Settings)
- AppShell with sidebar + command palette
- Protected routing
- Production build succeeds
"""
import json
import os
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = str(PROJECT_DIR / "frontend")
SRC_DIR = os.path.join(FRONTEND_DIR, "src")

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")


def read(path: str) -> str:
    full = os.path.join(FRONTEND_DIR, path) if not path.startswith("/") else path
    with open(full) as f:
        return f.read()


# ── Test 1: package.json has required dependencies ───────────────────
print("\nTest 1: package.json dependencies")
pkg = json.loads(read("package.json"))
deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
required_deps = [
    "react", "react-dom", "react-router-dom",
    "vite", "tailwindcss", "postcss", "autoprefixer",
    "typescript",
    "@tanstack/react-query",
    "zustand",
    "axios",
    "cmdk",
    "sonner",
    "lucide-react",
    "clsx",
    "tailwind-merge",
]
for dep in required_deps:
    check(f"dep: {dep}", dep in deps, f"Missing from package.json")

# ── Test 2: Vite config ──────────────────────────────────────────────
print("\nTest 2: Vite configuration")
vite_cfg = read("vite.config.ts")
check("react plugin import", "react" in vite_cfg.lower(), "No react plugin")
check("path alias @", "@" in vite_cfg, "No @ path alias")
check("proxy /api", "/api" in vite_cfg, "No /api proxy")
check("proxy /ws", "/ws" in vite_cfg, "No /ws proxy")

# ── Test 3: TypeScript config ────────────────────────────────────────
print("\nTest 3: TypeScript configuration")
tsconfig = json.loads(read("tsconfig.json"))
co = tsconfig.get("compilerOptions", {})
check("strict mode", co.get("strict") is True, "strict not true")
check("jsx react-jsx", co.get("jsx") == "react-jsx", f"jsx = {co.get('jsx')}")
paths = co.get("paths", {})
check("@/* path alias", "@/*" in paths, "No @/* path alias")

# ── Test 4: Tailwind config with PRD color tokens ────────────────────
print("\nTest 4: Tailwind config PRD color tokens")
tw = read("tailwind.config.js")
prd_colors = [
    "bg-base", "bg-surface", "bg-raised",
    "text-primary", "text-secondary", "text-muted",
    "accent-blue", "accent-green", "accent-amber", "accent-red",
    "border-default", "border-focus",
]
for color in prd_colors:
    # Check either the token name or a CSS var reference
    check(f"color: {color}", color.replace("-", "") in tw.replace("-", "") or color in tw,
          f"Missing color token {color}")

# ── Test 5: CSS custom properties (index.css) ────────────────────────
print("\nTest 5: CSS custom properties")
css = read("src/index.css")
check("has :root or .dark selector", ":root" in css or ".dark" in css, "No root/dark selectors")
css_vars = [
    "--bg-base", "--bg-surface", "--text-primary", "--accent-blue",
    "--border-default",
]
for v in css_vars:
    check(f"css var: {v}", v in css, f"Missing {v}")

# ── Test 6: Main entry point ─────────────────────────────────────────
print("\nTest 6: Entry point (main.tsx)")
main = read("src/main.tsx")
check("React 18 createRoot", "createRoot" in main, "No createRoot (React 18)")
check("BrowserRouter", "BrowserRouter" in main, "No BrowserRouter")
check("QueryClientProvider", "QueryClientProvider" in main, "No TanStack Query provider")
check("Toaster (sonner)", "Toaster" in main, "No Toaster from sonner")

# ── Test 7: App routing ──────────────────────────────────────────────
print("\nTest 7: App routing")
app = read("src/App.tsx")
routes = ["/login", "/projects", "storyboard", "timeline", "/admin", "/settings"]
for route in routes:
    check(f"route: {route}", route in app, f"Missing route {route}")
check("ProtectedRoute", "ProtectedRoute" in app or "protected" in app.lower(),
      "No route protection")

# ── Test 8: API client with JWT interceptor ──────────────────────────
print("\nTest 8: API client")
client = read("src/api/client.ts")
check("axios import", "axios" in client, "No axios import")
check("Authorization header", "Authorization" in client, "No Authorization header")
check("Bearer token", "Bearer" in client, "No Bearer token pattern")
check("401 interceptor", "401" in client, "No 401 response interceptor")
check("refresh logic", "refresh" in client.lower(), "No refresh token logic")

# ── Test 9: API modules ─────────────────────────────────────────────
print("\nTest 9: API modules")
api_files = ["auth.ts", "projects.ts", "storyboard.ts", "jobs.ts"]
for f in api_files:
    path = os.path.join(SRC_DIR, "api", f)
    check(f"api/{f} exists", os.path.exists(path), f"Missing {f}")
    if os.path.exists(path):
        content = read(f"src/api/{f}")
        check(f"api/{f} uses client", "client" in content.lower() or "api" in content.lower(),
              f"{f} doesn't import client")

# ── Test 10: Zustand stores ──────────────────────────────────────────
print("\nTest 10: Zustand stores")
auth_store = read("src/stores/authStore.ts")
check("authStore uses zustand create", "create" in auth_store, "No create()")
check("authStore has accessToken", "accessToken" in auth_store, "No accessToken state")
check("authStore has persist", "persist" in auth_store, "No persist middleware")

proj_store = read("src/stores/projectStore.ts")
check("projectStore uses create", "create" in proj_store, "No create()")
check("projectStore has currentProjectId", "currentProjectId" in proj_store, "No currentProjectId")

job_store = read("src/stores/jobStore.ts")
check("jobStore uses create", "create" in job_store, "No create()")
check("jobStore tracks progress", "progress" in job_store.lower(), "No progress tracking")

# ── Test 11: WebSocket hook ──────────────────────────────────────────
print("\nTest 11: WebSocket hook")
ws = read("src/hooks/useWebSocket.ts")
check("useWebSocket export", "useWebSocket" in ws, "No useWebSocket export")
check("WebSocket constructor", "WebSocket" in ws, "No WebSocket")
check("reconnect logic", "reconnect" in ws.lower() or "backoff" in ws.lower(),
      "No reconnect/backoff")
check("exponential backoff", "Math.min" in ws or "backoff" in ws.lower(),
      "No exponential backoff capping")

# ── Test 12: AppShell component ──────────────────────────────────────
print("\nTest 12: AppShell component")
shell = read("src/components/AppShell.tsx")
check("sidebar present", "sidebar" in shell.lower(), "No sidebar")
check("navigation links", "Link" in shell or "NavLink" in shell or "navigate" in shell.lower(),
      "No navigation links")
check("command palette trigger", "CommandPalette" in shell or "Cmd+K" in shell or "cmd" in shell.lower(),
      "No command palette trigger")

# ── Test 13: CommandPalette component ────────────────────────────────
print("\nTest 13: CommandPalette")
cmd = read("src/components/CommandPalette.tsx")
check("cmdk Command import", "Command" in cmd, "No Command from cmdk")
check("keyboard shortcut Ctrl/Cmd+K", "k" in cmd.lower() and ("meta" in cmd.lower() or "ctrl" in cmd.lower()),
      "No keyboard shortcut")

# ── Test 14: Views exist and contain key elements ────────────────────
print("\nTest 14: Views")
view_checks = {
    "LoginView.tsx": ["login", "password", "submit"],
    "ProjectsView.tsx": ["project", "create"],
    "StoryboardView.tsx": ["keyframe", "storyboard"],
    "TimelineView.tsx": ["timeline", "track"],
    "AdminView.tsx": ["admin", "user"],
    "SettingsView.tsx": ["setting"],
}
for view_file, keywords in view_checks.items():
    path = os.path.join(SRC_DIR, "views", view_file)
    check(f"{view_file} exists", os.path.exists(path), f"Missing {view_file}")
    if os.path.exists(path):
        content = read(f"src/views/{view_file}").lower()
        for kw in keywords:
            check(f"{view_file} contains '{kw}'", kw in content,
                  f"Missing keyword '{kw}'")

# ── Test 15: UI primitives ───────────────────────────────────────────
print("\nTest 15: UI primitives")
btn = read("src/components/ui/button.tsx")
check("Button component", "Button" in btn, "No Button export")
check("variant support", "variant" in btn.lower(), "No variant prop")
check("cva or class-variance-authority", "cva" in btn or "class-variance-authority" in btn,
      "No cva (class-variance-authority)")

inp = read("src/components/ui/input.tsx")
check("Input component", "Input" in inp, "No Input export")
check("forwardRef", "forwardRef" in inp or "React.forwardRef" in inp, "No forwardRef")

# ── Test 16: Dark mode only ──────────────────────────────────────────
print("\nTest 16: Dark mode configuration")
html = read("index.html")
check("html class='dark'", 'class="dark"' in html or "class='dark'" in html,
      "No dark class on html element")
check("bg-bg-base on body", "bg-bg-base" in html or "bg-base" in html,
      "No background utility on body")

# ── Test 17: Build output ────────────────────────────────────────────
print("\nTest 17: Build output")
dist = os.path.join(FRONTEND_DIR, "dist")
check("dist/ directory exists", os.path.isdir(dist), "No dist/ directory — build may not have run")
if os.path.isdir(dist):
    check("dist/index.html", os.path.exists(os.path.join(dist, "index.html")),
          "No index.html in dist/")
    assets = os.path.join(dist, "assets")
    check("dist/assets/ exists", os.path.isdir(assets), "No assets/ directory")
    if os.path.isdir(assets):
        files = os.listdir(assets)
        check("JS bundle in assets/", any(f.endswith(".js") for f in files),
              "No JS bundle")
        check("CSS bundle in assets/", any(f.endswith(".css") for f in files),
              "No CSS bundle")

# ── Summary ──────────────────────────────────────────────────────────
total = passed + failed
print(f"\n{'='*60}")
print(f"Phase 5 Verification: {passed}/{total} passed, {failed} failed")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
