import plistlib
import sys
from pathlib import Path


def find_forbidden(value, path="$"):
    findings = []

    if isinstance(value, dict):
        identifier = value.get("WFWorkflowActionIdentifier")
        if isinstance(identifier, str) and identifier.lower().endswith(".runworkflow"):
            findings.append(f"{path}.WFWorkflowActionIdentifier={identifier}")

        parameters = value.get("WFWorkflowActionParameters", {})
        if (
            isinstance(identifier, str)
            and identifier.lower().endswith(".setvariable")
            and isinstance(parameters, dict)
            and "WFInput" not in parameters
        ):
            findings.append(f"{path}: Set Variable is missing WFInput")

        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() == "cherri_functions":
                findings.append(child_path)
            findings.extend(find_forbidden(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_forbidden(child, f"{path}[{index}]"))
    elif isinstance(value, str) and "cherri_functions" in value.lower():
        findings.append(path)

    return findings


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_shortcut.py SHORTCUT_FILE")

    shortcut_path = Path(sys.argv[1])
    with shortcut_path.open("rb") as shortcut_file:
        shortcut = plistlib.load(shortcut_file)

    findings = find_forbidden(shortcut)
    if findings:
        details = "\n".join(f"- {finding}" for finding in findings)
        raise SystemExit(f"invalid Shortcut structure found:\n{details}")

    actions = shortcut.get("WFWorkflowActions", [])
    print(
        f"Verified {shortcut_path}: {len(actions)} actions, "
        "no Run Shortcut/function dispatcher or incomplete Set Variable"
    )


if __name__ == "__main__":
    main()
