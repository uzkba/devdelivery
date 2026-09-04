import { describe, expect, it } from "vitest";
import { ADMIN_NAV_ITEMS, getRolesForPath, isNavItemActive } from "../adminNavItems";

describe("adminNavItems", () => {
    describe("getRolesForPath", () => {
        it("retorna as roles corretas para uma rota existente", () => {
            expect(getRolesForPath("/admin/relatorios")).toEqual(["admin"]);
            expect(getRolesForPath("/admin/pedidos")).toEqual([
                "admin",
                "atendente",
                "caixa",
                "entregador",
            ]);
        });

        it("lança erro para uma rota não registrada em ADMIN_NAV_ITEMS", () => {
            expect(() => getRolesForPath("/admin/inexistente")).toThrow(
                /Nenhum item de navegação admin encontrado/,
            );
        });
    });

    describe("isNavItemActive", () => {
        it("marca /admin como ativo apenas na rota exata (não por prefixo)", () => {
            expect(isNavItemActive("/admin", "/admin")).toBe(true);
            expect(isNavItemActive("/admin", "/admin/pedidos")).toBe(false);
        });

        it("marca rotas aninhadas como ativas por prefixo", () => {
            expect(isNavItemActive("/admin/pedidos", "/admin/pedidos")).toBe(true);
            expect(isNavItemActive("/admin/pedidos", "/admin/pedidos/123")).toBe(true);
            expect(isNavItemActive("/admin/pedidos", "/admin/relatorios")).toBe(false);
        });
    });

    it("todo item de ADMIN_NAV_ITEMS tem ao menos uma role associada", () => {
        for (const item of ADMIN_NAV_ITEMS) {
            expect(item.roles.length).toBeGreaterThan(0);
        }
    });
});