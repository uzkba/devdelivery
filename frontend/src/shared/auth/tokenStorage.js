const ADMIN_TOKEN_KEY = "devdelivery:admin_token";
const CLIENT_TOKEN_KEY = "devdelivery:client_token";
function createTokenStorage(key) {
    return {
        get: () => localStorage.getItem(key),
        set: (token) => localStorage.setItem(key, token),
        clear: () => localStorage.removeItem(key),
    };
}
export const adminTokenStorage = createTokenStorage(ADMIN_TOKEN_KEY);
export const clientTokenStorage = createTokenStorage(CLIENT_TOKEN_KEY);
