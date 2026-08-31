import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { AdminOverviewPage } from "../features/auth/pages/AdminOverviewPage";
import { CardapioPage } from "../features/cardapio/pages/CardapioPage";
import { PedidosPage } from "../features/pedido/pages/PedidosPage";
import { RelatoriosPage } from "../features/relatorio/pages/RelatoriosPage";
import { FechamentoCaixaPage } from "../features/fechamento_caixa/pages/FechamentoCaixaPage";
import { AdminLayout } from "../shared/layout/admin/AdminLayout";
function App() {
    return (_jsx(BrowserRouter, { children: _jsxs(Routes, { children: [_jsx(Route, { path: "/login", element: _jsx(LoginPage, {}) }), _jsxs(Route, { path: "/admin", element: _jsx(AdminLayout, {}), children: [_jsx(Route, { index: true, element: _jsx(AdminOverviewPage, {}) }), _jsx(Route, { path: "cardapio", element: _jsx(CardapioPage, {}) }), _jsx(Route, { path: "pedidos", element: _jsx(PedidosPage, {}) }), _jsx(Route, { path: "relatorios", element: _jsx(RelatoriosPage, {}) }), _jsx(Route, { path: "fechamento-caixa", element: _jsx(FechamentoCaixaPage, {}) })] }), _jsx(Route, { path: "/", element: _jsx(Navigate, { to: "/admin", replace: true }) }), _jsx(Route, { path: "*", element: _jsx(Navigate, { to: "/admin", replace: true }) })] }) }));
}
export default App;
