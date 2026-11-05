"""Read project metadata without importing source or executing package tools."""
import json
import re

MANIFESTS = {
    "requirements.txt": "Python", "pyproject.toml": "Python", "package.json": "JavaScript / TypeScript",
    "go.mod": "Go", "Cargo.toml": "Rust", "pom.xml": "Java", "build.gradle": "Java / Kotlin",
    "Gemfile": "Ruby", "composer.json": "PHP", "CMakeLists.txt": "C / C++",
}


def inspect_project(project):
    files = sorted(path for path in project.rglob("*") if path.is_file())
    manifests = []
    dependencies = []
    for path in files:
        if path.name not in MANIFESTS or path.stat().st_size > 65536:
            continue
        entry = {"path": path.relative_to(project).as_posix(), "ecosystem": MANIFESTS[path.name]}
        manifests.append(entry)
        text = path.read_text(errors="replace")
        if path.name == "requirements.txt":
            for line in text.splitlines():
                match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)(\[[A-Za-z0-9_,.-]+\])?\s*([<>=!~].{0,100})?\s*", line)
                if match:
                    dependencies.append({"name": match[1], "constraint": match[3] or "unspecified",
                                         "manifest": entry["path"]})
        elif path.name == "package.json":
            try:
                package = json.loads(text)
                for field in ("dependencies", "devDependencies"):
                    values = package.get(field, {})
                    if isinstance(values, dict):
                        dependencies.extend({"name": str(name)[:120], "constraint": str(version)[:120],
                                             "manifest": entry["path"]} for name, version in list(values.items())[:100])
            except (ValueError, AttributeError, RecursionError):
                entry["error"] = "Invalid package metadata"
    suffixes = {path.suffix for path in files}
    languages = [name for suffix, name in ((".py", "Python"), (".mjs", "JavaScript"), (".js", "JavaScript"),
                 (".ts", "TypeScript"), (".sql", "SQL"), (".go", "Go"), (".rs", "Rust"),
                 (".java", "Java"), (".cpp", "C++"), (".cs", "C#")) if suffix in suffixes]
    return {"file_count": len(files), "languages": sorted(set(languages)), "manifests": manifests[:40],
            "dependencies": dependencies[:200],
            "note": "Static inventory. Compatibility is established by the recorded execution tests."}
