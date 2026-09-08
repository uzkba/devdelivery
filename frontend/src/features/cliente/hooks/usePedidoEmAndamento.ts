import { useEffect, useState } from "react";
import { clientApi } from "../../../shared/api/clientApi";
import { useClienteAuth } from "@/shared/auth/ClienteAuthContext";

interface OrderStatus {
    code: string;
    name: string;
    is_final: boolean;
}

interface OrderListItem {
    id: string;
    numero_pedido: number;
    status: OrderStatus;
    data_hora: string;
    valor_total: number;
}

interface PaginatedOrders {
    items: OrderListItem[];
    total: number;
}

export function usePedidoEmAndamento() {
    const { isAuthenticated } = useClienteAuth();
    const [pedido, setPedido] = useState<OrderListItem | null>(null);

    useEffect(() => {
        if (!isAuthenticated) {
            setPedido(null);
            return;
        }

        let ativo = true;

        const buscar = () => {
            clientApi
                .get<PaginatedOrders>("/pedidos/me", {
                    params: { page: 1, page_size: 5 },
                })
                .then((res) => {
                    if (!ativo) return;
                    const emAndamento = res.data.items.find(
                        (p) => !p.status.is_final,
                    );
                    setPedido(emAndamento ?? null);
                })
                .catch(() => {
                    if (ativo) setPedido(null);
                });
        };

        buscar();
        const intervalo = setInterval(buscar, 30000);

        return () => {
            ativo = false;
            clearInterval(intervalo);
        };
    }, [isAuthenticated]);

    return pedido;
}
