# RESUME HERE — hol tartunk és mi a következő lépés

**Utolsó session: 2026-09-03.** Ez a dokumentum az egyetlen belépési pont a
folytatáshoz. Ha új Claude Code sessiont indítasz, ezt add oda neki elsőnek
(`Read RESUME_HERE.md`).

Részletes technikai leírás: `HANDOFF.md`.

---

## 1. Git-állapot

```
main = origin/main = 9b6aeea   ("Add adjustable train/eval split and protect the
                                inflammatory clock features")
```

**A 2026-07-28-i munka (split csúszka + óra-titkosítás) + a 2026-09-03-i
biztonsági megerősítés → KÉSZ, COMMITOLVA ÉS PUSHOLVA.** A working tree tiszta.

---

## 2. Mi készült el

### a) Állítható tanító/kiértékelő split
Train oldalon csúszka: **50–90%, 5%-os lépték, default 80%**. A backend validál
(0.1–0.5), tanítás után kiírja a train/test mintaszámot.

Böngészőben végigtesztelve: 60%-ra állítva a backend tényleg 393/263-at tanít
(656 mintából), és a UI is ezt írja ki.

> **Javított hiba:** a csúszkának nem volt `key`-e, ezért Streamlit rerun után
> csendben visszaugrott 80-ra — a felhasználó 60%-ot állított, mégis 80/20-szal
> tanult. Ezt csak a kézi böngészős teszt hozta ki, teszt nem fogta volna meg.

Mellékesen javítva: a RandomForest hiperparaméterei sosem jutottak el a
backendre (rossz session-state kulcs).

### b) Az óra-jellemzők védelme
- 6 fájl csak `.enc` formában van a lemezen (Fernet), plaintext törölve.
- `/predictions/*` és `/datasets/*` már **bejelentkezést igényel**.
- Path guard: klienstől jövő fájlútvonal csak user-temp / example mappákra
  mutathat.
- Lefedettségi % → 5%-os lépcsőkben, lefelé kerekítve.
- **Rate limit mindkét predikciós végponton** (`/calculate_percent/` 60/óra,
  `/predict/` 120/óra). A `/predict/` is orákulum: a predikció csak akkor
  mozdul, ha a beküldött CpG tényleg az óra jellemzője.
- A predikciós végpontok **nem küldik vissza a belső hibaszöveget** (CpG-neveket
  tartalmazhat).
- Ha egy védett fájl **csak plaintextben** van meg, az app megtagadja az
  olvasását (kivéve ha `CLOCK_FEATURES_ALLOW_PLAINTEXT=1`) — így egy ottfelejtett
  visszafejtett másolat nem kerüli meg csendben a titkosítást.
- A beépített demo adathalmaz CpG-sorneveit a UI **elrejti** (az indexe pont az
  órák jellemzőinek uniója).

Ellenőrizve: bejelentkezve 4 különböző úton próbáltam kiolvasni a CpG-listákat
(relatív út, abszolút út az `.enc`-re, `..` traversal, `gene_cpgs_request`) —
mind a 4 blokkolva. 63%-os valós lefedettség 60%-ként jelenik meg.

---

## 3. ⚠️ A TITKOSÍTÓ KULCS — el ne veszítsd

A `.enc` fájlok kulcs nélkül **visszafejthetetlenek**, és nélkülük a beépített
órák nem indulnak el.

| Hely | Megjegyzés |
|---|---|
| `<repo>/.secrets/clock_features.key` | ezt használja az app; gitignore-olva |
| `C:\Users\sando\clock_features_backup_2026-07-28\` | kulcs + mind a 6 plaintext CSV |

**Tedd a kulcsot tartós helyre is** (jelszókezelő / titkosított backup).

### ⚠️ DEPLOY — ezt kell megtenni a szerveren
A most pusholt commit **törli a 6 plaintext CSV-t**. A szerver a `git pull` után
**csak akkor fog működni, ha a kulcs ott van**:

```bash
# a szerveren, EGYSZER, git-en kívül (scp/rsync):
mkdir -p <repo>/.secrets
# másold ide: clock_features.key
```
vagy `CLOCK_FEATURES_KEY` / `CLOCK_FEATURES_KEY_FILE` env var.

Kulcs nélkül: "No encryption key found..." és az órák nem indulnak.

Kezelőszkript:
```bash
python scripts/protect_clock_features.py --status
python scripts/protect_clock_features.py --decrypt
python scripts/protect_clock_features.py --encrypt --remove-plaintext
```

---

## 4. Tesztállapot

`python -m pytest tests -q` → **7 failed, 89 passed** (a 23 új teszttel együtt).

A 7 bukó teszt egyike sem regresszió:
- **4 db** (`test_large_data_*`) a több GB-os beta CSV-ket kéri, amik
  gitignore-oltak — csak ott futnak le, ahol az adat fizikailag megvan.
- **3 db** (`test_train_preprocess_services`) `feature_importances_`-t vár egy
  `Pipeline`-on, ami nem is teszi közzé — **elavult teszt**, nem kódhiba.

> Korábban 21 bukó teszt volt. A különbség 14 auth-teszt, ami csak azért bukott,
> mert ezen a gépen a `bcrypt` verziója elcsúszott a `requirements.txt`-től.

---

## 5. ⚠️ Környezeti elcsúszás — FONTOS

**Az app a szerveren fut, nem lokálisan.** Ha valaki mégis lokálisan indítja,
tudni kell, hogy ezen a gépen a telepített csomagok **eltérnek** a
`requirements.txt`-től, és emiatt hibák jönnek elő, amik a szerveren nincsenek:

| Csomag | `requirements.txt` | Ezen a gépen volt |
|---|---|---|
| `bcrypt` | 4.3.0 | 5.0.0 → **login 500-zal elszállt** |
| `scikit-learn` | 1.3.0 | 1.9.0 → **ElasticNetCV `n_alphas` TypeError** |

A kód a kitűzött verziókkal helyes. Ne "javítsd" a kódot ezek miatt — a
`requirements.txt` szerinti verziókat kell telepíteni.

---

## 6. Nyitott, nem eldöntött kérdések

1. **Plaintext CSV-k a git history-ban.** A régi commitokban (`fbaf33c`,
   `caed7dd`, `06ccb75`) a titkos CpG-listák **olvashatóan ott vannak**. Aki a
   teljes repót klónozza, ma is ki tudja szedni őket — a mostani titkosítás csak
   a jelent védi, a múltat nem. Lezárás = `git filter-repo` + force push + **új
   kulcs + újratitkosítás**. Invazív; korábban úgy döntöttél, most nem csináljuk.
   **Ha a repó publikus vagy azzá válik, ezt újra kell gondolni** — ez a
   legnagyobb megmaradt rés.
2. **"Multi-tissue inflammatory clock" gyenge teljesítménye** az Apply-demo
   adaton (negatív R) — valószínűleg 450k vs EPIC platform-inkompatibilitás.
   Csabával egyeztetendő.
3. **A 3 elavult `train_preprocess` teszt** javítása (lásd 4. szekció).
4. **Apply oldal böngészős tesztje** még nem történt meg (a Train oldal igen).
5. **`## Choose a model`** — a Train oldalon a legördülő címkéjében nyersen
   látszik a `##` markdown, kozmetikai hiba.
