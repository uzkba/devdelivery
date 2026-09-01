import { useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { ADMIN_NAV_ITEMS, isNavItemActive } from "./adminNavItems";

const ROLE_LABELS: Record<string, string> = {
    admin: "Administrador",
    atendente: "Atendente",
    caixa: "Caixa",
    entregador: "Entregador",
};

export function AdminLayout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    const visibleNavItems = ADMIN_NAV_ITEMS.filter((item) =>
        item.roles.includes(user.role),
    );

    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };

    return (
        <div className="flex min-h-screen flex-col bg-[#fff8ef]">
            {/* Header — mesma linguagem visual do ClientLayout (gradiente escuro) */}
            <header
                className="sticky top-0 z-30"
                style={{
                    background: "linear-gradient(160deg, #3D1A00 0%, #7C3A10 100%)",
                    boxShadow: "0 4px 20px rgba(26,10,0,0.18)",
                }}
            >
                <div className="mx-auto flex w-full max-w-5xl items-center gap-3 px-4 py-3 sm:px-6">
                    <div className="min-w-0 flex-1">
                        <p className="truncate text-[11px] font-bold uppercase tracking-widest text-amber-200/60">
                            DevDelivery
                        </p>
                        <p
                            className="truncate text-base font-bold leading-tight text-white sm:text-lg"
                            style={{ fontFamily: "Fraunces, serif" }}
                        >
                            {getPageLabel(location.pathname)}
                        </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-2 sm:gap-3">
                        <Clock className="hidden sm:inline-flex" />

                        <span className="rounded-lg border border-white/15 bg-white/10 px-2 py-1 text-[10px] font-bold text-amber-100 sm:px-3 sm:text-xs">
                            {ROLE_LABELS[user.role]}
                        </span>

                        <span className="hidden max-w-28 truncate text-sm font-semibold text-white/90 md:inline-block">
                            {user.nome}
                        </span>

                        <button
                            type="button"
                            onClick={handleLogout}
                            title="Sair"
                            aria-label="Sair"
                            className="shrink-0 rounded-lg p-2 text-amber-200/70 transition-colors hover:bg-white/10 hover:text-white"
                        >
                            <LogOut size={17} strokeWidth={1.8} />
                        </button>
                    </div>
                </div>
            </header>

            {/* Conteúdo — pb reserva espaço para a barra inferior fixa, em qualquer largura */}
            <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-5 pb-24 sm:px-6">
                <Outlet />
            </main>

            {/* Barra de navegação inferior — igual ao ClientLayout, em todas as breakpoints */}
            <nav
                className="fixed inset-x-0 bottom-0 z-40 border-t border-[#e8d5c4] bg-white"
                style={{ boxShadow: "0 -4px 20px rgba(0,0,0,0.06)" }}
            >
                <div className="mx-auto flex w-full max-w-5xl items-stretch">
                    {visibleNavItems.map((item) => {
                        const Icon = item.icon;
                        const active = isNavItemActive(item.path, location.pathname);

                        return (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                end={item.path === "/admin"}
                                className="flex flex-1 flex-col items-center gap-0.5 py-2.5"
                            >
                                <Icon
                                    size={20}
                                    strokeWidth={active ? 2.2 : 1.8}
                                    color={active ? "#F97316" : "#b0967e"}
                                />
                                <span
                                    className={[
                                        "text-center text-[10px] font-bold leading-tight sm:text-xs",
                                        active ? "text-[#F97316]" : "text-[#b0967e]",
                                    ].join(" ")}
                                >
                                    {item.shortLabel ?? item.label}
                                </span>
                            </NavLink>
                        );
                    })}
                </div>
            </nav>
        </div>
    );
}

function getPageLabel(pathname: string): string {
    if (pathname === "/admin") return "Visão geral";
    if (pathname.startsWith("/admin/cardapio")) return "Cardápio";
    if (pathname.startsWith("/admin/pedidos")) return "Pedidos";
    if (pathname.startsWith("/admin/relatorios")) return "Relatórios";
    if (pathname.startsWith("/admin/fechamento-caixa")) return "Fechamento de caixa";
    return "Visão geral";
}

function Clock({ className = "" }: { className?: string }) {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const id = setInterval(() => setTime(new Date()), 30_000);
        return () => clearInterval(id);
    }, []);

    return (
        <span className={`text-sm font-semibold tabular-nums text-amber-100/80 ${className}`}>
            {time.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </span>
    );
}