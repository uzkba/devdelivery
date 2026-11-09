from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    alimento_route,
    autenticacao_route,
    cardapio_route,
    cardapio_do_dia_route,
    categoria_alimento_route,
    cliente_route,
    combo_route,
    endereco_route,
    marmita_route,
    pedido_route,
    teste,
    fechamento_caixa_route,
    relatorio_route,
    admin_cardapio_route,
    restaurante_publico_route,
    restaurante_admin_route,
    disponibilidade_route,
    cardapio_publico_route,
)

app = FastAPI(
    title="DevDelivery API",  
    description="API do sistema de delivery multi-restaurante",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(autenticacao_route.router)
app.include_router(cliente_route.router)
app.include_router(teste.router)
app.include_router(endereco_route.me_router)
app.include_router(endereco_route.router)
app.include_router(categoria_alimento_route.router)
app.include_router(alimento_route.router)
app.include_router(cardapio_route.router)
app.include_router(cardapio_do_dia_route.router)
app.include_router(pedido_route.router)
app.include_router(fechamento_caixa_route.router)
app.include_router(relatorio_route.router)
app.include_router(admin_cardapio_route.router)
app.include_router(restaurante_publico_route.router)
app.include_router(restaurante_admin_route.router)
app.include_router(marmita_route.router)
app.include_router(combo_route.router)
app.include_router(cardapio_publico_route.router)

for _router in disponibilidade_route.routers:
    app.include_router(_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}