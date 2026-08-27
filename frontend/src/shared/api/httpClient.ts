// Alias de compatibilidade: código antigo (ex.: cardapio.api.ts) importa "httpClient".
// Como as rotas de cardápio usadas hoje são de admin, apontamos para adminApi.
// Ideal: migrar os imports para `adminApi` diretamente e remover este arquivo depois.
export { adminApi as httpClient } from "./adminApi";