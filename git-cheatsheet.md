# Git Workflow Cheatsheet (NL)

Hieronder vind je de standaard workflow voor aanpassingen, committen en pushen in Git.

---

## 1. Repository clonen
```powershell
git clone <url-naar-repo>
```
- Bijvoorbeeld:
  ```powershell
git clone https://github.com/viggomeesters/transform-myd.git
```
- Hiermee maak je een kopie van de repo op jouw computer.

---

## 2. Branches gebruiken
```powershell
git branch                # toont lokale branches
git branch -r             # toont remote branches
git checkout <naam>       # wissel van branch of maak nieuwe branch aan
```
- Nieuwe branch maken en direct wisselen:
  ```powershell
git checkout -b nieuwe-feature
```
- Remote branch ophalen:
  ```powershell
git fetch
git checkout -b nieuwe-feature origin/nieuwe-feature
```

---

## 3. Bestanden/Mappen aanpassen
- Voeg toe, verwijder, hernoem of bewerk bestanden/mappen in je projectfolder.
- Dit kan via Verkenner, VSCode, of de command line.

---

## 4. Status bekijken
```powershell
git status
```
*Toont welke bestanden zijn veranderd, toegevoegd of verwijderd sinds de laatste commit.*

---

## 5. Wijzigingen toevoegen aan "staging"
```powershell
git add .
```
*Voegt alle wijzigingen (nieuw, veranderd, verwijderd) toe aan de staging area.*

- Wil je slechts één bestand toevoegen?
  ```powershell
git add pad/naar/bestand.py
```

---

## 6. Commit maken
```powershell
git commit -m "Korte, duidelijke omschrijving van je wijziging"
```
*Bijvoorbeeld:*
```powershell
git commit -m "Datafolder hernoemd naar dataset en script aangepast"
```

---

## 7. Pushen naar GitHub
```powershell
git push
```
*Zet je commits online in de actieve branch.*

---

## 8. (Optioneel) Eerst ophalen, bij samenwerken
```powershell
git pull
```
*Haalt nieuwe wijzigingen van GitHub op vóór je gaat pushen (handig bij teamwork).* 

---

## 9. Controleer je commitgeschiedenis
```powershell
git log --oneline
```
*Geeft een korte lijst van je recente commits.*

---

## Snelle Samenvatting

1. **Clonen:**  `git clone <url>`
2. **Branch kiezen/maken:**  `git branch`, `git checkout -b <branchnaam>`
3. **Aanpassen:**  Werk in je projectmap (bestanden/mappen).
4. **Status checken:**  `git status`
5. **Toevoegen (stagen):**  `git add .`
6. **Commit maken:**  `git commit -m "Jouw omschrijving"`
7. **Pushen:**  `git push`
8. **(Optioneel) Pullen:**  `git pull`
9. **Log bekijken:**  `git log --oneline`

---

**Tip:** Herhaal stap 4–7 zo vaak als nodig!