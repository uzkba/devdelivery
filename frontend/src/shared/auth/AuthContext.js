import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useMemo, useState, } from "react";
const MOCK_USER = {
    id: "admin-001",
    nome: "Marcos Ferreira",
    email: "marcos@devdelivery.com",
    role: "admin",
};
const AuthContext = createContext(undefined);
export function AuthProvider({ children }) {
    const [user, setUser] = useState(MOCK_USER);
    const login = () => {
        setUser(MOCK_USER);
    };
    const logout = () => {
        setUser(null);
    };
    const value = useMemo(() => ({
        user,
        isAuthenticated: user !== null,
        login,
        logout,
    }), [user]);
    return (_jsx(AuthContext.Provider, { value: value, children: children }));
}
export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth deve ser utilizado dentro de um AuthProvider");
    }
    return context;
}
