import axios from "axios";
const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export function createApiInstance() {
    return axios.create({
        baseURL,
        headers: { "Content-Type": "application/json" },
    });
}
