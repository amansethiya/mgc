# Test plan

Included automated tests:
- Node: credential validation and strict ML response contract. Run `npm run test:backend`.
- Python: no-model response, unsupported/missing inputs, real feature extraction + probability transport with a synthetic estimator fixture, corrupt audio, group-disjoint split. Run `python -m pytest -q` from ml-service.
- E2E: real model and database required. Run `npm run test:e2e -- path/to/audio.wav` using a disposable database. Tests account isolation, history, stats, audio Range playback and deletion.

Manual browser checklist:
1. Register a new email; duplicate email returns an error; log out and log in again.
2. Open /dashboard while logged out; redirect to login. New user sees empty history and zero tracks.
3. Start FastAPI without artifact; UI reports model not ready. Preview a WAV or MP3 locally.
4. Train and restart ML, refresh status; upload a valid 5+ sec file. Check returned probabilities total about 100% and highest matches the genre.
5. Try .txt, oversized, corrupted WAV and a clip shorter than five seconds. Confirm errors and no saved prediction.
6. History lists result newest-first. Play private audio, view details and delete. Dashboard updates on navigation.
7. Register another account; it cannot view or delete the first account's predictions or audio. Check with E2E script.
8. Use a narrow mobile viewport. Check sidebar, forms, file selection and charts.
9. Stop FastAPI; model status or upload reports a service error instead of a fake result.

Verification at packaging: two Node validation tests passed and three Python tests passed in the available environment (synthetic estimator only for testing, not shipped). All frontend JS/JSX parsed successfully using a TypeScript syntax parser; npm registry access unavailable, so dependencies could not be installed here; React build, real Node/Mongo integration, actual GTZAN training and live cross-service tests are pending locally. No performance metrics are invented.
