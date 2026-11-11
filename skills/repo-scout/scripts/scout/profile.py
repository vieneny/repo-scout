"""Read-only, bounded project fingerprints without exporting local source text."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

MANIFESTS = {
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts",
    "composer.json", "Gemfile", "pubspec.yaml", "tsconfig.json", "deno.json",
    "Package.swift", "Podfile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml",
}
IGNORED = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "vendor",
    "dist", "build", "target", "__pycache__", ".next", ".cache", "coverage",
    "private", "secrets", "credentials", ".idea", ".vscode",
}
TECHNOLOGIES = {
    "langchain": "LangChain", "langgraph": "LangGraph", "llama-index": "LlamaIndex",
    "llama_index": "LlamaIndex", "fastapi": "FastAPI", "django": "Django",
    "flask": "Flask", "pydantic": "Pydantic", "sqlalchemy": "SQLAlchemy",
    "streamlit": "Streamlit", "gradio": "Gradio", "pytest": "pytest",
    "next": "Next.js", "nuxt": "Nuxt", "react": "React", "react-native": "React Native",
    "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular", "vite": "Vite",
    "typescript": "TypeScript", "express": "Express", "@nestjs/core": "NestJS",
    "electron": "Electron", "@tauri-apps/api": "Tauri", "vitest": "Vitest",
    "playwright": "Playwright", "prisma": "Prisma", "drizzle-orm": "Drizzle",
    "redis": "Redis", "pymongo": "MongoDB", "mongodb": "MongoDB",
    "psycopg": "PostgreSQL", "pg": "PostgreSQL", "psycopg2": "PostgreSQL",
    "mysql": "MySQL", "pymysql": "MySQL", "mysql2": "MySQL",
    "sqlite": "SQLite", "sqlite3": "SQLite", "better-sqlite3": "SQLite",
    "chromadb": "Chroma", "qdrant-client": "Qdrant", "faiss-cpu": "FAISS",
    "weaviate-client": "Weaviate", "flutter": "Flutter", "spring-boot": "Spring Boot",
    "gin-gonic/gin": "Gin", "labstack/echo": "Echo", "actix-web": "Actix Web",
    "axum": "Axum", "tokio": "Tokio", "rails": "Rails", "laravel": "Laravel",
    "org.jetbrains.kotlin": "Kotlin", "kotlin-android": "Kotlin", "swiftui": "SwiftUI",
    "uikit": "UIKit", "jetpack": "Jetpack", "androidx.compose": "Jetpack Compose",
}
CAPABILITY_WORDS = {
    "rag": ("rag", "retrieval augmented", "retrieval-augmented"),
    "agent": ("agent", "agents", "智能体"),
    "chat": ("chat", "chatbot", "聊天", "对话"),
    "search": ("search", "搜索", "检索"),
    "workflow": ("workflow", "工作流"),
    "authentication": ("authentication", "登录", "auth"),
    "database": ("database", "数据库", "sql"),
    "knowledge-base": ("knowledge base", "knowledge-base", "知识库"),
    "dashboard": ("dashboard", "仪表盘"),
    "automation": ("automation", "自动化"),
    "testing": ("testing", "测试"),
}


def _unique(values):
    output, seen = [], set()
    for value in values:
        text = str(value).strip()
        if text and text.casefold() not in seen:
            output.append(text)
            seen.add(text.casefold())
    return output


def detect_stack(contents: dict[str, str]) -> list[str]:
    """Return only allowlisted technology names, never arbitrary dependency values."""
    detected = []
    for filename, text in contents.items():
        name = Path(filename).name
        if name in {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"}:
            detected.append("Python")
        if name in {"package.json", "deno.json"}:
            detected.append("JavaScript")
        if name == "tsconfig.json":
            detected.append("TypeScript")
        if name == "go.mod":
            detected.append("Go")
        if name == "Cargo.toml":
            detected.append("Rust")
        if name == "pom.xml":
            detected.append("Java / JVM")
        if name in {"build.gradle", "build.gradle.kts"}:
            detected.append("Gradle" if name == "build.gradle" else "Gradle (Kotlin DSL)")
        if name == "Package.swift":
            detected.append("Swift")
        if name == "Podfile":
            detected.append("CocoaPods")
        if name == "composer.json":
            detected.append("PHP")
        if name == "Gemfile":
            detected.append("Ruby")
        if name == "pubspec.yaml":
            detected.append("Dart")
        if name == "Dockerfile" or name.lower().startswith(("docker-compose", "compose.")):
            detected.append("Docker")
        search_text = text.lower()
        if name == "package.json":
            try:
                package = json.loads(text)
                dependencies = {}
                for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    if isinstance(package.get(key), dict):
                        dependencies.update(package[key])
                search_text = "\n".join(dependencies).lower()
            except (ValueError, TypeError, AttributeError):
                # Malformed manifests do not become an arbitrary text-export route.
                continue
        for needle, label in TECHNOLOGIES.items():
            if re.search(r"(?<![\w-])" + re.escape(needle) + r"(?![\w-])", search_text):
                detected.append(label)
    return _unique(detected)


def build_profile(kind, value, stack=None, capabilities=None, audience="individual"):
    if kind not in {"idea", "local"}:
        raise ValueError("build_profile accepts idea or local; repository input uses a provider")
    if audience not in {"individual", "team", "enterprise"}:
        raise ValueError("audience must be individual, team, or enterprise")
    supplied_stack = _unique(stack or [])
    supplied_capabilities = _unique(capabilities or [])
    observations = []
    if kind == "idea":
        goal = str(value).strip()
        if not goal:
            raise ValueError("idea cannot be empty")
        title = goal[:90]
        words = goal.lower()
        inferred = [name for name, aliases in CAPABILITY_WORDS.items() if any(alias in words for alias in aliases)]
        capabilities = _unique(supplied_capabilities + inferred)
        anchors = [label for word, label in TECHNOLOGIES.items() if re.search(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", words)]
        inferred_languages = []
        for word, label in {"python": "Python", "typescript": "TypeScript", "javascript": "JavaScript", "rust": "Rust", "java": "Java / JVM", "kotlin": "Kotlin", "swift": "Swift", "golang": "Go", "php": "PHP"}.items():
            if re.search(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", words):
                inferred_languages.append(label)
        stack = _unique(supplied_stack + anchors + inferred_languages)
    else:
        root = Path(value).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("local input must be an existing directory")
        contents = {}
        scanned = 0
        capped = False
        for current, dirs, filenames in os.walk(root, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.relative_to(root).parts)
            dirs[:] = sorted(d for d in dirs if d not in IGNORED and not d.startswith(".") and not (current_path / d).is_symlink()) if depth < 4 else []
            for filename in sorted(filenames):
                scanned += 1
                if scanned > 2000:
                    capped = True
                    break
                file = current_path / filename
                if filename not in MANIFESTS or file.is_symlink():
                    continue
                try:
                    if file.stat().st_size <= 65536:
                        contents[file.relative_to(root).as_posix()] = file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
            if capped:
                break
        stack = _unique(supplied_stack + detect_stack(contents))
        capabilities = supplied_capabilities
        title = root.name
        goal = "Find learning references and reusable projects for this local technology profile."
        observations = [{"kind": "manifest", "path": filename} for filename in sorted(contents)]
        observations.append({"kind": "scan", "note": "Only allowlisted manifests and technology labels were retained; source text and absolute paths were omitted.", "bounded": capped})
        if not capabilities:
            observations.append({"kind": "needs-context", "note": "Add the project's business goal and capabilities before treating search results as semantically similar."})
    # Use abstractions rather than the private local directory name in outbound queries.
    query_parts = _unique((anchors[:2] if kind == "idea" else []) + list(capabilities or [])[:3] + list(stack or [])[:3])
    if not query_parts and kind == "idea":
        query_parts = re.findall(r"[A-Za-z][A-Za-z0-9-]+", goal)[:6]
        if not query_parts:
            query_parts = [goal[:120]]
    queries = [" ".join(query_parts[:4])] if query_parts else []
    if len(query_parts) > 2:
        queries.append(" ".join(query_parts[:2]))
    return {
        "schema_version": 1, "kind": kind, "title": title, "goal": goal,
        "stack": _unique(stack or []), "capabilities": _unique(capabilities or []),
        "queries": _unique(queries), "target_audience": audience, "observations": observations,
    }
