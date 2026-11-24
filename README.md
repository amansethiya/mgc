# GenreLab — Music Genre Classifier

BCA project | React + Express + MongoDB + independent Python FastAPI ML service.

## What is included

- Responsive dark-themed landing page, login/register, dashboard, drag-and-drop classification, audio preview, probability charts, model status, history, playback and deletion.
- Express API with JWT in HttpOnly cookies, bcrypt-compatible password hashing, private local uploads, per-user data access, input validation, rate limits and MongoDB models.
- Python service with actual Librosa feature extraction (75 features), Random Forest and SVM training, group-aware split, evaluation and artifact export. No external genre API. No hardcoded predictions.
- Test scripts and documentation. CNN is an optional extension, not implemented.

**Important:** The GTZAN audio dataset, database credentials and trained model are not included. Until a real model is trained, `/api/v1/predict` returns 503 and the classify UI displays a model-not-ready message. You can use authentication, dashboard, history and the upload preview once MongoDB and the Node service are running. No model accuracy has been claimed.

## Requirements

- Node.js 22, npm, Python 3.11 (recommended), VS Code.
- MongoDB Atlas connection or a running local MongoDB service.
- Internet access to download npm/pip dependencies and the dataset.
- Use a trusted dataset and your own audio. SoundFile 0.13+ supports MP3 through libsndfile on supported platforms; if MP3 decoding fails on your platform, convert to WAV with FFmpeg (`ffmpeg -i input.mp3 output.wav`).

## 1. Extract and open the project

Open the extracted `music-genre-classifier` folder in VS Code. In a terminal at the root:

```sh
npm run setup
npm run install:js
```

`setup` creates `backend/.env` with a random JWT secret, without overwriting an existing file. It defaults to a local MongoDB URI. Install and start local MongoDB first, OR use Atlas as described below.

### MongoDB Atlas (alternative to local MongoDB)

1. Create a cluster at https://www.mongodb.com/atlas and a database user with read/write access to your project database.
2. Allow your current IP in Network Access. Avoid opening the database to all IPs.
3. Copy the connection string, replace credentials (URL-encode special characters), and set `MONGODB_URI` in `backend/.env`. Use the database name `music_genre_classifier` in the URI. Do not share the secret or `.env` file.
4. Keep `APP_ORIGIN=http://localhost:5173`; use exactly that address in the browser. Ports default to 5173, 5000 and 8000.

## 2. Start the Python service (terminal 1)

```sh
cd ml-service
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If activation is blocked, use `.\.venv\Scripts\python.exe` in place of `python`; no execution policy change is needed. On macOS/Linux, create the environment with `python3 -m venv .venv` and activate it with `source .venv/bin/activate` before installing and starting the service.

Open http://127.0.0.1:8000/docs or http://127.0.0.1:8000/health. Model readiness will be false until training is complete.

## 3. Start the Node backend (terminal 2, root)

```sh
npm run dev:backend
```

Open http://127.0.0.1:5000/api/v1/health. Expected `database: connected`. If startup fails, verify MongoDB is running or Atlas network access/credentials are correct.

## 4. Start React (terminal 3, root)

```sh
npm run dev:frontend
```

Open **http://localhost:5173**. Register, sign in, explore the dashboard and preview an audio file. Do not use a different hostname for the frontend unless you update APP_ORIGIN. Vite forwards `/api` to Express, so authentication cookies and private audio work via the same origin.

## 5. Train the real model (ML developer)

Download GTZAN from https://www.kaggle.com/datasets/andradaolteanu/gtzan-dataset-music-genre-recognition . Extract the `genres_original` directory into `ml-service/dataset/` (check nesting). The directory must contain ten folders `blues`, `classical`, `country`, `disco`, `hiphop`, `jazz`, `metal`, `pop`, `reggae`, `rock` with audio inside each. No precomputed CSV needed.

From `ml-service`, with the virtual environment active:

```sh
python train.py --dataset dataset/genres_original
```

This scans and decodes tracks, extracts features, removes exact decoded excerpt duplicates, splits by groups, trains both models, selects by validation macro F1, evaluates on the held-out test set, and writes:

- `models/genre_model.joblib` — trained selected model and preprocessing metadata.
- `evaluation/dataset_audit.json` — skipped/corrupted files, class counts, duplicate report.
- `evaluation/splits.csv` — track/group split assignments.
- `evaluation/metrics.json` — actual validation/test accuracy, precision, recall, macro F1, timings and confusion matrices.
- `evaluation/random_forest_confusion.png`, `evaluation/svm_confusion.png` — held-out test confusion matrix plots.

Training takes time depending on your hardware and dataset. To prevent artist/recording leakage in final academic results, use a reviewed grouping manifest from verified GTZAN metadata: `python train.py --dataset dataset/genres_original --manifest dataset/groups.csv`. The CSV needs columns `path,group,exclude,reason` covering all discovered files. Assign the same group to tracks from the same artist and recordings that overlap (merge linked groups); set exclude=1 for known faults. See `docs/ml-method.md`. Without it the split is only track-disjoint and exact duplicates are removed, so disclose artist and near-duplicate leakage risk. Do not claim a definitive fault-filtered benchmark from the default split.

After training, stop and restart FastAPI. Verify `modelReady: true` at `/health`. Refresh the model status in the web app and upload a valid 5+ second song. The application stores the prediction in MongoDB and the audio in `backend/uploads`.

**Two computers:** The ML developer may train and send the trusted joblib artifact to the web developer. Use the same dependency versions on both computers (`python -m pip freeze > requirements-lock.txt` after installing); scikit-learn version is checked when loading. Copy the artifact to `ml-service/models/genre_model.joblib`. Or run FastAPI on a private network and configure Node's `ML_URL` to the private address after adding network access restrictions. Never load untrusted joblib files.

## 6. Testing

From root:

```sh
npm run test:backend
npm run build
```

From `ml-service` in the active environment:

```sh
python -m pytest -q
```

For real integration testing after all services are running with the trained model, use a disposable local database and a valid audio file:

```sh
npm run test:e2e -- "path/to/track.wav"
```

This creates two test accounts, performs real inference, checks history and cross-account isolation, verifies audio range playback, and deletes the generated prediction. Test accounts remain for manual removal. See `docs/testing.md` for the browser checklist.

## Ownership

Member 1: `frontend/`, `backend/`, MongoDB and integration. Member 2: `ml-service/`, dataset, training, evaluation and model API. Both: `docs/`, testing, report and deployment.

## Deployment notes

This is a local-first implementation. For production, serve the React build and `/api` from a common HTTPS origin using a reverse proxy, set `APP_ORIGIN` to that origin and `NODE_ENV=production` (Secure cookies). The Node server and Python server bind loopback by default; use a private network and explicit binding changes if separated. Keep FastAPI private, enforce request size/time/concurrency limits at the gateway, restrict model files, configure persistent private audio storage, configure database backups and an orphan-file cleanup process. JWT logout clears the browser cookie but does not revoke a copied token before expiration; add token revocation if required. For multi-instance deployments use shared persistent storage and a shared rate-limit store. No public deployment is supplied.

## Documentation

- `docs/architecture.md` — workflow and schemas
- `docs/api-contract.md` — endpoints and response shape
- `docs/ml-method.md` — ML approach and evaluation limitations
- `docs/testing.md` — verification and test results
#   m g c  
 