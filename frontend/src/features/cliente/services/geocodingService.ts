const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

export interface Coordenadas {
    latitude: number;
    longitude: number;
}

interface BuscarCoordenadasParams {
    street: string;
    city: string;
    state: string;
    neighborhood?: string;
    postalCode?: string;
    country?: string;
}

export async function buscarCoordenadasPorEndereco({
    street,
    city,
    state,
    neighborhood,
    postalCode,
    country = "Brasil",
}: BuscarCoordenadasParams): Promise<Coordenadas | null> {
    const endereco = [
        street,
        neighborhood,
        city,
        state,
        postalCode,
        country,
    ]
        .filter(Boolean)
        .join(", ");

    const params = new URLSearchParams({
        q: endereco,
        format: "json",
        limit: "1",
        countrycodes: "br",
    });

    try {
        const res = await fetch(`${NOMINATIM_URL}?${params.toString()}`, {
            headers: {
                "Accept-Language": "pt-BR",
            },
        });

        if (!res.ok) {
            return null;
        }

        const data = await res.json();

        if (!Array.isArray(data) || data.length === 0) {
            return null;
        }

        const latitude = Number(data[0].lat);
        const longitude = Number(data[0].lon);

        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
            return null;
        }

        return {
            latitude,
            longitude,
        };
    } catch {
        return null;
    }
}