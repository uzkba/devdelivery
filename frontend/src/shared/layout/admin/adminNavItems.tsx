import {
    BarChart3,
    BookOpen,
    ClipboardList,
    LayoutDashboard,
    Wallet,
} from "lucide-react";
import type { ComponentType } from "react";

import type { UserRole } from "../../auth/AuthContext";

export interface AdminNavItem {
    label: string;
    /** Rótulo curto para a barra inferior (telas estreitas). Cai para `label` se ausente. */
    shortLabel?: string;
    path: string;
    icon: ComponentType<{ size?: number; strokeWidth?: number; color?: string }>;
    roles: UserRole[];
}

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
    {
        label: "Visão geral",
        shortLabel: "Início",
        path: "/admin",
        icon: LayoutDashboard,
        roles: ["admin", "atendente", "caixa", "entregador"],
    },
    {
        label: "Cardápio",
        path: "/admin/cardapio",
        icon: BookOpen,
        roles: ["admin", "atendente"],
    },
    {
        label: "Pedidos",
        path: "/admin/pedidos",
        icon: ClipboardList,
        roles: ["admin", "atendente", "caixa", "entregador"],
    },
    {
        label: "Relatórios",
        path: "/admin/relatorios",
        icon: BarChart3,
        roles: ["admin"],
    },
    {
        label: "Fechamento de caixa",
        shortLabel: "Caixa",
        path: "/admin/fechamento-caixa",
        icon: Wallet,
        roles: ["admin", "caixa"],
    },
];

export function isNavItemActive(path: string, currentPath: string): boolean {
    if (path === "/admin") {
        return currentPath === "/admin";
    }
    return currentPath.startsWith(path);
}

/**
 * Fonte única de roles por rota, usada pelo RequireRole em App.tsx.
 * Lança erro em tempo de import se a rota não existir em ADMIN_NAV_ITEMS —
 * preferível a um `!` silencioso: se alguém criar uma rota nova e esquecer
 * de registrá-la aqui, o app quebra no boot, não em produção.
 */
export function getRolesForPath(path: string): UserRole[] {
    const item = ADMIN_NAV_ITEMS.find((entry) => entry.path === path);

    if (!item) {
        throw new Error(
            `Nenhum item de navegação admin encontrado para "${path}". Registre-o em ADMIN_NAV_ITEMS antes de usar RequireRole.`,
        );
    }

    return item.roles;
}