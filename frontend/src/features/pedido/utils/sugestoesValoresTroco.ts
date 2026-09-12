// Sugere valores de "quanto o cliente vai pagar" pra calcular o troco, em vez
// de uma lista fixa (ex: [50, 100]) que não faz sentido pra qualquer total.
// Usa as cédulas mais comuns do dinheiro brasileiro e só sugere as que são
// maiores que o total do pedido.

const CEDULAS = [5, 10, 20, 50, 100, 200]

export function suggestChangeAmounts(total: number, quantidade = 2): number[] {
  const candidatos = CEDULAS.filter((cedula) => cedula > total)

  if (candidatos.length < quantidade) {
    let proximo = candidatos.length > 0
      ? candidatos[candidatos.length - 1]
      : Math.ceil(total / 50) * 50

    while (candidatos.length < quantidade) {
      proximo += 50
      candidatos.push(proximo)
    }
  }

  return candidatos.slice(0, quantidade)
}
