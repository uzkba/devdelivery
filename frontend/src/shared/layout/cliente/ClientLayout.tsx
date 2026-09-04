import { Link, Outlet } from "react-router-dom";
import { useClienteAuth } from "../../auth/ClienteAuthContext";

export function ClientLayout() {
    const { cliente, logout } = useClienteAuth();

    return (
        <div className="min-h-screen flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 border-b">
                <span className="font-semibold">DevDelivery</span>
                <nav className="flex gap-4 text-sm">
                    <Link to="/cardapio">Cardápio</Link>
                    <Link to="/pedidos">Meus Pedidos</Link>
                    <Link to="/enderecos">Endereços</Link>
                </nav>
                <div className="flex items-center gap-2">
                    <span>{cliente?.nome}</span>
                    <button onClick={logout}>Sair</button>
                </div>
            </header>
            <main className="flex-1 p-4">
                <Outlet />
            </main>
        </div>
    );
}