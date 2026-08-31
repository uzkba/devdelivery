import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../shared/auth/AuthContext";
export function LoginPage() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const handleLogin = () => {
        login();
        navigate("/admin", { replace: true });
    };
    return (_jsx("main", { className: "flex min-h-screen items-center justify-center bg-[#fffaf4] p-6", children: _jsxs("section", { className: "w-full max-w-md rounded-2xl border border-[#ead8c5] bg-white p-8 shadow-sm", children: [_jsx("p", { className: "text-xs font-bold tracking-wide text-[#d49b32]", children: "DEVDELIVERY" }), _jsx("h1", { className: "mt-2 font-serif text-3xl font-bold text-[#21170f]", children: "Acesso administrativo" }), _jsx("p", { className: "mt-2 text-sm text-[#806a57]", children: "Entre para acessar o painel do restaurante." }), _jsx("button", { type: "button", onClick: handleLogin, className: "mt-6 w-full rounded-xl bg-[#ff7315] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#e9650d]", children: "Entrar" })] }) }));
}
