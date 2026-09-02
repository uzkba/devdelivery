import {
    createContext,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";

export interface ClienteAuth {
    id: string;
    nome: string;
    telefone: string;
    ativo: boolean;
}

interface ClienteAuthContextData {
    cliente: ClienteAuth | null;
    isAuthenticated: boolean;
    login: () => void;
    logout: () => void;
}

const MOCK_CLIENTE: ClienteAuth = {
    id: "cliente-001",
    nome: "Ana Souza",
    telefone: "(84) 99999-9999",
    ativo: true,
};

const ClienteAuthContext = createContext<ClienteAuthContextData | undefined>(
    undefined,
);

interface ClienteAuthProviderProps {
    children: ReactNode;
}

export function ClienteAuthProvider({
    children,
}: ClienteAuthProviderProps) {
    const [cliente, setCliente] = useState<ClienteAuth | null>(
        MOCK_CLIENTE,
    );

    const login = () => setCliente(MOCK_CLIENTE);
    const logout = () => setCliente(null);

    const value = useMemo(
        () => ({
            cliente,
            isAuthenticated: cliente !== null,
            login,
            logout,
        }),
        [cliente],
    );

    return (
        <ClienteAuthContext.Provider value={value}>
            {children}
        </ClienteAuthContext.Provider>
    );
}

export function useClienteAuth(): ClienteAuthContextData {
    const context = useContext(ClienteAuthContext);

    if (!context) {
        throw new Error(
            "useClienteAuth deve ser utilizado dentro de um ClienteAuthProvider",
        );
    }

    return context;
}