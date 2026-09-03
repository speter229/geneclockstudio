# RESUME HERE — hol tartunk és mi a következő lépés

**Utolsó session: 2026-07-28.** Ez a dokumentum az egyetlen belépési pont a
folytatáshoz. Ha új Claude Code sessiont indítasz, ezt add oda neki elsőnek
(`Read RESUME_HERE.md`), és onnan folytatjátok.

Részletes technikai leírás: `HANDOFF.md` (két szekció: 2026-07-09/11 és 2026-07-28).

---

## 1. Git-állapot — EZ A LEGFONTOSABB

```
main = origin/main = 06ccb75   ("Implement Csaba's requested demo/UX improvements")
```

- **Csaba email-batch (7 pont) → KÉSZ, commitolva ÉS pusholva** (`06ccb75`).
  (A `HANDOFF.md` első szekciója még azt írja, hogy "staged, nincs commitolva" —
  ez már elavult, azóta ki lett commitolva.)
- **A 2026-07-28-i munka (split slider + óra-titkosítás) → KÉSZ, DE NINCS
  COMMITOLVA és nincs pusholva.** Minden változás a working tree-ben ül,
  semmi nincs `git add`-elve.

Ellenőrzés induláskor:

```bash
git log --oneline -1        # 06ccb75-öt kell látni
git status --short          # ~27 sor: M/D/?? bejegyzések
```

Ha a `git status` üres és a log-ban új commit van → valaki (te) már
commitolta, akkor ez a pont kész, ugorj a 4. szekcióra.

---

## 2. Mi készült el a 2026-07-28-i sessionben

### a) Állítható tanító/kiértékelő split (Csaba kérése)
Train oldalon csúszka: **50–90%, 5%-os lépték, default 80%** (= a régi fix
80/20 marad az alapértelmezés). Backend validál (0.1–0.5), tanítás után
kiírja a train/test mintaszámot.
Mellékesen javítva: a RandomForest hiperparaméterei sosem jutottak el a
backendre (rossz session-state kulcs), mindig a backend defaultjaival tanult.

### b) Clock 1 / Clock 2 CpG-listák titkosítása (Csaba kérése)
- 6 fájl már csak `.enc` formában van a lemezen (Fernet titkosítás), plaintext
  törölve a working tree-ből.
- `/predictions/predict/` és `/calculate_percent/` eddig **auth nélkül** volt
  hívható → most bejelentkezés kell.
- Új path guard: klienstől jövő fájlútvonal csak user-temp / example mappákra
  mutathat (ez zárta a `/train/check_dfs/` + `/gene_cpgs_request/` réstt, amivel
  bármelyik szerveroldali fájl sorindexe visszaolvasható volt).
- Lefedettségi % → 5%-os lépcsőkben, lefelé kerekítve + óránként max 60 hívás.

### Tesztállapot
`python -m pytest tests -q` → **21 failed, 55 passed**.
A 21 bukó teszt **pontosan ugyanaz a készlet, ami a módosítások előtt is bukott**
(auth-service tesztek, train_preprocess Pipeline-tesztek, nagy adatfájlos
tesztek). Új hiba nincs. Ha legközelebb más számot látsz, az regresszió.

> Megjegyzés: a tesztfuttatás importálja a `backend.main`-t, ami törli a
> `backend/temp/` tartalmát — emiatt a `backend/temp/.gitkeep` eltűnhet a
> working tree-ből. Ha a `git status`-ban `D backend/temp/.gitkeep` jelenik meg,
> csak `git checkout -- backend/temp/.gitkeep`, nem valódi hiba.

---

## 3. ⚠️ A TITKOSÍTÓ KULCS — el ne veszítsd

A `.enc` fájlok kulcs nélkül **visszafejthetetlenek**, és nélkülük a beépített
órák egyáltalán nem indulnak el ("No encryption key found...").

**Hol van most a kulcs:**

