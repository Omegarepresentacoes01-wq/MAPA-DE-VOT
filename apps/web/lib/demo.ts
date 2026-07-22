export type DemoSearchResult = {
  id: string;
  tipo: "candidato" | "municipio" | "partido";
  titulo: string;
  subtitulo?: string;
  uf?: string;
  partido_sigla?: string;
  situacao?: string;
};

// A demonstração é o padrão para permitir avaliação visual sem Docker/serviços.
// Defina NEXT_PUBLIC_DEMO_MODE=false (e DEMO_MODE=false no servidor) para usar a API real.
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

export const DEMO_SEARCH_RESULTS: DemoSearchResult[] = [
  { id: "demo-candidata-1", tipo: "candidato", titulo: "Marina Alves", subtitulo: "PSB · Deputada Federal", uf: "SP", partido_sigla: "PSB", situacao: "ELEITO" },
  { id: "demo-candidato-2", tipo: "candidato", titulo: "Rafael Nogueira", subtitulo: "PT · Deputado Estadual", uf: "SP", partido_sigla: "PT", situacao: "SUPLENTE" },
  { id: "municipio_3550308", tipo: "municipio", titulo: "São Paulo", subtitulo: "São Paulo", uf: "SP" },
  { id: "municipio_3304557", tipo: "municipio", titulo: "Rio de Janeiro", subtitulo: "Rio de Janeiro", uf: "RJ" },
  { id: "partido_psb", tipo: "partido", titulo: "PSB", subtitulo: "Partido Socialista Brasileiro", partido_sigla: "PSB" },
];

export function demoSearch(query: string, tipo?: string) {
  const normalized = query.trim().toLocaleLowerCase("pt-BR");
  const matches = DEMO_SEARCH_RESULTS.filter((item) => {
    const searchable = `${item.titulo} ${item.subtitulo || ""} ${item.uf || ""} ${item.partido_sigla || ""}`.toLocaleLowerCase("pt-BR");
    return (!tipo || item.tipo === tipo) && (searchable.includes(normalized) || normalized.length < 2);
  });
  return matches.length ? matches : DEMO_SEARCH_RESULTS.filter((item) => !tipo || item.tipo === tipo);
}

export const DEMO_CANDIDATE = {
  candidatura: {
    nome: "Marina Alves de Souza",
    nome_urna: "Marina Alves",
    nascimento: "1982-04-18",
    genero: "Feminino",
    raca_cor: "Parda",
    escolaridade: "Superior completo",
    ocupacao: "Advogada",
    partido_sigla: "PSB",
    cargo_descricao: "Deputada Federal",
    territorio_nome: "São Paulo",
    territorio_uf: "SP",
    numero_urna: "40123",
    situacao: "ELEITO",
    bens_declarados: 485000,
    votos_totais: 126840,
  },
  historico_eleitoral: [
    { eleicao: "2018 T1", cargo: "Deputada Estadual", partido: "PSB", situacao: "ELEITO" },
    { eleicao: "2016 T1", cargo: "Vereadora", partido: "PSB", situacao: "ELEITO" },
  ],
  financas: {
    total_receitas: 720000,
    total_despesas: 693450,
    receitas_por_origem: [
      { origem: "Fundo Eleitoral", total: 460000 },
      { origem: "Doações de pessoas físicas", total: 180000 },
      { origem: "Recursos próprios", total: 80000 },
    ],
    despesas_por_categoria: [
      { categoria: "Publicidade", total: 290000 },
      { categoria: "Pessoal", total: 185000 },
      { categoria: "Serviços", total: 142450 },
      { categoria: "Transporte", total: 76000 },
    ],
  },
  votos_por_municipio: [
    { nome: "São Paulo", codigo_ibge: "3550308", votos: 72400 },
    { nome: "Guarulhos", codigo_ibge: "3518800", votos: 16820 },
    { nome: "Osasco", codigo_ibge: "3534401", votos: 12170 },
    { nome: "Santo André", codigo_ibge: "3547809", votos: 9350 },
  ],
  meta: { fonte: "Demonstração local — estrutura baseada em dados TSE", url: "https://dadosabertos.tse.jus.br" },
};

export const DEMO_COMPARISON_ROWS = [
  { territory_nome: "PSB — São Paulo", votos_a: 82210, votos_b: 100540, variacao_absoluta: 18330, variacao_percentual: 22.3 },
  { territory_nome: "PT — São Paulo", votos_a: 121400, votos_b: 132180, variacao_absoluta: 10780, variacao_percentual: 8.9 },
  { territory_nome: "PSD — São Paulo", votos_a: 68450, votos_b: 59120, variacao_absoluta: -9330, variacao_percentual: -13.6 },
  { territory_nome: "PSOL — São Paulo", votos_a: 48400, votos_b: 56270, variacao_absoluta: 7870, variacao_percentual: 16.3 },
];

export const DEMO_MUNICIPALITIES: Record<string, { nome: string; uf: string; populacao: number; votos_validos: number }> = {
  "3550308": { nome: "São Paulo", uf: "SP", populacao: 11451999, votos_validos: 6582400 },
  "3518800": { nome: "Guarulhos", uf: "SP", populacao: 1296687, votos_validos: 703120 },
  "3534401": { nome: "Osasco", uf: "SP", populacao: 728615, votos_validos: 403670 },
  "3547809": { nome: "Santo André", uf: "SP", populacao: 748919, votos_validos: 434200 },
};

export type StrategyPriority = "alta" | "media" | "manutencao";

export const DEMO_STRATEGY_2026 = [
  { codigo: "3550308", municipio: "São Paulo", uf: "SP", prioridade: "alta" as StrategyPriority, votos2022: 72400, votos2024: 84350, variacao: 16.5, potencial: 112000, meta: 93000, status: "Planejar agenda" },
  { codigo: "3518800", municipio: "Guarulhos", uf: "SP", prioridade: "alta" as StrategyPriority, votos2022: 16820, votos2024: 22310, variacao: 32.6, potencial: 31000, meta: 25500, status: "Ampliar presença" },
  { codigo: "3534401", municipio: "Osasco", uf: "SP", prioridade: "alta" as StrategyPriority, votos2022: 12170, votos2024: 10980, variacao: -9.8, potencial: 19000, meta: 14500, status: "Recuperar base" },
  { codigo: "3547809", municipio: "Santo André", uf: "SP", prioridade: "media" as StrategyPriority, votos2022: 9350, votos2024: 10920, variacao: 16.8, potencial: 14500, meta: 12000, status: "Consolidar" },
  { codigo: "3304557", municipio: "Rio de Janeiro", uf: "RJ", prioridade: "media" as StrategyPriority, votos2022: 18750, votos2024: 16200, variacao: -13.6, potencial: 26000, meta: 20500, status: "Diagnosticar queda" },
];
