from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import (
    alimento_route,
    autenticacao_route,
    cardapio_route,
    cardapio_do_dia_route,
    categoria_alimento_route,
    cliente_route,
    endereco_route,
    pedido_route,
    auditoria_route,
    teste,
    fechamento_caixa_route,
    relatorio_route,
    admin_cardapio_route,
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
    allow_methods=[""],  
    allow_headers=[""], 
)

app.include_router(autenticacao_route.router)
app.include_router(cliente_route.router)
app.include_router(teste.router)
app.include_router(endereco_route.router)
app.include_router(categoria_alimento_route.router)
app.include_router(alimento_route.router)
app.include_router(cardapio_route.router)
app.include_router(cardapio_do_dia_route.router)
app.include_router(pedido_route.router)
app.include_router(fechamento_caixa_route.router)
app.include_router(relatorio_route.router)
app.include_router(auditoria_route.router)
app.include_router(admin_cardapio_route.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}