| Hely | Megjegyzés |
|---|---|
| `<repo>/.secrets/clock_features.key` | ezt használja az app; gitignore-olva, sosem kerül a repóba |
| `C:\Users\sando\clock_features_backup_2026-07-28\` | biztonsági másolat: a kulcs **és** mind a 6 plaintext CSV |

**Tennivaló:** tedd a kulcsot valami tartós helyre is (jelszókezelő / titkosított
backup). A `C:\Users\sando\...` mappa csak ezen a gépen van meg.

**Deploy-nál:** a kulcsfájlt kézzel (scp/rsync) át kell másolni a szerverre a
`<repo>/.secrets/clock_features.key` útvonalra — vagy `CLOCK_FEATURES_KEY` /
`CLOCK_FEATURES_KEY_FILE` env varral megadni. Git-tel SOHA.

Kezelőszkript:

```bash
python scripts/protect_clock_features.py --status     # mi van titkosítva, van-e kulcs
python scripts/protect_clock_features.py --decrypt    # karbantartáshoz visszafejt
python scripts/protect_clock_features.py --encrypt --remove-plaintext
```

---

## 4. KÖVETKEZŐ LÉPÉSEK (prioritás szerint)

### 4.1 Döntés: commitoljuk-e a mostani munkát? — ELSŐ TEENDŐ
A változások review-ra várnak. Ha jónak találod:

```bash
git add -A
git commit    # javasolt üzenet lentebb
git push
```

Javasolt commit-üzenet:

```
Add adjustable train/eval split and protect the inflammatory clock feature lists

- Train page: 50-90% training split slider (default 80%), validated end to end
- Fix RandomForest hyperparameters never reaching the backend (wrong state key)
- Encrypt the Clock 1 / Clock 2 CpG lists at rest; decrypt in memory only
- Require authentication on the prediction endpoints
- Restrict client-supplied file paths to the user data directories
- Report clock coverage in 5% buckets and rate-limit the endpoint
```

> ⚠️ A commit **6 CSV törlését** is tartalmazza. Ez szándékos (helyettük `.enc`
> fájlok kerülnek be). Push előtt győződj meg róla, hogy a kulcs backupolva van
> (3. szekció), különben a szerveren nem fognak elindulni az órák.

### 4.2 Böngészős teszt — még sosem történt meg
Sem a júliusi batch, sem a mostani nincs kézzel végigkattintva. Indítás:

```bash
# 1. terminál (backend)
python backend/main.py
# 2. terminál (frontend)
streamlit run frontend/Home_Page.py
```

Amit végig kell nézni:
- **Train oldal:** megjelenik-e a split csúszka a modellválasztás után,
  működik-e 50%-on és 90%-on is, stimmel-e a kiírt train/test mintaszám.
- **Apply oldal:** bejelentkezve megy-e a predikció (most már token kell!),
  a lefedettség "at least X%" formában jelenik-e meg, betölt-e a beépített
  demo adathalmaz (ez most a titkosított fájlból íródik ki).
- **RandomForest tanítás:** a javítás után tényleg a beállított paraméterekkel
  tanul-e (a backend logban látszik).

### 4.3 Nyitott, nem eldöntött kérdések
1. **Plaintext CSV-k a git history-ban.** A régi commitokban (`fbaf33c`,
   `caed7dd`, `06ccb75`) ott vannak a titkos CpG-listák olvashatóan. Aki a teljes
   repót klónozza, ma is ki tudja szedni őket. Lezárás = `git filter-repo` +
   force push + **új kulcs generálása és újratitkosítás**. Invazív, és a
   GitHub-on maradhatnak cache-elt objektumok — ezt te döntötted el, hogy most
   nem csináljuk. Ha a repó publikus vagy publikus lesz, ezt újra kell gondolni.
2. **"Multi-tissue inflammatory clock" gyenge teljesítménye** az Apply-demo
   adaton (negatív R) — valószínűleg 450k vs EPIC platform-inkompatibilitás.
   Még mindig **nincs kijavítva**, Csabával egyeztetendő. (Júliusi nyitott pont.)
3. **A 21 régóta bukó teszt** (auth-service, train_preprocess Pipeline-tesztek,
   nagy adatfájlos tesztek) továbbra sincs javítva — a júliusi és a mostani
   kérésnek sem volt része. Ha egyszer rendbe akarod tenni, ez egy jól
   körülhatárolt, önálló feladat.
4. **Az `.enc` fájlok bináris blobok a gitben.** Kicsik (pár száz KB), de minden
   újratitkosítás új blobot hoz létre (a Fernet minden futásnál más kimenetet ad
   ugyanarra a bemenetre). Ne futtasd feleslegesen az `--encrypt`-et, mert
   hízlalja a repót.

---

## 5. Ha új Claude Code sessiont indítasz

Add oda neki ezt indításkor:

> Olvasd el a `RESUME_HERE.md`-t és a `HANDOFF.md`-t a repo gyökerében, aztán
> mondd meg, hol tartunk és mi a következő lépés.

Amit elsőnek ellenőrizzen: `git log --oneline -1`, `git status --short`,
`python scripts/protect_clock_features.py --status`.
