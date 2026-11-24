import "dotenv/config";
import mongoose from "mongoose";
import { createApp } from "./app.js";
const {
  PORT = 5000,
  MONGODB_URI,
  JWT_SECRET,
  ML_URL = "http://127.0.0.1:8000",
  APP_ORIGIN = "http://localhost:5173",
  NODE_ENV,
} = process.env;
if (
  !MONGODB_URI ||
  !JWT_SECRET ||
  JWT_SECRET.length < 32 ||
  JWT_SECRET.startsWith("replace-")
) {
  console.error(
    "Set MONGODB_URI and a random JWT_SECRET (at least 32 characters) in backend/.env",
  );
  process.exit(1);
}
try {
  await mongoose.connect(MONGODB_URI, { serverSelectionTimeoutMS: 10000 });
  const server = createApp({
    jwtSecret: JWT_SECRET,
    mlUrl: ML_URL.replace(/\/$/, ""),
    origin: APP_ORIGIN,
    production: NODE_ENV === "production",
  }).listen(Number(PORT), "0.0.0.0", () =>
    console.log(`API listening at http://127.0.0.1:${PORT}`),
  );
  const stop = () =>
    server.close(async () => {
      await mongoose.disconnect();
      process.exit(0);
    });
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
} catch (e) {
  console.error("Startup failed:", e.message);
  process.exit(1);
}
