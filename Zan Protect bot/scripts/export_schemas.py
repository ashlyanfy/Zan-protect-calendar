import json

from app.config import ROOT
from app.knowledge import LegalMaterial, SchemeMaterial


def main():
    folder = ROOT / "data" / "schemas"
    folder.mkdir(parents=True, exist_ok=True)
    for name, model in [("legal", LegalMaterial), ("scheme", SchemeMaterial)]:
        (folder / f"{name}.schema.json").write_text(json.dumps({
            "type": "array", "items": model.model_json_schema()}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
