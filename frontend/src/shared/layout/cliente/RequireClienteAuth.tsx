import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useClienteAuth } from "../../auth/ClienteAuthContext";

interface RequireClienteAuthProps {
    children: ReactNode;
}

export function RequireClienteAuth({ children }: RequireClienteAuthProps) {
    const { isAuthenticated } = useClienteAuth();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return <>{children}</>;
}