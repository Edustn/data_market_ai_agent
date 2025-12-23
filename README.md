# Data Market AI Agent

O objetivo desse projeto é sair de uma única URL (ranking Valor 1000) e contar a história completa de cada empresa em um grafo. A ideia é que os agentes façam o trabalho pesado de pesquisa e interpretação, para que você possa enxergar o ecossistema corporativo de forma viva:
- Descobrir e enriquecer informações básicas e de presença digital (site, LinkedIn, endereços, CNPJs, descrição) sem preenchimento manual.
- Mapear quem é quem: holdings, participações, marcas e subempresas (ex.: StoneCo → Stone, PagarMe, Ton, Linx), investidores e relações de capital.
- Classificar produtos/serviços mesmo com termos diferentes (gateway, adquirência, orquestração) e agrupar ofertas similares.
- Preencher o grafo (Neo4j por padrão) com nós e relações que revelem conexões, correlações e insights de grupo econômico.

Arquitetura inicial em MVC + agentes para orquestrar coleta, enriquecimento e escrita em Graph Database, partindo exclusivamente da URL base do ranking Valor 1000.

## Estrutura de pastas
- `src/app.py`: ponto de entrada orquestrador (CLI).
- `src/controllers/`: camada de coordenação das ações de scraping, enriquecimento e escrita no grafo.
- `src/models/`: modelos de domínio (Company, Brand, Relationship).
- `src/views/`: interface CLI para logs/saídas.
- `src/services/scraping/`: scrapers focados na URL fornecida.
- `src/services/enrichment/`: agentes/serviços LLM para interpretação e enriquecimento.
- `src/services/graph/`: cliente e builder do Graph DB (Neo4j por padrão, mas pode trocar).
- `src/agents/`: agentes orquestradores e tarefas especializadas.
- `src/data/raw/` e `src/data/processed/`: armazenamento transitório de dados coletados.

## Fluxo proposto (alto nível)
1) **Scraping**: `Valor1000Scraper` extrai a lista de empresas e metadados iniciais (nome, setor, receita) a partir da URL. Seleciona linhas `<tr class="odd">` e `<tr class="even">`; nome em `td.click-control`; setor na célula com `style="text-align: left;"`; receita no primeiro `<td>` numérico visível após o setor (ignora colunas de ranking e `display: none`).
2) **Enriquecimento**: agentes chamam ferramentas de busca/LLM para obter site, LinkedIn, endereços, CNPJs, marcas e descrições, normalizando produtos/serviços.
3) **Inferência societária**: agente de raciocínio cruza CNPJs, holdings e marcas para inferir grupos econômicos e relações (OWNS, SUBSIDIARY_OF, OPERATES_AS).
4) **Persistência em grafo**: `GraphBuilder` cria/mantém nodes e edges no Neo4j (ou banco equivalente) mantendo versionamento básico e atributos de confiança.
5) **Consultas/demonstração**: camada de view expõe consultas exemplo (clusters de similaridade, mapa societário, marcas por holding).

## Decisões iniciais
- **MVC + agentes**: Controllers orquestram a pipeline; Services executam scraping, enriquecimento e gravação; Agents encapsulam lógica LLM e tomada de decisão.
- **Agno opcional**: Orquestrador de agentes pode usar o framework Agno (se instalado) com modelo OpenAI; se indisponível, cai para enriquecimento simples via LLM.
- **Graph-first**: modelagem pensada para Neo4j, mas interfaces isolam dependência para permitir trocar por Neptune/Arango.
- **Escalabilidade**: separação por etapas permite rodar em batches (100/1k/10k), paralelizar scraping/enriquecimento e reaproveitar cache em `data/processed`.

## Modelagem de grafo sugerida (ajustável)
- Nodes: `Company`, `Brand`, `Holding`, `Person` (quando sócios aparecerem), `ProductCategory`.
- Edges: `OWNS`, `SUBSIDIARY_OF`, `OPERATES_AS`, `INVESTOR_IN`, `SIMILAR_TO`, `OFFERS`.
- Propriedades mínimas: `name`, `cnpj`, `website`, `linkedin`, `address`, `confidence`, `source`, `last_seen`.

## Como rodar
Pré-requisitos: Python 3.10+, Neo4j acessível (local ou remoto), `.env` preenchido.
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Exemplo: processar 50 empresas, usando cache e credenciais do .env
python src/app.py --limit 50

# Override de Neo4j via CLI (prioridade sobre .env)
python src/app.py --limit 50 --neo4j-uri=bolt://localhost:7687 --neo4j-user=neo4j --neo4j-password=senha

# Desabilitar cache de HTML
python src/app.py --limit 50 --no-cache
```
O comando executa: scraping da URL oficial, enriquecimento (LLM + busca) e escrita no Neo4j.

### Cache de scraping
- O `Valor1000Scraper` usa cache opcional em `src/data/raw/valor1000.html`.
- Se o arquivo existir, ele é lido; se não existir, a URL é baixada e salva (se `use_cache=True`, default).
- Para desabilitar o cache via CLI, use `--no-cache`.

### Ambiente (.env)
- Copie `.env.example` para `.env` e preencha:
  - `OPENAI_API_KEY`
  - `NEO4J_URI` (ex.: `bolt://localhost:7687`)
  - `NEO4J_USER`, `NEO4J_PASSWORD`
  - `TAVILY_API_KEY` (opcional; SearchAgent tenta Tavily, senão usa fallback DuckDuckGo sem credenciais)
  - Ajuste outros parâmetros conforme necessário.

### Configurar LLM (OpenAI)
- Defina `OPENAI_API_KEY` no ambiente.
- O `LlmEnricher` usa `gpt-4.1-mini` (ajuste no código se quiser outro modelo).
- Se `OPENAI_API_KEY` não estiver setado, o agente devolve os dados originais (sem enriquecimento).

### Usar Agno (orquestração de agentes)
- Instale dependência `agno` (já listada em `requirements.txt`).
- Se Agno estiver disponível e `OPENAI_API_KEY` setado, o `OrchestratorAgent` usará o agente Agno; caso contrário, faz fallback para o caminho simples.
