import {
    createContext,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import { adminTokenStorage } from "./tokenStorage";
import { decodeJwtPayload } from "../utils/jwt";

export type UserRole = "admin" | "atendente" | "caixa" | "entregador";

export interface AuthUser {
    id: string;
    nome: string;
    email: string;
    role: UserRole;
}

interface AuthContextData {
    user: AuthUser | null;
    isAuthenticated: boolean;
    login: (token: string) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextData | undefined>(undefined);

function buildUserFromToken(token: string): AuthUser {
    const payload = decodeJwtPayload(token);
    return {
        id: payload.sub,
        nome: payload.name,
        email: payload.login,
        role: payload.role,
    };
}

function getInitialUser(): AuthUser | null {
    const token = adminTokenStorage.get();
    if (!token) return null;

    try {
        return buildUserFromToken(token);
    } catch {
        adminTokenStorage.clear();
        return null;
    }
}

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<AuthUser | null>(getInitialUser);

    const login = (token: string) => {
        adminTokenStorage.set(token);
        setUser(buildUserFromToken(token));
    };

    const logout = () => {
        adminTokenStorage.clear();
        setUser(null);
    };

    const value = useMemo(
        () => ({
            user,
            isAuthenticated: user !== null,
            login,
            logout,
        }),
        [user],
    );

    return (
        <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    );
}

export function useAuth(): AuthContextData {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error("useAuth deve ser utilizado dentro de um AuthProvider");
    }

    return context;
}