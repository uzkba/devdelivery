// features/auth/services/authService.ts
import { adminApi } from "../../../shared/api/adminApi";

export interface LoginRequest {
    login: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    expires_in: number;
}

export async function loginAdmin(payload: LoginRequest): Promise<TokenResponse> {
    const { data } = await adminApi.post<TokenResponse>("/auth/login/admin", payload);
    return data;
}