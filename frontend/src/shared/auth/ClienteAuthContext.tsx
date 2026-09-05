import {
    createContext,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import { clientTokenStorage } from "./tokenStorage";
import { decodeJwtPayload } from "../utils/jwt";

export interface ClienteAuth {
    id: string;
    nome: string;
    telefone: string;
    ativo: boolean;
}

interface ClienteTokenPayload {
    sub: string;
    type: "client";
    name?: string;
    phone?: string;
    is_active?: boolean;
    exp: number;
}

interface ClienteAuthContextData {
    cliente: ClienteAuth | null;
    isAuthenticated: boolean;
    login: (token: string, telefoneInformado?: string) => void; // 👈 assinatura nova
    logout: () => void;
}

const ClienteAuthContext = createContext<ClienteAuthContextData | undefined>(
    undefined,
);

function buildClienteFromToken(
    token: string,
    telefoneInformado?: string,
): ClienteAuth {
    const payload = decodeJwtPayload<ClienteTokenPayload>(token);
    return {
        id: payload.sub,
        nome: payload.name ?? "Cliente",
        telefone: payload.phone ?? telefoneInformado ?? "",
        ativo: payload.is_active ?? true,
    };
}

function getInitialCliente(): ClienteAuth | null {
    const token = clientTokenStorage.get();
    if (!token) return null;

    try {
        return buildClienteFromToken(token);
    } catch {
        clientTokenStorage.clear();
        return null;
    }
}

interface ClienteAuthProviderProps {
    children: ReactNode;
}

export function ClienteAuthProvider({ children }: ClienteAuthProviderProps) {
    const [cliente, setCliente] = useState<ClienteAuth | null>(getInitialCliente);

    const login = (token: string, telefoneInformado?: string) => {
        clientTokenStorage.set(token);
        setCliente(buildClienteFromToken(token, telefoneInformado));
    };

    const logout = () => {
        clientTokenStorage.clear();
        setCliente(null);
    };

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