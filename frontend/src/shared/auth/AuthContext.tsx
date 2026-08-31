import {
    createContext,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";

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
    login: () => void;
    logout: () => void;
}

const MOCK_USER: AuthUser = {
    id: "admin-001",
    nome: "Marcos Ferreira",
    email: "marcos@devdelivery.com",
    role: "admin",
};

const AuthContext = createContext<AuthContextData | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<AuthUser | null>(MOCK_USER);

    const login = () => {
        setUser(MOCK_USER);
    };

    const logout = () => {
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