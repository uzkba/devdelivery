import { Outlet, useNavigate, useLocation, NavLink } from "react-router-dom";
import { ArrowLeft, Home, BookOpen, ClipboardList, User } from "lucide-react";
import { useRestauranteInfo } from "../../../features/cliente/hooks/useRestauranteInfo";
import { usePedidoEmAndamento } from "../../../features/cliente/hooks/usePedidoEmAndamento";

const TITLES: Record<string, string> = {
    "/": "Seu prato, do seu jeito!",
    "/cardapio": "Monte sua marmita",
    "/pedido/endereco": "Endereço de entrega",
    "/pedido/pagamento": "Pagamento",
    "/pedido/pagamento/pix": "Pagamento via PIX",
    "/pedido/pagamento/cartao": "Pagamento com cartão",
    "/pedido/pagamento/dinheiro": "Pagamento em dinheiro",
    "/pedido/revisao": "Revisar pedido",
    "/pedido/confirmado": "Pedido confirmado",
    "/pedidos": "Meus pedidos",
    "/conta": "Minha conta",
    "/conta/enderecos": "Meus endereços",
    "/conta/login": "Entrar",
};

const BACK_TARGETS: Record<string, string> = {
    "/cardapio": "/",
    "/pedido/endereco": "/cardapio",
    "/pedido/pagamento": "/pedido/endereco",
    "/pedido/pagamento/pix": "/pedido/pagamento",
    "/pedido/pagamento/cartao": "/pedido/pagamento",
    "/pedido/pagamento/dinheiro": "/pedido/pagamento",
    "/pedido/revisao": "/pedido/pagamento",
    "/conta/enderecos": "/conta",
    "/conta/login": "/conta",
};

const CHECKOUT_PATHS = [
    "/pedido/endereco",
    "/pedido/pagamento",
    "/pedido/pagamento/pix",
    "/pedido/pagamento/cartao",
    "/pedido/pagamento/dinheiro",
    "/pedido/revisao",
];

const CHECKOUT_STEPS = [
    {
        path: "/pedido/endereco",
        label: "Endereço",
        matches: (p: string) => p === "/pedido/endereco",
    },
    {
        path: "/pedido/pagamento",
        label: "Pagamento",
        matches: (p: string) => p.startsWith("/pedido/pagamento"),
    },
    {
        path: "/pedido/revisao",
        label: "Revisão",
        matches: (p: string) => p === "/pedido/revisao",
    },
];

const NO_BOTTOM_NAV = new Set([
    "/pedido/endereco",
    "/pedido/pagamento",
    "/pedido/pagamento/pix",
    "/pedido/pagamento/cartao",
    "/pedido/pagamento/dinheiro",
    "/pedido/revisao",
    "/pedido/confirmado",
    "/conta/login",
]);

const NAV_ITEMS = [
    { to: "/", icon: Home, label: "Início", exact: true },
    { to: "/cardapio", icon: BookOpen, label: "Cardápio", exact: false },
    { to: "/pedidos", icon: ClipboardList, label: "Pedidos", exact: false },
    { to: "/conta", icon: User, label: "Conta", exact: false },
];

