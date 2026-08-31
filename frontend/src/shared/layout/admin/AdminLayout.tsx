import {
    BarChart3,
    BookOpen,
    ClipboardList,
    LayoutDashboard,
    LogOut,
    Wallet,
} from "lucide-react";
import {
    NavLink,
    Navigate,
    Outlet,
    useLocation,
    useNavigate,
} from "react-router-dom";

import { useAuth, type UserRole } from "../../auth/AuthContext";

interface MenuItem {
    label: string;
    path: string;
    icon: typeof LayoutDashboard;
    roles: UserRole[];
}

const menuItems: MenuItem[] = [
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

const roleLabels: Record<UserRole, string> = {
    admin: "Administrador",
    atendente: "Atendente",
    caixa: "Caixa",
    entregador: "Entregador",
};

function isMenuItemActive(path: string, currentPath: string): boolean {
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
        return <Navigate to="/login" replace />;
    }

    const visibleMenuItems = menuItems.filter((item) =>
        item.roles.includes(user.role),
    );

    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };

    return (
        <div className="min-h-screen bg-[#fffaf4] text-[#21170f]">
            <aside className="fixed inset-y-0 left-0 z-30 flex w-55.5 flex-col bg-[#241004] text-white">
                <div className="border-b border-white/10 px-5 py-5">
                    <p className="text-[12px] font-bold tracking-wide text-[#d49b32]">
                        DEVDELIVERY
                    </p>

                    <h1 className="mt-1 font-serif text-[17px] font-bold leading-tight">
                        Marmitaria Sabor &amp;
                        <br />
                        Arte
                    </h1>
                </div>

                <nav className="flex-1 px-2.5 py-4">
                    <div className="space-y-1">
                        {visibleMenuItems.map((item) => {
                        const Icon = item.icon;
                        const active = isMenuItemActive(item.path, location.pathname);

                        return (
                            <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === "/admin"}
                            className={[
                                "flex items-center gap-3 rounded-xl px-3 py-2.5",
                                "text-sm font-semibold transition-colors",
                                active
                                ? "bg-[#ff7315] text-white"
                                : "text-[#d7c7b4] hover:bg-white/5 hover:text-white",
                            ].join(" ")}
                            >
                            <Icon size={18} strokeWidth={1.8} />

                            <span>{item.label}</span>
                            </NavLink>
                        );
                        })}
                    </div>
                </nav>

                <div className="border-t border-white/10 px-3 py-4">
                    <div className="flex items-center justify-between gap-3 rounded-lg px-1">
                        <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-white">
                                {user.nome}
                            </p>

                            <p className="mt-0.5 text-xs text-[#d49b32]">
                                {roleLabels[user.role]}
                            </p>
                        </div>

                        <button
                        type="button"
                        onClick={handleLogout}
                        title="Sair"
                        aria-label="Sair"
                        className="shrink-0 rounded-md p-2 text-[#a88c6e] transition-colors hover:bg-white/5 hover:text-white"
                        >
                            <LogOut size={17} strokeWidth={1.8} />
                        </button>
                    </div>
                </div>
            </aside>

            <div className="min-h-screen pl-55.5">
                <header className="sticky top-0 z-20 flex h-12.5 items-center justify-between border-b border-[#ead8c5] bg-white px-6">
                <div className="flex items-center gap-2 text-sm">
                    <span className="font-semibold text-[#21170f]">
                        Restaurante
                    </span>

                    <span className="text-[#b99e85]">›</span>

                    <span className="text-[#b99e85]">
                        {getPageLabel(location.pathname)}
                    </span>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-[#704d32]">
                        {getCurrentTime()}
                    </span>

                    <span className="rounded-lg border border-[#ffb66f] bg-[#fff7ed] px-3 py-1 text-xs font-semibold text-[#e76812]">
                        {roleLabels[user.role]}
                    </span>
                </div>
                </header>

                <main className="min-h-[calc(100vh-50px)] px-6 py-6">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}

function getPageLabel(pathname: string): string {
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

function getCurrentTime(): string {
    return new Intl.DateTimeFormat("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date());
}