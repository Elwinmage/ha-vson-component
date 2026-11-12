#!/usr/bin/env python3
"""Verify that every entity translation key exists in every locale.

Expected keys are discovered from the source, never hardcoded: any literal
``translation_key="..."`` (EntityDescription) or ``_attr_translation_key = "..."``
(entity class attribute) found in a platform module. The file name gives the
``entity`` section of the translation files.

The modules are parsed with ``ast`` because the pre-commit / CI environment has
no Home Assistant installed, so importing them is not an option.
"""

from __future__ import annotations

import ast
import json
import os
import sys

from colorama import Fore, Style

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_PATH = os.path.join(REPO_ROOT, "custom_components", "vson")
TRANSLATIONS_PATH = os.path.join(BASE_PATH, "translations")
STRINGS_FILE = os.path.join(BASE_PATH, "strings.json")

# Platform module -> `entity` section in the translation files.
PLATFORM_FILES = {
    "binary_sensor.py": "binary_sensor",
    "button.py": "button",
    "number.py": "number",
    "select.py": "select",
    "sensor.py": "sensor",
    "switch.py": "switch",
}


def _parse(path: str) -> ast.Module:
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def literal_translation_keys(path: str) -> set[str]:
    """Return every literal translation key declared in a module."""
    keys: set[str] = set()
    for node in ast.walk(_parse(path)):
        # translation_key="..." keyword argument
        if isinstance(node, ast.keyword) and node.arg == "translation_key":
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            ):
                keys.add(node.value.value)
        # _attr_translation_key = "..." assignment
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "_attr_translation_key"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    keys.add(node.value.value)
    return keys


def expected_keys() -> dict[str, set[str]]:
    """section -> set of translation keys expected in every locale."""
    expected: dict[str, set[str]] = {}
    for filename, section in PLATFORM_FILES.items():
        path = os.path.join(BASE_PATH, filename)
        if not os.path.exists(path):
            continue
        found = literal_translation_keys(path)
        if found:
            expected.setdefault(section, set()).update(found)
    return expected


def locale_keys(locale_file: str) -> dict[str, set[str]]:
    with open(locale_file, encoding="utf-8") as fh:
        data = json.load(fh)
    entity = data.get("entity", {})
    return {section: set(keys) for section, keys in entity.items()}


def main() -> int:
    expected = expected_keys()
    locale_files = [STRINGS_FILE]
    if os.path.isdir(TRANSLATIONS_PATH):
        locale_files += [
            os.path.join(TRANSLATIONS_PATH, f)
            for f in sorted(os.listdir(TRANSLATIONS_PATH))
            if f.endswith(".json")
        ]

    ok = True
    for locale_file in locale_files:
        present = locale_keys(locale_file)
        name = os.path.relpath(locale_file, REPO_ROOT)
        for section, keys in expected.items():
            missing = keys - present.get(section, set())
            if missing:
                ok = False
                for key in sorted(missing):
                    print(
                        f"{Fore.RED}MISSING{Style.RESET_ALL} {name}: "
                        f"entity.{section}.{key}"
                    )

    if ok:
        print(f"{Fore.GREEN}All entity translation keys are present.{Style.RESET_ALL}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
