import type { NextApiRequest, NextApiResponse } from "next";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, body, query } = req;

  try {
    let response;
    if (method === "POST") {
      // Start new analysis session
      response = await fetch(`${BACKEND_URL}/api/v1/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } else if (method === "GET" && query.session_id) {
      // Get current session state
      response = await fetch(`${BACKEND_URL}/api/v1/state/${query.session_id}`);
    } else if (method === "DELETE" && query.session_id) {
      // Stop session
      response = await fetch(`${BACKEND_URL}/api/v1/stop/${query.session_id}`, { method: "DELETE" });
    } else {
      return res.status(400).json({ message: "Invalid request. Use POST to start or GET with session_id to poll." });
    }

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `Backend error: ${response.status}`);
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error: any) {
    console.error("API Route Error:", error);
    return res.status(500).json({ message: error.message || "Backend connection failed. Is the Python server running on port 8000?" });
  }
}
