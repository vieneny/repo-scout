"""Read-only, bounded project fingerprints without exporting local source text."""
from __future__ import annotations

import ast
import configparser
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
CREATIVE_TECHNOLOGIES = {
    "comfyui": "ComfyUI", "diffusers": "Diffusers", "torch": "PyTorch",
    "pytorch": "PyTorch", "transformers": "Transformers", "ffmpeg": "FFmpeg",
    "ffmpeg-python": "FFmpeg", "imageio-ffmpeg": "FFmpeg", "blender": "Blender",
    "bpy": "Blender",
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
    "graduation-project": ("graduation project", "graduation-project", "capstone", "final year project", "final-year project", "thesis project", "毕业设计", "毕设", "课程设计"),
    "image-generation": ("image generation", "image-generation", "text to image", "text-to-image", "txt2img", "文生图", "图像生成", "图片生成", "生成图片", "生成图像", "生图", "AI绘画", "AI 绘画"),
    "ai-creation": ("ai creation", "ai-creation", "aigc", "AI创作", "AI 创作", "AI生成内容", "AI 生成内容"),
    "video-generation": ("video generation", "video-generation", "text to video", "text-to-video", "txt2video", "txt2vid", "文生视频", "图生视频", "视频生成", "生成视频"),
    "video-editing": ("video editing", "video-editing", "video editor", "视频编辑", "视频剪辑", "剪辑"),
    "audio": ("audio", "speech", "text-to-speech", "text to speech", "tts", "music", "音频", "音乐", "语音", "配音"),
}
DOMAIN_CAPABILITIES = ("graduation-project", "video-generation", "video-editing", "image-generation", "ai-creation", "audio")


def _unique(values):
    output, seen = [], set()
    for value in values:
        text = str(value).strip()
        if text and text.casefold() not in seen:
            output.append(text)
            seen.add(text.casefold())
    return output


def _mentions(text, alias, *, package=False):
    # Unicode \w treats adjacent Chinese as part of the same word. Restrict
    # identifiers to ASCII so 学习Java的项目 matches, but JavaHelper does not.
    boundary = r"A-Za-z0-9_-" if package else r"A-Za-z0-9_"
    prefix = r"(?<![" + boundary + r"])" if re.match(r"[A-Za-z0-9_]", alias) else ""
    suffix = r"(?![" + boundary + r"])" if re.search(r"[A-Za-z0-9_]$", alias) else ""
    return re.search(prefix + re.escape(alias) + suffix, text, re.IGNORECASE) is not None


def _dependency_names(values):
    names = []
    for value in values:
        if isinstance(value, str):
            match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", value)
            if match:
                names.append(match.group(1).replace("_", "-"))
    return "\n".join(names)


def _creative_declarations(name, text):
    """Read dependency/tool fields, not descriptions, without executing code."""
    if name == "requirements.txt":
        return _dependency_names(line.split("#", 1)[0] for line in text.splitlines())
    if name == "pyproject.toml":
        values = []
        clean = re.sub(r"(?m)#.*$", "", text)
        sections = re.split(r"(?m)^\s*\[([^\]\r\n]+)\]\s*$", clean)
        # A bracket inside a quoted requirement (diffusers[torch]) does not
        # close its TOML dependency array.
        array_value = r"""\[((?:[^"']|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')*?)\]"""
        for index in range(1, len(sections), 2):
            section, body = sections[index].strip(), sections[index + 1]
            arrays = []
            if section == "project":
                arrays = re.findall(r"(?ms)^\s*dependencies\s*=\s*" + array_value, body)
            elif section in {"project.optional-dependencies", "dependency-groups", "tool.pdm.dev-dependencies"}:
                arrays = re.findall(r"(?ms)^\s*[^=\n]+\s*=\s*" + array_value, body)
            elif section.startswith("tool.poetry.") and section.endswith("dependencies"):
                values.extend(re.findall(r"(?m)^\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*=", body))
            for array in arrays:
                values.extend(re.findall(r"[\"']([^\"']+)[\"']", array))
        return _dependency_names(values)
    if name == "setup.cfg":
        config = configparser.ConfigParser(interpolation=None)
        try:
            config.read_string(text)
            values = config.get("options", "install_requires", fallback="").splitlines()
            if config.has_section("options.extras_require"):
                values.extend(line for _, value in config.items("options.extras_require") for line in value.splitlines())
            return _dependency_names(values)
        except configparser.Error:
            return ""
    if name == "setup.py":
        values = []
        try:
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.keyword) and node.arg in {"install_requires", "extras_require", "setup_requires"}:
                    try:
                        declared = ast.literal_eval(node.value)
                    except (ValueError, TypeError, SyntaxError):
                        continue
                    if isinstance(declared, dict):
                        values.extend(item for group in declared.values() if isinstance(group, (list, tuple)) for item in group)
                    elif isinstance(declared, (list, tuple)):
                        values.extend(declared)
        except SyntaxError:
            return ""
        return _dependency_names(values)
    if name == "Dockerfile":
        logical_lines = text.replace("\\\n", " ")
        declarations = re.findall(r"(?im)^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", logical_lines)
        for line in re.findall(r"(?im)^\s*RUN\s+(.+)$", logical_lines):
            for command in re.split(r"&&|;|\|\|", line):
                if re.match(r"\s*(?:(?:(?:python[0-9.]*\s+-m|uv)\s+)?pip[0-9.]*\s+install\b|(?:sudo\s+)?(?:apt(?:-get)?|conda|mamba)\s+install\b|apk\s+add\b|poetry\s+add\b)", command):
                    declarations.append(command)
                elif re.match(r"\s*(?:ffmpeg|blender)\b", command, re.IGNORECASE):
                    declarations.append(command.strip().split()[0])
        return "\n".join(declarations)
    if name.lower().startswith(("docker-compose", "compose.")):
        declarations = re.findall(r"(?im)^\s*image\s*:\s*(\S+)", text)
        declarations.extend(re.findall(r"(?im)^\s*(?:command|entrypoint)\s*:\s*[\"']?((?:ffmpeg|blender)\b)", text))
        return "\n".join(declarations)
    return ""


