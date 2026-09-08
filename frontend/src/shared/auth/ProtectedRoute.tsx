import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./StaffAuthContext";

type UserRole = "admin" | "atendente" | "caixa" | "entregador" | "cliente";

interface ProtectedRouteProps {
  allowedRoles: UserRole[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    // Usuário autenticado, mas sem permissão pra essa área
    return <Navigate to="/nao-autorizado" replace />;
  }

  return <Outlet />;
}
