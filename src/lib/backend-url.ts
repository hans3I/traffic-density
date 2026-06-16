const LOCAL_BACKEND_URL = "http://127.0.0.1:8000";

export function getBackendUrl() {
  const rawUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();

  if (!rawUrl) {
    return LOCAL_BACKEND_URL;
  }

  const normalizedUrl = /^https?:\/\//i.test(rawUrl) ? rawUrl : `https://${rawUrl}`;
  return normalizedUrl.replace(/\/+$/, "");
}