def _queries(stack, capabilities, anchors=()):
    # Keep combined platform labels intact. Punctuation in Java / JVM is a
    # display label, not three useful forge-search terms.
    labels = {"Java / JVM": "Java", "Gradle (Kotlin DSL)": "Gradle Kotlin"}
    technologies = _unique(labels.get(label, label) for label in [*anchors, *stack])
    capabilities = _unique(capabilities)
    domains = {value.casefold(): value for value in capabilities}
    domain = next((domains[value] for value in DOMAIN_CAPABILITIES if value in domains), capabilities[0] if capabilities else None)
    core = _unique(technologies[:1] + ([domain] if domain else []))
    combined = _unique(technologies[:2] + capabilities)
    queries = [" ".join(combined)] if combined else []
    if core and combined != core:
        queries.append(" ".join(core))
    for capability in capabilities:
        if capability != domain:
            queries.append(" ".join(_unique(core + [capability])))
    if domain and domain.casefold() == "graduation-project":
        queries.append(" ".join(_unique(technologies[:1] + ["毕业设计"])))
    return _unique(queries)


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
            if _mentions(search_text, needle, package=True):
                detected.append(label)
        creative_text = search_text if name == "package.json" else _creative_declarations(name, text)
        for needle, label in CREATIVE_TECHNOLOGIES.items():
            if _mentions(creative_text, needle, package=True):
                detected.append(label)
    return _unique(detected)


def build_profile(kind, value, stack=None, capabilities=None, audience="individual", constraints=None):
    if kind not in {"idea", "local"}:
        raise ValueError("build_profile accepts idea or local; repository input uses a provider")
    if audience not in {"individual", "team", "enterprise"}:
        raise ValueError("audience must be individual, team, or enterprise")
    if constraints is not None and (not isinstance(constraints, (list, tuple)) or not all(isinstance(item, str) for item in constraints)):
        raise ValueError("constraints must be a list of explicit strings")
    constraints = _unique(constraints or [])
    supplied_stack = _unique(stack or [])
    supplied_capabilities = _unique(capabilities or [])
    observations = []
    if kind == "idea":
        goal = str(value).strip()
        if not goal:
            raise ValueError("idea cannot be empty")
        title = goal[:90]
        words = goal.lower()
        inferred = [name for name, aliases in CAPABILITY_WORDS.items() if any(_mentions(words, alias) for alias in aliases)]
        capabilities = _unique(supplied_capabilities + inferred)
        anchors = [label for word, label in {**TECHNOLOGIES, **CREATIVE_TECHNOLOGIES}.items() if _mentions(words, word)]
        inferred_languages = []
        for word, label in {"python": "Python", "typescript": "TypeScript", "javascript": "JavaScript", "rust": "Rust", "java": "Java / JVM", "kotlin": "Kotlin", "swift": "Swift", "golang": "Go", "php": "PHP"}.items():
            if _mentions(words, word):
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
    queries = _queries(stack or [], capabilities or [], anchors if kind == "idea" else ())
    if not queries and kind == "idea":
        query_parts = re.findall(r"[A-Za-z][A-Za-z0-9-]+", goal)[:6]
        queries = [" ".join(query_parts)] if query_parts else [goal[:120]]
    return {
        "schema_version": 1, "kind": kind, "title": title, "goal": goal,
        "stack": _unique(stack or []), "capabilities": _unique(capabilities or []),
        "constraints": constraints,
        "queries": _unique(queries), "target_audience": audience, "observations": observations,
    }
