const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function requestJson(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });

    if (!response.ok) {
        throw new Error(`request failed ${response.status}`);
    }

    return response.json();
}

export function sendChatMessage(payload) {
    return requestJson("/chat", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export function authGoogle(idToken) {
    return requestJson("/auth/google", {
        method: "POST",
        body: JSON.stringify({ id_token: idToken }),
    });
}

export function getChatHistory(userId, sessionId) {
    return requestJson(`/history/${userId}/${sessionId}`);
}

export function trainModel() {
    return requestJson("/train", {
        method: "POST",
    });
}
