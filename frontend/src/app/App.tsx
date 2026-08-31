import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "../features/auth/pages/LoginPage";
import { AdminOverviewPage } from "../features/auth/pages/AdminOverviewPage";
import { CardapioPage } from "../features/cardapio/pages/CardapioPage";
import { PedidosPage } from "../features/pedido/pages/PedidosPage";
import { RelatoriosPage } from "../features/relatorio/pages/RelatoriosPage";
import { FechamentoCaixaPage } from "../features/fechamento_caixa/pages/FechamentoCaixaPage";
import { AdminLayout } from "../shared/layout/admin/AdminLayout";

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<LoginPage />} />

                <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<AdminOverviewPage />} />
                <Route path="cardapio" element={<CardapioPage />} />
                <Route path="pedidos" element={<PedidosPage />} />
                <Route path="relatorios" element={<RelatoriosPage />} />
                <Route
                    path="fechamento-caixa"
                    element={<FechamentoCaixaPage />}
                />
                </Route>

                <Route path="/" element={<Navigate to="/admin" replace />} />
                <Route path="*" element={<Navigate to="/admin" replace />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;