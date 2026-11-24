import axios from "axios";
export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 140000,
  withCredentials: true,
});
export const request = async (method, url, data, config = {}) =>
  (await api({ method, url, data, ...config })).data.data;
export const message = (e) =>
  e.response?.data?.error?.message ||
  (e.code === "ECONNABORTED"
    ? "The request timed out. Try again."
    : e.response
      ? "Request failed."
      : "Cannot reach the backend. Check the local servers.");
export const genres = [
  "blues",
  "classical",
  "country",
  "disco",
  "hiphop",
  "jazz",
  "metal",
  "pop",
  "reggae",
  "rock",
];
export const genreName = (g) =>
  g === "hiphop" ? "Hip-hop" : g ? g[0].toUpperCase() + g.slice(1) : "—";
export const pct = (n) => (n == null ? "—" : `${(n * 100).toFixed(1)}%`);
export const duration = (n) =>
  `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, "0")}`;
export const date = (s) => new Date(s).toLocaleString();
