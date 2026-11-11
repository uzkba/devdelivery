from pydantic import BaseModel, field_validator


class FormaPagamentoAdminOut(BaseModel):
    codigo: str
    nome: str
    aceita: bool


class FormasPagamentoIn(BaseModel):
    aceitas: list[str]

    @field_validator("aceitas")
    @classmethod
    def _validar_codigos(cls, valor: list[str]) -> list[str]:
        codigos = [codigo.strip().upper() for codigo in valor]
        if not codigos:
            raise ValueError("Aceite ao menos uma forma de pagamento (Pix, cartão ou dinheiro).")
        if any(not codigo for codigo in codigos):
            raise ValueError("Código de forma de pagamento vazio.")
        if len(set(codigos)) != len(codigos):
            raise ValueError("Forma de pagamento repetida.")
        return codigos