# Handoff — Csaba emailjének feldolgozása (2026-07-09/11)

Git állapot ennek a session-nek a végén: minden módosítás `git add`-olva (staged),
**nincs commitolva és nincs pusholva**. Legközelebb el kell dönteni, commitoljuk-e.

## ✅ Elkészült

1. **Menüpont átnevezés** — „Train Your Own Aging Clock" → **„Train your own
   gene set-specific aging clock"** (fájl átnevezve, oldalcím + H1 frissítve).

2. **Beépített génhalmaz a Train oldalon** — GenAge humán öregedési
   géndatabázis, **307 gén** (pont annyi, mint a Csaba által linkelt cikkben).
   Új „Gene set source" választó a Train oldalon: saját feltöltés vagy
   beépített lista (`backend/data/example_genesets/genage_human_aging_genes.csv`,
   `backend/services/example_genesets_service.py`).

3. **Beépített adathalmaz az Apply oldalon** — eddig itt semmi nem volt, most
   van egy 36 mintás demo, ami **100%-ban lefedi mind a 4 beépített órát**
   (`backend/data/example_datasets/apply_demo_inflammatory_clocks_*.csv`).

4. **„Blood inflammatory Clock 2"** — kiderült, hogy ez már eleve
   kiválasztható volt (nem kellett hozzáadni), csak nem volt hozzá demo adat —
   azt pótoltuk. Teszt eredmény: MAE≈6.7 év, R≈0.85.

5. **Jó eredmény demonstrálása** — beépített adat + GenAge génhalmaz +
   ElasticNetCV: **MAE≈7.4 év, R≈0.85** (a korábbi CD74-es 21 CpG-s rossz
   eredmény helyett).

6. **Hiperparaméter-optimalizálás** — új „Automatically optimize
   regularization strength" checkbox (`ElasticNetCV`, belső CV-vel, ~1-3 perc
   futásidő), alapból bekapcsolva. Kikapcsolható manuális alpha/l1_ratio-ra.
   (`backend/services/train_preprocess.py::train_elasticnet_model`)

7. **CpG letöltés** — tanítás után CSV-ben letölthető a kiválasztott
   (nemnulla együtthatós) CpG-lista + koefficiensek.

**Mellékesen talált és javított hiba:** a régi „demo_blood" adathalmaz 1281
CpG-sorából 1260 üres volt (adathiba) — csak 21 valódi CpG-t tartalmazott
ténylegesen. Ezt megtisztítottam és a leírást pontosítottam.

## ⚠️ Nyitott pontok / nem lett elvégezve

- **Nincs commitolva/pusholva** — erről dönteni kell.
- **A „Multi-tissue inflammatory clock" gyengén teljesít** az új Apply-demo
  adaton (R negatív) — valószínűleg platform-inkompatibilitás (450k vs EPIC
  array). Ezt érdemes Csabával egyeztetni, nincs kijavítva, csak észlelve.
- **Optuna nem került bevezetésre** — Peti döntése alapján ElasticNetCV-t
  használtam helyette (nincs új dependency).
- **A pontos Nature-cikk (s41598-018-22240-w) gén listáját nem sikerült
  elérni** (login/cookie fal) — GenAge adatbázist használtam helyette (307 gén
  egyezik, de nem 100%-osan biztos, hogy ugyanaz a lista).
- **UI nem lett élesben tesztelve böngészőben** (streamlit szerver indítása,
  kattintgatás) — csak backend logika + a meglévő automata tesztkészlet lett
  lefuttatva.
- A már korábban is hibás tesztek (auth-szolgáltatás, illetve az
  ElasticNet/XGBoost/RandomForest `hasattr(model, "coef_"/"feature_importances_")`
  tesztek `tests/services/test_train_preprocess_services.py`-ban) **nem lettek
  javítva** — ezek a mostani módosítások előtt is hibásak voltak (Pipeline-t
  ad vissza a függvény, nem a bare estimatort), nem tartoztak a kérés körébe.

## Módosított/új fájlok

```
A  backend/data/example_datasets/apply_demo_inflammatory_clocks_beta.csv
A  backend/data/example_datasets/apply_demo_inflammatory_clocks_meta.csv
M  backend/data/example_datasets/demo_blood_beta.csv
A  backend/data/example_genesets/genage_human_aging_genes.csv
M  backend/services/example_datasets_service.py
A  backend/services/example_genesets_service.py
M  backend/services/train_preprocess.py
M  backend/services/train_service.py
M  frontend/pages/2_Apply_Built-in_Aging_Clocks.py
R  frontend/pages/3_Train_Your_Own_Aging_Clock.py -> frontend/pages/3_Train_your_own_gene_set-specific_aging_clock.py
M  frontend/utils.py
M  tests/services/test_train_service.py
```

---

# Handoff 2. — állítható train/eval split + az órák titkos feature-listái (2026-07-28)

## 1. Állítható tanító/kiértékelő split

Eddig fixen 80/20 volt beégetve (`train_test_split(..., test_size=0.2)`).
Most a Train oldalon a modellválasztás után megjelenik egy **"Percentage of the
dataset used for training"** csúszka: **50–90%**, 5%-os léptékkel, **alapérték 80%**
(tehát a régi viselkedés a default). A frontend `test_size`-ként küldi a
`/train/train_model/` végpontnak, a backend validálja (0.1–0.5 közötti érték,
pydantic `Field` + szolgáltatás-szintű ellenőrzés is), és a tanítás után
kiírjuk, hány mintán tanult és hány visszatartott mintán mértünk.

**Mellékesen javított hiba:** a RandomForest paraméterei sosem érkeztek meg a
backendre. A frontend `f"{model_choice.lower()}_params"` kulccsal olvasta a
session state-et, ami RandomForest esetén `"randomforest_params"` — a tárolt
kulcs viszont `"random_forest_params"`, így üres dict `{}` ment el, és a backend
mindig a saját defaultjaival tanított. Most explicit kulcs-mapping van.

