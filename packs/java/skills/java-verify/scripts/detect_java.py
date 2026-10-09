#!/usr/bin/env python3
"""Detect Java build conventions using only the Python standard library."""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

STATIC_REVIEW = Path(__file__).resolve().with_name("static_review.py")


def static_command() -> str:
    if sys.platform == "win32":
        return f'"{Path(sys.executable).resolve()}" "{STATIC_REVIEW}" <paths>'
    return f"python3 {shlex.quote(str(STATIC_REVIEW))} <paths>"


def text_value(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def xml_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xml_children(parent, name: str):
    return [child for child in list(parent) if xml_local(child.tag) == name]


def first_child(parent, name: str):
    return next(iter(xml_children(parent, name)), None)


def maven_info(root: Path, wrapper: bool):
    result = {"java_version": None, "spring_boot_version": None, "modules": [], "namespace": "unknown", "persistence": []}
    pom = root / "pom.xml"
    try:
        tree = ET.parse(pom)
        project = tree.getroot()
    except (OSError, ET.ParseError):
        return result
    props = first_child(project, "properties")
    properties = {}
    if props is not None:
        for child in list(props):
            properties[xml_local(child.tag)] = text_value(child.text)
    for key in ("java.version", "maven.compiler.release", "maven.compiler.source", "maven.compiler.target", "release"):
        if properties.get(key):
            result["java_version"] = properties[key]
            break
    parent = first_child(project, "parent")
    if parent is not None:
        artifact = text_value(first_child(parent, "artifactId").text if first_child(parent, "artifactId") is not None else None)
        version = text_value(first_child(parent, "version").text if first_child(parent, "version") is not None else None)
        if artifact == "spring-boot-starter-parent":
            result["spring_boot_version"] = version
    modules = first_child(project, "modules")
    if modules is not None:
        result["modules"] = [text_value(child.text) for child in xml_children(modules, "module") if text_value(child.text)]
    deps = first_child(project, "dependencies")
    artifacts = set()
    if deps is not None:
        for dep in xml_children(deps, "dependency"):
            aid = first_child(dep, "artifactId")
            group = first_child(dep, "groupId")
            aid_text = text_value(aid.text if aid is not None else None)
            group_text = text_value(group.text if group is not None else None)
            if aid_text:
                artifacts.add(aid_text)
            if aid_text in {"mybatis-spring-boot-starter", "mybatis"}:
                if "mybatis" not in result["persistence"]:
                    result["persistence"].append("mybatis")
            if aid_text and "mybatis-plus" in aid_text and "mybatis-plus" not in result["persistence"]:
                result["persistence"].append("mybatis-plus")
            if aid_text and (aid_text.startswith("spring-data-jpa") or aid_text == "hibernate-core") and "jpa" not in result["persistence"]:
                result["persistence"].append("jpa")
            if group_text == "org.mybatis" and "mybatis" not in result["persistence"]:
                result["persistence"].append("mybatis")
    if result["spring_boot_version"] is None:
        for child in list(project):
            if xml_local(child.tag) == "dependencyManagement":
                raw = ET.tostring(child, encoding="unicode")
                match = re.search(r"spring-boot-dependencies.*?<version>([^<]+)</version>", raw, re.S)
                if match:
                    result["spring_boot_version"] = match.group(1).strip()
                    break
    source = "\n".join(read_text(p) for p in root.rglob("*.java"))
    if re.search(r"\bjakarta\.(?:persistence|validation|servlet)\b", source):
        result["namespace"] = "jakarta"
    elif re.search(r"\bjavax\.(?:persistence|validation|servlet)\b", source):
        result["namespace"] = "javax"
    return result


def gradle_info(root: Path, wrapper: bool):
    result = {"java_version": None, "spring_boot_version": None, "modules": [], "namespace": "unknown", "persistence": []}
    scripts = [p for p in (root / "build.gradle", root / "build.gradle.kts") if p.is_file()]
    text = "\n".join(read_text(p) for p in scripts)
    match = re.search(r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)|JavaVersion\.VERSION_(\d+)|sourceCompatibility\s*=\s*[\"']?([0-9]+)", text)
    if match:
        result["java_version"] = next(group for group in match.groups() if group)
    match = re.search(r"org\.springframework\.boot[^\n]*version\s*[= ]\s*[\"']([^\"']+)", text)
    if match:
        result["spring_boot_version"] = match.group(1)
    for settings in (root / "settings.gradle", root / "settings.gradle.kts"):
        if settings.is_file():
            settings_text = read_text(settings)
            for block in re.findall(r"include\s*\((.*?)\)|include\s+(.+)", settings_text, re.S):
                fragment = " ".join(x for x in block if x)
                result["modules"].extend(re.findall(r"[\"'](:[^\"']+)[\"']", fragment))
            break
    if re.search(r"mybatis-plus", text, re.I):
        result["persistence"].append("mybatis-plus")
    elif re.search(r"mybatis", text, re.I):
        result["persistence"].append("mybatis")
    if re.search(r"spring-boot-starter-data-jpa|hibernate", text, re.I):
        result["persistence"].append("jpa")
    source = "\n".join(read_text(p) for p in root.rglob("*.java"))
    if re.search(r"\bjakarta\.(?:persistence|validation|servlet)\b", source):
        result["namespace"] = "jakarta"
    elif re.search(r"\bjavax\.(?:persistence|validation|servlet)\b", source):
        result["namespace"] = "javax"
    return result


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def main(argv=None) -> int:
    project = Path((argv or sys.argv[1:] or ["."])[0]).expanduser().resolve()
    has_maven = (project / "pom.xml").is_file()
    gradle_files = [p for p in (project / "build.gradle", project / "build.gradle.kts") if p.is_file()]
    wrapper = any((project / name).is_file() for name in ("mvnw", "gradlew"))
    if has_maven:
        info = maven_info(project, wrapper)
        tool = "maven"
        executable = "./mvnw" if (project / "mvnw").is_file() else "mvn"
    elif gradle_files:
        info = gradle_info(project, wrapper)
        tool = "gradle"
        executable = "./gradlew" if (project / "gradlew").is_file() else "gradle"
    else:
        info = {"java_version": None, "spring_boot_version": None, "modules": [], "namespace": "unknown", "persistence": []}
        tool = "unknown"
        executable = None
    module_arg = " -pl <module> -am" if tool == "maven" and info["modules"] else ""
    if tool == "gradle":
        # `build` also runs tests; `classes` is the compile-only lifecycle task
        task = ":<module>:" if info["modules"] else ""
        compile_cmd, test_cmd, start_cmd = f"{executable} {task}classes", f"{executable} {task}test", f"{executable} {task}bootRun"
    elif tool == "maven":
        # -am on spring-boot:run would run the plugin in upstream modules that do not declare it
        start_arg = " -pl <module>" if info["modules"] else ""
        compile_cmd, test_cmd, start_cmd = f"{executable}{module_arg} compile", f"{executable}{module_arg} test", f"{executable}{start_arg} spring-boot:run"
    else:
        compile_cmd = test_cmd = start_cmd = None
    output = {
        "build_tool": tool,
        "wrapper": wrapper,
        "modules": info["modules"],
        "java_version": info["java_version"],
        "spring_boot_version": info["spring_boot_version"],
        "namespace": info["namespace"],
        "persistence": info["persistence"],
        "commands": {"compile": compile_cmd, "test": test_cmd, "start": start_cmd, "static": static_command()},
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
