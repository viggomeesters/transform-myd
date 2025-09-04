# apply_split_patch.py
# Past een custom patch toe met blokken als:
# *** Add File: path
#   + <inhoud>
# *** End Patch

import sys
from pathlib import Path

def apply_custom_patch(patch_path: Path, root: Path):
    current_file = None
    content_lines = []
    inside_block = False

    for raw in patch_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")

        # negeer code fences en begin-markers
        if line.strip().startswith("```") or line.startswith("*** Begin Patch"):
            continue

        if line.startswith("*** Add File:"):
            # nieuw bestand starten
            current_file = line.split(":", 1)[1].strip()
            content_lines = []
            inside_block = True
            continue

        if line.startswith("*** End Patch"):
            if current_file:
                out_path = (root / current_file)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                text = "\n".join(content_lines) + "\n"
                out_path.write_text(text, encoding="utf-8")
                print(f"[write] {out_path}")
            current_file = None
            content_lines = []
            inside_block = False
            continue

        if inside_block:
            # strip één leidend '+' (en spatie) uit diff
            if line.startswith("+ "):
                content_lines.append(line[2:])
            elif line.startswith("+"):
                content_lines.append(line[1:])
            else:
                content_lines.append(line)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gebruik: python apply_split_patch.py split.patch")
        sys.exit(1)
    patch = Path(sys.argv[1]).resolve()
    apply_custom_patch(patch, Path(".").resolve())
    print("Gereed.")
