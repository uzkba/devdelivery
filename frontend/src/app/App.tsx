import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "../features/auth/pages/LoginPage";
import { AdminOverviewPage } from "../features/admin/pages/AdminOverviewPage";
import { CardapioPage } from "../features/cardapio/pages/CardapioPage";
import { PedidosPage } from "../features/pedido/pages/PedidosPage";
import { RelatoriosPage } from "../features/relatorio/pages/RelatoriosPage";
import { FechamentoCaixaPage } from "../features/fechamento_caixa/pages/FechamentoCaixaPage";
import { AdminLayout } from "../shared/layout/admin/AdminLayout";
import { RequireRole } from "../shared/layout/admin/RequireRole";
import { getRolesForPath } from "../shared/layout/admin/adminNavItems";
import { AuthProvider } from "../shared/auth/StaffAuthContext";

import { CardapioClientePage } from "../features/cliente/pages/CardapioClientePage";
import { MeusPedidosPage } from "../features/cliente/pages/MeusPedidosPage";
import { EnderecosPage } from "../features/cliente/pages/EnderecosPage";
import { ClientLayout } from "../shared/layout/cliente/ClientLayout";
import { RequireClienteAuth } from "../shared/layout/cliente/RequireClienteAuth";
import { ClienteAuthProvider } from "../shared/auth/ClienteAuthContext";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ClienteAuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<AdminOverviewPage />} />

              <Route
                path="cardapio"
                element={
                  <RequireRole roles={getRolesForPath("/admin/cardapio")}>
                    <CardapioPage />
                  </RequireRole>
                }
              />
              <Route
                path="pedidos"
                element={
                  <RequireRole roles={getRolesForPath("/admin/pedidos")}>
                    <PedidosPage />
                  </RequireRole>
                }
              />
              <Route
                path="relatorios"
                element={
                  <RequireRole roles={getRolesForPath("/admin/relatorios")}>
                    <RelatoriosPage />
                  </RequireRole>
                }
              />
              <Route
                path="fechamento-caixa"
                element={
                  <RequireRole
                    roles={getRolesForPath("/admin/fechamento-caixa")}
                  >
                    <FechamentoCaixaPage />
                  </RequireRole>
                }
              />
            </Route>

            <Route path="/" element={<ClientLayout />}>
              <Route
                index
                element={
                  <RequireClienteAuth>
                    <CardapioClientePage />
                  </RequireClienteAuth>
                }
              />
              <Route
                path="cardapio"
                element={
                  <RequireClienteAuth>
                    <CardapioClientePage />
                  </RequireClienteAuth>
                }
              />
              <Route
                path="pedidos"
                element={
                  <RequireClienteAuth>
                    <MeusPedidosPage />
                  </RequireClienteAuth>
                }
              />
              <Route
                path="enderecos"
                element={
                  <RequireClienteAuth>
                    <EnderecosPage />
                  </RequireClienteAuth>
                }
              />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ClienteAuthProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
