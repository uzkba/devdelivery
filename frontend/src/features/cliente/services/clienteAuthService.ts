import { clientApi } from "../../../shared/api/clientApi";

export interface ClienteLoginRequest {
    phone: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    expires_in: number;
}

export async function loginCliente(
    payload: ClienteLoginRequest,
): Promise<TokenResponse> {
    const { data } = await clientApi.post<TokenResponse>("/clientes/login", payload);
    return data;
}