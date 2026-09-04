import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth, type UserRole } from "../../auth/StaffAuthContext";

interface RequireRoleProps {
  roles: UserRole[];
  children: ReactNode;
}

/**
 * Guard de rota: complementa a filtragem do menu (que só esconde o item).
 * Sem isso, um usuário sem permissão ainda acessava a página digitando a URL.
 */
export function RequireRole({ roles, children }: RequireRoleProps) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(user.role)) {
    return <Navigate to="/admin" replace />;
  }

  return <>{children}</>;
}
