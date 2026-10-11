"""Snapshot installed runtime dependency versions, excluding dev-only dependencies."""
from importlib.metadata import distribution

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from app.config import ROOT


def main():
    pending = [Requirement(x) for x in distribution("zan-protect-bot").requires or []
               if not Requirement(x).marker or Requirement(x).marker.evaluate({"extra": ""})]
    seen = {}
    while pending:
        requirement = pending.pop()
        key = canonicalize_name(requirement.name)
        if key in seen:
            continue
        dist = distribution(requirement.name)
        seen[key] = f"{dist.metadata['Name']}=={dist.version}"
        for value in dist.requires or []:
            child = Requirement(value)
            if not child.marker or child.marker.evaluate({"extra": ""}):
                pending.append(child)
    (ROOT / "requirements-runtime.txt").write_text(
        "# Installed runtime version snapshot; regenerate after dependency upgrades.\n" +
        "\n".join(seen[key] for key in sorted(seen)) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
