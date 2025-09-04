# transform-myd
**Doel:** EXTRACT-bestanden omzetten naar SAP *Migrate Your Data* CSV met YAML-configs.

![CI](https://github.com/viggomeesters/transform-myd/actions/workflows/ci.yml/badge.svg)

## Snelstart (Windows/PowerShell)
1) Python 3.13 hebben.
2) In de projectmap (de map waar `pyproject.toml` staat):
   ```powershell
   py -3.13 -m pip install -e . --no-build-isolation
   ```
3) Een run doen:
   ```powershell
   myd-transform -o M140 -v BNKA --report --reports raw,post,validation --no-txt-log
   # of met een specifiek bronbestand:
   myd-transform -o M140 -v BNKA -i .\data\raw\bank_raw.xlsx --report --reports raw,post,validation
   ```

## Mappenstructuur (advies)
```
.
├─ src/transform_myd/           # Python package (code)
├─ config/                      # YAML-configs per object/variant
│  ├─ _shared/                  # gedeelde defaults (meta.yaml)
│  └─ M140/BNKA/                # specifieke variant
│     ├─ column_map.yaml
│     ├─ value_map.yaml
│     ├─ value_rules.yaml
│     └─ meta.yaml
├─ data/
│  ├─ raw/                      # bronbestanden (niet committen)
│  ├─ out/                      # export CSV (niet committen)
│  └─ rejects/                  # rejects CSV (niet committen)
├─ logs/                        # reports / reasons / txt logs (niet committen)
├─ pyproject.toml
├─ README.md
├─ .gitignore
└─ .gitattributes
```

## Belangrijkste opties
- `--object/-o`, `--variant/-v` – kies object/variant (bv. `M140` + `BNKA`)
- `--input/-i` – bronbestand forceren
- `--report` + `--reports raw,post,validation` – maak rapporten
- `--sample N` – alleen eerste N rijen
- `--keep-lineage` – lineage-kolommen mee-exporteren
- `--trace-config` – toon welke YAML-lagen meedoen
- `--lint`, `--lint-all`, `--strict` – check je config
- `--ci` – preset voor pipelines (quiet, html reports, strict, fail-on-*)

## Reports (stages)
- **raw**: direct na load (na optionele text hygiene + lineage) → zicht op broninhoud.
- **post**: ná maps/transforms, met **Delta** t.o.v. RAW per kolom.
- **validation**: ná rules; alleen geldige records (aparte reject reasons CSV).

Alle CSV/TXT/MD/HTML worden geschreven met **UTF-8 (BOM)**; HTML bevat `<meta charset="utf-8">`.

## Lineage
`config/_shared/meta.yaml` (voorbeeld):
```yaml
lineage:
  enabled: true
  keep_in_export: false
  tz: "Europe/Amsterdam"
  uid:
    enabled: false
    keys: []       # bv. ["BANKS","BANKL"]
    length: 16
```

## Runlist (batch)
`config/runlist_ci.yaml` voorbeeld (zie bestand in deze download):
```powershell
myd-transform --runlist config/runlist_ci.yaml
# Lint in plaats van uitvoeren:
myd-transform --runlist config/runlist_ci.yaml --lint --strict
```

## Git & GitHub (simpel)
- **.gitignore** → gewoon tekstbestand met paden die Git moet negeren (outputs, logs, venv).
- **.gitattributes** → regels voor line-endings: code/config LF, Windows-scripts CRLF, Excel-binaries nooit aanpassen.

### Nieuwe repo maken (met GitHub Desktop – makkelijkste manier)
1. Open **GitHub Desktop** → **File > New repository…**
2. **Name**: `transform-myd`  
   **Local path**: kies jouw map (bijv. `C:\Dev\transform-myd`)  
   Klik **Create repository**.
3. Voeg (indien nog niet aanwezig) dit **README.md**, **.gitignore**, **.gitattributes** toe aan die map.
4. Terug in GitHub Desktop: je ziet de wijzigingen → **Commit to main**.
5. Klik **Publish repository** (kies **Private** als je wil). Klaar.

### Bestaande map koppelen (als je al in die map werkt)
1. GitHub Desktop → **File > Add local repository…** → kies jouw map `C:\Dev\transform-myd` → **Add**.
2. **Publish repository** om naar GitHub te zetten. Klaar.

### Command line (alternatief)
```powershell
# initialiseer repo
git init
git add .
git commit -m "chore: initial import"

# maak op github.com een lege repo (zonder README), b.v. https://github.com/<USER>/transform-myd

git branch -M main
git remote add origin https://github.com/<USER>/transform-myd.git
git push -u origin main
```

### Wijzigingen doorvoeren (commit & push)
```powershell
git add -A
git commit -m "feat: nieuwe README + runlist"
git push
```

## Troubleshooting
- **CRLF/LF warnings** → voeg `.gitattributes` toe (zie dit pakket) en doe 1x:
  ```powershell
  git add .gitattributes
  git add --renormalize .
  git commit -m "chore: normalize line endings"
  ```
- **Meerdere `myd-transform.exe` in PATH** → check met `where myd-transform` of roep zo aan:
  ```powershell
  py -3.13 -m transform_myd.cli ...
  ```
