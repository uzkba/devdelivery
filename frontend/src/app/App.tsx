import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AdminOverviewPage } from "@/features/admin/pages/AdminOverviewPage";
import { PedidosPage } from "@/features/pedido/pages/PedidosPage";
import { RelatoriosPage } from "@/features/relatorio/pages/RelatoriosPage";
import { FechamentoCaixaPage } from "@/features/fechamento_caixa/pages/FechamentoCaixaPage";
import { AdminLayout } from "@/shared/layout/admin/AdminLayout";
import { RequireRole } from "@/shared/layout/admin/RequireRole";
import { getRolesForPath } from "@/shared/layout/admin/adminNavItems";
import { AuthProvider } from "@/shared/auth/StaffAuthContext";
import { MeusPedidosPage } from "@/features/cliente/pages/MeusPedidosPage";
import ClientLayout from "@/shared/layout/cliente/ClientLayout";
import { ClienteAuthProvider } from "../shared/auth/ClienteAuthContext";
import StaffLoginPage from "@/features/auth/pages/StaffLoginPage";
import { RequireClientAuth } from "@/shared/layout/cliente/RequireClientAuth";
import ClientLoginPage from "@/features/cliente/pages/LoginClientePage";
import ClientRegisterPage from "@/features/cliente/pages/CadastroClientePage";
import { MinhaContaPage } from "@/features/cliente/pages/MinhaContaPage";
import { InicioPage } from "@/features/cliente/pages/InicioPage";
import EnderecosPage from "@/features/cliente/pages/EnderecosPage";
import PagamentoPage from "@/features/pedido/pages/PagamentoPage";
import PixPage from "@/features/pedido/pages/PixPage";
import CartaoPage from "@/features/pedido/pages/CartaoPage";
import DinheiroPage from "@/features/pedido/pages/DinheiroPage";
import { CardapioPage } from "@/features/cardapio/pages/CardapioPage";
import CardapioClientePage from "@/features/cliente/pages/CardapioClientePage";

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <ClienteAuthProvider>
                    <Routes>
                        <Route path="/login" element={<StaffLoginPage />} />

                        <Route path="/cliente/registrar" element={<ClientRegisterPage />} />

                        <Route path="/cliente/login" element={<ClientLoginPage />} />

                        <Route path="/admin" element={<AdminLayout />}>
                            <Route index element={<AdminOverviewPage />} />

                            <Route
                                path="cardapio"
                                element={
                                    <RequireRole
                                        roles={getRolesForPath(
                                            "/admin/cardapio",
                                        )}
                                    >
                                        <CardapioPage />
                                    </RequireRole>
                                }
                            />
                            <Route
                                path="pedidos"
                                element={
                                    <RequireRole
                                        roles={getRolesForPath(
                                            "/admin/pedidos",
                                        )}
                                    >
                                        <PedidosPage />
                                    </RequireRole>
                                }
                            />
                            <Route
                                path="relatorios"
                                element={
                                    <RequireRole
                                        roles={getRolesForPath(
                                            "/admin/relatorios",
                                        )}
                                    >
                                        <RelatoriosPage />
                                    </RequireRole>
                                }
                            />
                            <Route
                                path="fechamento-caixa"
                                element={
                                    <RequireRole
                                        roles={getRolesForPath(
                                            "/admin/fechamento-caixa",
                                        )}
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
                                    <RequireClientAuth>
                                        <InicioPage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="cardapio"
                                element={
                                    <RequireClientAuth>
                                        <CardapioClientePage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="pedidos"
                                element={
                                    <RequireClientAuth>
                                        <MeusPedidosPage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="conta"
                                element={
                                    <RequireClientAuth>
                                        <MinhaContaPage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="enderecos"
                                element={
                                    <RequireClientAuth>
                                        <EnderecosPage />
                                    </RequireClientAuth>
                                }
                            />

                            {/* Fluxo de checkout - pagamento (issue: Formulário de Forma de Pagamento) */}
                            <Route
                                path="pedido/pagamento"
                                element={
                                    <RequireClientAuth>
                                        <PagamentoPage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="pedido/pagamento/pix"
                                element={
                                    <RequireClientAuth>
                                        <PixPage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="pedido/pagamento/cartao"
                                element={
                                    <RequireClientAuth>
                                        <CartaoPage />
                                    </RequireClientAuth>
                                }
                            />
                            <Route
                                path="pedido/pagamento/dinheiro"
                                element={
                                    <RequireClientAuth>
                                        <DinheiroPage />
                                    </RequireClientAuth>
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
