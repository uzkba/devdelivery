import { describe, it, expect } from "vitest";
import { decodeJwtPayload } from "../jwt";

function buildToken(payload: object, { urlSafe = false } = {}) {
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    let body = btoa(JSON.stringify(payload));
    if (urlSafe) {
        body = body.replace(/\+/g, "-").replace(/\//g, "_");
    }
    return `${header}.${body}.assinatura-fake`;
}

const PAYLOAD = {
    sub: "admin-001",
    login: "marcos@devdelivery.com",
    name: "Marcos Ferreira",
    role: "admin",
    restaurant_id: "rest-001",
    type: "admin",
    exp: 9999999999,
};

describe("decodeJwtPayload", () => {
    it("decodifica corretamente o payload de um token válido", () => {
        expect(decodeJwtPayload(buildToken(PAYLOAD))).toEqual(PAYLOAD);
    });

    it("lida com caracteres url-safe (-, _) no payload", () => {
        expect(decodeJwtPayload(buildToken(PAYLOAD, { urlSafe: true }))).toEqual(PAYLOAD);
    });

    it("lança erro quando o token não tem o formato esperado (sem pontos)", () => {
        expect(() => decodeJwtPayload("token-sem-pontos")).toThrow("Token inválido.");
    });

    it("lança erro ao tentar decodificar um payload que não é base64 válido", () => {
        expect(() => decodeJwtPayload("header.###.sig")).toThrow();
    });
});