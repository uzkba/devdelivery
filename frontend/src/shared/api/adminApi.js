import { createApiInstance } from "./apiFactory";
import { adminTokenStorage } from "../auth/tokenStorage";
export const adminApi = createApiInstance();
// injeta o token do staff em toda requisição autenticada
adminApi.interceptors.request.use((config) => {
    const token = adminTokenStorage.get();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
// token expirado/inválido -> limpa sessão e manda pro login do staff
adminApi.interceptors.response.use((response) => response, (error) => {
    if (error.response?.status === 401) {
        adminTokenStorage.clear();
        if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
        }
    }
    return Promise.reject(error);
});
