import type { AxiosError, InternalAxiosRequestConfig } from "axios";
import { createApiInstance } from "./apiFactory";
import { clientTokenStorage } from "../auth/tokenStorage";

export const clientApi = createApiInstance();

clientApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = clientTokenStorage.get();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

clientApi.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
        clientTokenStorage.clear();
        if (!window.location.pathname.startsWith("/cliente/login")) {
            window.location.href = "/cliente/login";
        }
        }
        return Promise.reject(error);
    }
);