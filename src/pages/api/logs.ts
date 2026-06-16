import type { NextApiRequest, NextApiResponse } from "next";

const BACKEND_URL = "http://127.0.0.1:8000";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET") {
    return res.status(405).json({ message: "Method not allowed" });
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(req.query)) {
    if (Array.isArray(value)) {
      if (value[0]) params.set(key, value[0]);
    } else if (value) {
      params.set(key, value);
    }
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/logs?${params.toString()}`);

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `Backend error: ${response.status}`);
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error: any) {
    console.error("Logs API Error:", error);
    return res.status(500).json({
      message: error.message || "Backend logs unavailable. Is the Python server running on port 8000?",
    });
  }
}