## 2. A Clock 1 / Clock 2 feature-listák titkosítása

Csaba kérése: a "Blood inflammatory Clock 1" és "Clock 2" CpG-listái üzleti
titkok, kliens ne tudja őket megszerezni.

**a) Titkosítás nyugalmi állapotban (encryption at rest).** Az érintett fájlok
már csak `.enc` formában (Fernet / AES-128-CBC + HMAC) vannak a lemezen:

```
backend/data/hannum_elnet_cg_order.csv.enc                      (Clock 1 input order)
backend/data/Hannum_Inflammation_elnet_nonzero_cpg_order.csv.enc (Clock 1 nemnulla CpG-k)
backend/data/inflamm_hugging_models_cg_order.csv.enc            (Clock 2 + XGBoost input order)
backend/data/computage_elnet_nonzero_cpg_order.csv.enc          (Clock 2 nemnulla CpG-k)
backend/data/inflammation_cg_means.csv.enc                      (az összes óra CpG-jének uniója!)
backend/data/example_datasets/apply_demo_inflammatory_clocks_beta.csv.enc
```

Az utolsó kettő is titok: a `cg_means` tábla és a 100%-os lefedettségre épített
Apply-demo adathalmaz sorindexe **maga az órák CpG-halmazának uniója**, tehát
plaintextben hagyva értelmetlen lett volna a többi fájlt titkosítani.

A backend `backend/services/secure_features_service.py`-n keresztül memóriában
dekódolja (és processzenként cache-eli) őket. A demo adathalmazt a
`materialize_example_prediction_dataset()` írja ki a user temp könyvtárába.

**b) A kulcs.** Sorrendben: `CLOCK_FEATURES_KEY` env var → `CLOCK_FEATURES_KEY_FILE`
env var → `<PROJECT_ROOT>/.secrets/clock_features.key` (gitignore-olt, ez a
default). A kulcs **nincs és soha nem is lehet a repóban**.

> ⚠️ **DEPLOY LÉPÉS:** a `.secrets/clock_features.key` fájlt kézzel (scp/rsync)
> át kell másolni a szerverre, különben a beépített órák nem indulnak el
> ("No encryption key found..."). A kulcsot **le kell menteni biztos helyre** —
> nélküle az `.enc` fájlok visszafejthetetlenek. A jelenlegi kulcs a fejlesztői
> gépen a fenti útvonalon van.

Kezelő szkript: `scripts/protect_clock_features.py --init | --encrypt
[--remove-plaintext] | --decrypt | --status`.

**c) API-oldali szivárgási utak lezárása.**

- `/predictions/predict/` és `/predictions/calculate_percent/` eddig **teljesen
  authentikáció nélkül** hívható volt — most mindkettő bejelentkezést igényel
  (a frontend 2. oldala küldi a Bearer tokent).
- Új `backend/services/path_guard.py`: a klienstől kapott fájlútvonalak csak a
  user temp könyvtárára és a beépített example dataset/geneset mappákra
  mutathatnak. Ez zárja azt a rést, amivel a `/train/check_dfs/` +
  `/train/gene_cpgs_request/` páros bármelyik szerveroldali fájl sorindexét
  visszaolvashatóvá tette (pl. pont a titkos CpG-listákat), és ugyanez a védelem
  került a predikciós végpontokra is.
- A lefedettségi százalékok mostantól **5%-os lépcsőkben, lefelé kerekítve**
  jönnek vissza ("at least 85%"), plusz a végpont óránként max 60 hívást engedélyez
  felhasználónként. Pontos százalékkal egyedi CpG-kre lehetett kérdezni
  (1 CpG-s fájl → nem-nulla lefedettség = a CpG az órában van), és így
  visszafejthető volt a teljes lista.

## ⚠️ Nyitott pont

- A plaintext CSV-k **benne maradtak a git history-ban** (a korábbi commitokban).
  Aki a repó teljes történetét látja, ma is ki tudja szedni őket. A history
  átírása (`git filter-repo`) külön, invazívabb művelet — Peti döntése alapján
  ez most nem történt meg. A working tree-ből törölve vannak, és a `.gitignore`
  megakadályozza a visszakerülésüket.

## Módosított/új fájlok

```
A  backend/services/secure_features_service.py
A  backend/services/path_guard.py
A  scripts/protect_clock_features.py
A  tests/services/test_protected_clock_features.py
A  backend/data/*.enc  (6 db, lásd fent)
D  backend/data/*.csv  (a 6 titkosított fájl plaintext változata)
M  backend/routers/predictions_router.py
M  backend/routers/train_router.py
M  backend/schemas/train_schema.py
M  backend/services/predictive_model_service.py
M  backend/services/train_service.py
M  backend/services/example_datasets_service.py
M  frontend/pages/2_Apply_Built-in_Aging_Clocks.py
M  frontend/pages/3_Train_your_own_gene_set-specific_aging_clock.py
M  tests/routers/test_predictions_router.py
M  requirements.txt   (cryptography==46.0.5)
M  .gitignore
```

## Teszt-állapot

`python -m pytest tests -q` → **21 failed, 55 passed**. A 21 hiba pontosan
ugyanaz a készlet, ami a módosítások előtt is bukott (auth-szolgáltatás,
train_preprocess Pipeline-tesztek, nagy adatfájlos tesztek) — új hiba nincs,
a korábbi 36 passed-ből 55 lett. Az órák predikciója dekódolt fájlokkal
ellenőrizve: Clock 2 az Apply-demón MAE≈6.71 / R≈0.85, ugyanaz, mint
titkosítás előtt.