function getTitle(path: string) {
    if (TITLES[path]) return TITLES[path];
    if (/^\/pedidos\//.test(path)) return "Acompanhar pedido";
    return "DevDelivery";
}

function getBack(path: string): string | undefined {
    if (BACK_TARGETS[path]) return BACK_TARGETS[path];
    if (/^\/pedidos\//.test(path)) return "/pedidos";
    return undefined;
}

export default function ClientLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const { restaurante } = useRestauranteInfo();
    const pedidoEmAndamento = usePedidoEmAndamento();

    const path = location.pathname;
    const title = getTitle(path);
    const backTarget = getBack(path);

    const isRoot = path === "/";
    const isConfirmed = path === "/pedido/confirmado";
    const isCheckout = CHECKOUT_PATHS.includes(path);

    const showBottomNav =
        !NO_BOTTOM_NAV.has(path) && !/^\/pedidos\/.+/.test(path);

    return (
        <div
            className="min-h-screen flex flex-col"
            style={{ background: "#FFF8EF", color: "#3D1A00" }}
        >
            {/* HEADER */}
            <header
                className="sticky top-0 z-30"
                style={{
                    background: "#4A2105",
                    boxShadow: "0 2px 12px rgba(61, 26, 0, 0.12)",
                }}
            >
                <div className="max-w-lg mx-auto px-4">
                    <div
                        className="grid items-center min-h-17"
                        style={{ gridTemplateColumns: "1fr auto 1fr" }}
                    >
                        <div className="flex justify-start">
                            {backTarget && !isConfirmed && (
                                <button
                                    type="button"
                                    onClick={() => navigate(backTarget)}
                                    className="flex items-center gap-1.5 text-sm font-semibold text-amber-100/75 hover:text-white transition-colors"
                                >
                                    <ArrowLeft size={17} strokeWidth={2} />
                                    <span>Voltar</span>
                                </button>
                            )}
                        </div>

                        <div className="text-center px-3">
                            {isRoot && (
                                <p className="text-[10px] uppercase tracking-[0.18em] font-bold text-amber-200/65 mb-1">
                                    {restaurante?.trade_name ?? "DevDelivery"}
                                </p>
                            )}
                            <h1
                                className="text-white font-bold leading-tight whitespace-nowrap"
                                style={{
                                    fontFamily: "Fraunces, serif",
                                    fontSize: isRoot ? "1.25rem" : "1.1rem",
                                }}
                            >
                                {title}
                            </h1>
                        </div>

                        <div />
                    </div>

                    {isCheckout && <CheckoutSteps currentPath={path} />}
                </div>
            </header>

            {/* CONTEÚDO */}
            <main
                className="flex-1 w-full max-w-lg mx-auto px-4 pt-5 pb-8"
                style={{ paddingBottom: showBottomNav ? "6.5rem" : "2rem" }}
            >
                <Outlet />
            </main>

            {/* NAVEGAÇÃO */}
            {showBottomNav && (
                <nav
                    className="fixed bottom-0 left-0 right-0 z-40"
                    style={{
                        background: "rgba(255,255,255,0.98)",
                        borderTop: "1px solid #E8D5C4",
                        boxShadow: "0 -4px 18px rgba(61, 26, 0, 0.08)",
                    }}
                >
                    <div className="max-w-lg mx-auto flex items-center">
                        {NAV_ITEMS.map((item) => {
                            const Icon = item.icon;
                            const showBadge =
                                item.to === "/pedidos" && !!pedidoEmAndamento;

                            return (
                                <NavLink
                                    key={item.to}
                                    to={item.to}
                                    end={item.exact}
                                    className="flex-1"
                                >
                                    {({ isActive }) => (
                                        <div className="relative flex flex-col items-center justify-center min-h-16 gap-1 transition-all">
                                            <span
                                                className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full transition-all"
                                                style={{
                                                    background: isActive
                                                        ? "#F97316"
                                                        : "transparent",
                                                }}
                                            />
                                            <span
                                                className="relative transition-transform duration-200"
                                                style={{
                                                    color: isActive
                                                        ? "#F97316"
                                                        : "#B0967E",
                                                    transform: isActive
                                                        ? "translateY(-1px)"
                                                        : "translateY(0)",
                                                }}
                                            >
                                                <Icon
                                                    size={20}
                                                    strokeWidth={
                                                        isActive ? 2.3 : 1.8
                                                    }
                                                />
                                                {showBadge && (
                                                    <span
                                                        className="absolute -top-0.5 -right-1 w-2 h-2 rounded-full"
                                                        style={{
                                                            background:
                                                                "#F97316",
                                                            boxShadow:
                                                                "0 0 0 2px #fff",
                                                        }}
                                                    />
                                                )}
                                            </span>
                                            <span
                                                className="text-[11px] font-bold transition-colors"
                                                style={{
                                                    color: isActive
                                                        ? "#F97316"
                                                        : "#B0967E",
                                                }}
                                            >
                                                {item.label}
                                            </span>
                                        </div>
                                    )}
                                </NavLink>
                            );
                        })}
                    </div>
                </nav>
            )}
        </div>
    );
}

function CheckoutSteps({ currentPath }: { currentPath: string }) {
    const currentIdx = CHECKOUT_STEPS.findIndex((step) =>
        step.matches(currentPath),
    );

    return (
        <div className="flex items-start justify-center px-4 pb-4">
            {CHECKOUT_STEPS.map((step, idx) => {
                const done = idx < currentIdx;
                const active = idx === currentIdx;

                return (
                    <div key={step.path} className="flex items-start">
                        <div className="flex flex-col items-center min-w-16">
                            <div
                                className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold transition-all duration-300"
                                style={{
                                    background: done
                                        ? "#16A34A"
                                        : active
                                            ? "#F97316"
                                            : "rgba(255,255,255,0.12)",
                                    color:
                                        done || active
                                            ? "#fff"
                                            : "rgba(255,255,255,0.4)",
                                    boxShadow: active
                                        ? "0 0 0 3px rgba(249,115,22,0.15)"
                                        : "none",
                                }}
                            >
                                {done ? (
                                    <svg
                                        viewBox="0 0 24 24"
                                        className="w-3.5 h-3.5"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="3"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    >
                                        <path d="M20 6L9 17l-5-5" />
                                    </svg>
                                ) : (
                                    idx + 1
                                )}
                            </div>

                            <span
                                className="mt-1 text-[10px] font-semibold"
                                style={{
                                    color: active
                                        ? "#FDE68A"
                                        : done
                                            ? "#86EFAC"
                                            : "rgba(255,255,255,0.4)",
                                }}
                            >
                                {step.label}
                            </span>
                        </div>

                        {idx < CHECKOUT_STEPS.length - 1 && (
                            <div
                                className="w-12 h-px mt-3"
                                style={{
                                    background: done
                                        ? "#16A34A"
                                        : "rgba(255,255,255,0.14)",
                                }}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
