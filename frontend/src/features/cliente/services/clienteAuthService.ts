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

export interface ClienteRegisterRequest {
    name: string;
    phone: string;
    password: string;
}

export interface ClienteOut {
    id: string;
    name: string;
    phone: string;
    is_active: boolean;
}

export async function registrarCliente(
    payload: ClienteRegisterRequest,
): Promise<ClienteOut> {
    const { data } = await clientApi.post<ClienteOut>("/clientes/registrar", payload);
    return data;
}