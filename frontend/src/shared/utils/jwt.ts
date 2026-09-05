export interface StaffTokenPayload {
    sub: string;
    login: string;
    name: string;
    role: "admin" | "atendente" | "caixa" | "entregador";
    restaurant_id: string;
    type: "admin";
    exp: number;
}

export function decodeJwtPayload<T = StaffTokenPayload>(token: string): T {
    const [, payloadB64] = token.split(".");

    if (!payloadB64) {
        throw new Error("Token inválido.");
    }

    const json = atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as T;
}