import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { BarChart3, BookOpen, ClipboardList, LayoutDashboard, LogOut, Wallet, } from "lucide-react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate, } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
const menuItems = [
    {
        label: "Visão geral",
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
        path: "/admin/fechamento-caixa",
        icon: Wallet,
        roles: ["admin", "caixa"],
    },
];
const roleLabels = {
    admin: "Administrador",
    atendente: "Atendente",
    caixa: "Caixa",
    entregador: "Entregador",
};
function isMenuItemActive(path, currentPath) {
    if (path === "/admin") {
        return currentPath === "/admin";
    }
    return currentPath.startsWith(path);
}
export function AdminLayout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    if (!user) {
        return _jsx(Navigate, { to: "/login", replace: true });
    }
    const visibleMenuItems = menuItems.filter((item) => item.roles.includes(user.role));
    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };
    return (_jsxs("div", { className: "min-h-screen bg-[#fffaf4] text-[#21170f]", children: [_jsxs("aside", { className: "fixed inset-y-0 left-0 z-30 flex w-55.5 flex-col bg-[#241004] text-white", children: [_jsxs("div", { className: "border-b border-white/10 px-5 py-5", children: [_jsx("p", { className: "text-[12px] font-bold tracking-wide text-[#d49b32]", children: "DEVDELIVERY" }), _jsxs("h1", { className: "mt-1 font-serif text-[17px] font-bold leading-tight", children: ["Marmitaria Sabor &", _jsx("br", {}), "Arte"] })] }), _jsx("nav", { className: "flex-1 px-2.5 py-4", children: _jsx("div", { className: "space-y-1", children: visibleMenuItems.map((item) => {
                                const Icon = item.icon;
                                const active = isMenuItemActive(item.path, location.pathname);
                                return (_jsxs(NavLink, { to: item.path, end: item.path === "/admin", className: [
                                        "flex items-center gap-3 rounded-xl px-3 py-2.5",
                                        "text-sm font-semibold transition-colors",
                                        active
                                            ? "bg-[#ff7315] text-white"
                                            : "text-[#d7c7b4] hover:bg-white/5 hover:text-white",
                                    ].join(" "), children: [_jsx(Icon, { size: 18, strokeWidth: 1.8 }), _jsx("span", { children: item.label })] }, item.path));
                            }) }) }), _jsx("div", { className: "border-t border-white/10 px-3 py-4", children: _jsxs("div", { className: "flex items-center justify-between gap-3 rounded-lg px-1", children: [_jsxs("div", { className: "min-w-0", children: [_jsx("p", { className: "truncate text-sm font-semibold text-white", children: user.nome }), _jsx("p", { className: "mt-0.5 text-xs text-[#d49b32]", children: roleLabels[user.role] })] }), _jsx("button", { type: "button", onClick: handleLogout, title: "Sair", "aria-label": "Sair", className: "shrink-0 rounded-md p-2 text-[#a88c6e] transition-colors hover:bg-white/5 hover:text-white", children: _jsx(LogOut, { size: 17, strokeWidth: 1.8 }) })] }) })] }), _jsxs("div", { className: "min-h-screen pl-55.5", children: [_jsxs("header", { className: "sticky top-0 z-20 flex h-12.5 items-center justify-between border-b border-[#ead8c5] bg-white px-6", children: [_jsxs("div", { className: "flex items-center gap-2 text-sm", children: [_jsx("span", { className: "font-semibold text-[#21170f]", children: "Restaurante" }), _jsx("span", { className: "text-[#b99e85]", children: "\u203A" }), _jsx("span", { className: "text-[#b99e85]", children: getPageLabel(location.pathname) })] }), _jsxs("div", { className: "flex items-center gap-3", children: [_jsx("span", { className: "text-sm font-semibold text-[#704d32]", children: getCurrentTime() }), _jsx("span", { className: "rounded-lg border border-[#ffb66f] bg-[#fff7ed] px-3 py-1 text-xs font-semibold text-[#e76812]", children: roleLabels[user.role] })] })] }), _jsx("main", { className: "min-h-[calc(100vh-50px)] px-6 py-6", children: _jsx(Outlet, {}) })] })] }));
}
function getPageLabel(pathname) {
    if (pathname === "/admin") {
        return "Visão geral";
    }
    if (pathname.startsWith("/admin/cardapio")) {
        return "Cardápio";
    }
    if (pathname.startsWith("/admin/pedidos")) {
        return "Pedidos";
    }
    if (pathname.startsWith("/admin/relatorios")) {
        return "Relatórios";
    }
    if (pathname.startsWith("/admin/fechamento-caixa")) {
        return "Fechamento de caixa";
    }
    return "Visão geral";
}
function getCurrentTime() {
    return new Intl.DateTimeFormat("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date());
}
