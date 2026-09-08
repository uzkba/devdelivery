import { useEffect, useState } from "react";
import { clientApi } from "../../../shared/api/clientApi";

interface RestauranteInfo {
    id: string;
    trade_name: string;
    phone: string;
    is_active: boolean;
}

export function useRestauranteInfo() {
    const [restaurante, setRestaurante] = useState<RestauranteInfo | null>(
        null,
    );
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let ativo = true;

        clientApi
            .get<RestauranteInfo>("/restaurante")
            .then((res) => {
                if (ativo) setRestaurante(res.data);
            })
            .catch(() => {
                // sem rota ainda / falhou → mantém null, header cai no fallback "DevDelivery"
            })
            .finally(() => {
                if (ativo) setLoading(false);
            });

        return () => {
            ativo = false;
        };
    }, []);

    return { restaurante, loading };
}
