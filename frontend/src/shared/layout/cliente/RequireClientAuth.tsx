import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useClienteAuth } from "../../auth/ClienteAuthContext";

interface RequireClientAuthProps {
    children: ReactNode;
}

export function RequireClientAuth({ children }: RequireClientAuthProps) {
    const { isAuthenticated } = useClienteAuth();

    if (!isAuthenticated) {
        return <Navigate to="/cliente/login" replace />;
    }

    return <>{children}</>;
}