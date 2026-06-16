import type { NextApiRequest, NextApiResponse } from "next";
import { getBackendUrl } from "@/lib/backend-url";

const BACKEND_URL = getBackendUrl();

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ message: "Method not allowed" });
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/speed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      const contentType = response.headers.get("content-type") || "";

      if (contentType.includes("application/json")) {
        return res.status(response.status).send(errorText);
      }

      return res.status(response.status).json({ message: errorText || `Backend error: ${response.status}` });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error: any) {
    console.error("Speed API Error:", error);
    return res.status(500).json({ message: error.message || "Backend connection failed." });
  }
}
