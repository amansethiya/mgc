# REST API contract (v1)

## FastAPI (private, port 8000)

- GET `/health`: service status and `modelReady`.
- GET `/api/v1/genres`: array of 10 lowercase keys.
- GET `/api/v1/model/info`: `ready`, `modelVersion`, `genres`, `preprocessing`.
- POST `/api/v1/predict`: multipart field `file` (MP3/WAV, 25 MiB maximum, 5 seconds minimum). Analyze at most first 30 seconds.
- GET `/docs`: Swagger.

All successful JSON responses use `{ "success": true, "data": ... }`. Prediction data contains `predictedGenre`, `confidenceScore`, `probabilities`, `audioDuration`, `analyzedDuration`, `modelVersion`. Genre keys: blues, classical, country, disco, hiphop, jazz, metal, pop, reggae, rock. Probabilities are floats [0,1] and sum to approximately one. Returned class is the probability argmax. Durations in seconds. No fake predictions when model is absent.

Errors: `{ "success": false, "error": { "code": "MODEL_NOT_READY", "message": "Train the GTZAN model and restart the ML service." } }` (503 example). Invalid audio 400, oversized 413, format 415, missing field 422, unexpected 500.

## Express (port 5000, prefix /api/v1)

| Method | Path | Input / return | Access |
|---|---|---|---|
| GET | /health | database status | Public |
| GET | /model/info | proxied model info | Public |
| POST | /auth/register | username, email, password; user data | Public |
| POST | /auth/login | email, password; user data | Public |
| POST | /auth/logout | clears HttpOnly cookie | Public |
| GET | /auth/me | current user | Session |
| POST | /predictions | multipart file; saved prediction | Session |
| GET | /predictions?page=1 | items, total, page, limit (20) | Session |
| GET | /predictions/:id | saved prediction | Owner |
| GET | /predictions/:id/audio | audio bytes, Range supported | Owner |
| DELETE | /predictions/:id | deletes prediction and attempts file cleanup | Owner |
| GET | /dashboard/stats | total, averageConfidence, mostFrequentGenre, distribution, recent | Session |

JWT cookie `genre_session` expires in one day. Cookie flags HttpOnly, SameSite=Lax, Secure in production. Requests from a browser must use the configured APP_ORIGIN; keep frontend and API on the same origin. Invalid or missing session 401; cross-user record access 404; duplicate email 409; throttling 429; ML unavailable 502 or model-not-ready 503. Node passes validated ML errors to the frontend. The audio endpoint returns bytes rather than JSON.
