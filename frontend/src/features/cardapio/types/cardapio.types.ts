export type ItemCardapio = {
  id: number;
  alimentoId: number;
  nome: string;
  categoria: string;
  disponivel: boolean;
  preco: number;
};

export type CardapioDoDia = {
  data: string;
  itens: ItemCardapio[];
};
