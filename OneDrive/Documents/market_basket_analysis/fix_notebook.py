import json
from pathlib import Path


def _ensure_dict(node, key: str):
    if key not in node or node[key] is None:
        node[key] = {}
    elif not isinstance(node[key], dict):
        node[key] = {}


def clean_notebook(in_path: Path, out_path: Path) -> None:
    nb = json.loads(in_path.read_text(encoding="utf-8"))

    # Notebook-level metadata must exist
    _ensure_dict(nb, "metadata")

    for cell in nb.get("cells", []):
        _ensure_dict(cell, "metadata")
        outputs = cell.get("outputs")
        if not isinstance(outputs, list):
            continue
        for out in outputs:
            if not isinstance(out, dict):
                continue
            # nbformat expects outputs to have a metadata field for execute_result/display_data
            if out.get("output_type") in {"execute_result", "display_data"}:
                _ensure_dict(out, "metadata")
            if out.get("output_type") == "execute_result":
                # Required by the schema; nbconvert validates even for pre-existing outputs
                out.setdefault("execution_count", None)
            # For stream/error outputs, avoid adding unexpected fields.
            if out.get("output_type") == "stream":
                out.pop("metadata", None)
                out.setdefault("name", "stdout")
            if out.get("output_type") == "error":
                out.pop("metadata", None)

    out_path.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    in_nb = Path("market-basket-analysis project  (1).ipynb")
    out_nb = Path("market-basket-analysis project  (1)_clean.ipynb")
    clean_notebook(in_nb, out_nb)
    print(f"Wrote cleaned notebook: {out_nb}")

