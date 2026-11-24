# Rota Vital — Serverless (`POST /guias`)

> **Atividade Individual 1 — Serverless**  
> **Disciplina:** Infraestrutura de Software · ADS · CESAR School · 2026.2  
> **Estudante:** Ricardo Severiano de Souza Filho ([@byteric](https://github.com/byteric))  
> **Caminho escolhido:** **Caminho A (AWS SAM CLI local com Docker Desktop e Python 3.12)**

Função serverless em Python 3.12 que gera a guia de transporte de uma requisição do **Rota Vital**, exposta via API Gateway Proxy (`POST /guias`), utilizada para observar na prática o ciclo de vida do ambiente de execução (*cold start* e reaproveitamento), a ausência de estado garantido em variáveis globais e o limite de tempo de execução (*timeout*).

---

## 📁 Estrutura do Repositório

```text
rota-vital-serverless/
├── evidencias/
│   └── logs/                                # Saídas brutas reais das execuções locais
├── events/
│   └── pedido.json                          # Evento API Gateway gerado via sam local generate-event
├── hello_world/
│   ├── __init__.py
│   ├── app.py                               # Handler Lambda (POST /guias)
│   └── requirements.txt                     # Apenas stdlib (sem dependências externas)
├── tests/
│   ├── __init__.py
│   ├── requirements.txt                     # Dependências de teste (pytest, boto3, requests)
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_handler.py                  # 16 testes unitários locais (pytest)
│   └── integration/
│       ├── __init__.py
│       └── test_api_gateway.py              # Teste de integração opcional (Caminho B)
├── samconfig.toml                           # Configuração SAM local (warm_containers desabilitado por padrão)
├── template.yaml                            # Template SAM (Path: /guias, Method: post, Timeout: 10)
└── README.md
```

---

## 🛠️ Pré-requisitos e Como Rodar

### Pré-requisitos validados no ambiente
- **Docker Desktop** ativo (daemon Linux containers rodando) — validado com `29.9.3`
- **AWS SAM CLI** — validado com `1.174.0`
- **Python 3.12** — validado com `3.12.10`
- **Git Bash ou WSL** (recomendado no Windows para aspas simples e redirecionamento UTF-8 sem BOM) e **curl**

### Notas técnicas observadas no ambiente (Windows + SAM CLI 1.174.0)
1. **Decodificação `isBase64Encoded` no handler (`hello_world/app.py`):** o comando `sam local generate-event apigateway aws-proxy --body ...` da versão `1.174.0` gera o arquivo `events/pedido.json` com `"isBase64Encoded": true` e o campo `body` codificado em Base64. Sem decodificar Base64 antes de `json.loads(...)`, a invocação falha com `JSONDecodeError`. O tratamento condicional (`if event.get("isBase64Encoded") ...`) com validação de JSON/tipo mantém compatibilidade tanto com eventos gerados pelo SAM CLI quanto com chamadas HTTP diretas em texto puro via `curl`.
2. **Desativação de `warm_containers = "EAGER"` em `samconfig.toml`:** o template `hello-world` atual do `sam init` inclui `warm_containers = "EAGER"` por padrão no `samconfig.toml`, o que faria `sam local start-api` sem flags já reutilizar o container desde o início. Essa chave foi comentada do `samconfig.toml` para que `sam local start-api` sem argumentos demonstre fielmente o comportamento **sem reaproveitamento** (`invocacaoNesteAmbiente: 1, 1, 1`), enquanto `sam local start-api --warm-containers LAZY` demonstra o **reaproveitamento sob demanda** (`1, 2, 3`).

### Passo a passo reproduzível (Git Bash / WSL / Linux / macOS)

```bash
# 1. Instalar dependências de teste, validar template e rodar testes unitários
pip install -r tests/requirements.txt
sam validate --lint
pytest tests/unit -v

# 2. Gerar evento de teste e compilar o pacote SAM
sam local generate-event apigateway aws-proxy --method POST --path guias \
  --body '{"requisicaoId":"R-001","hospital":"H-Recife","bolsas":["O-NEG-0142"]}' \
  > events/pedido.json
sam build

# 3. Invocar localmente por evento (duas vezes para comparar)
sam local invoke -e events/pedido.json
sam local invoke -e events/pedido.json

# 4a. Subir API HTTP local SEM reaproveitamento de container
sam local start-api
# Em outro terminal (3x):
curl -X POST http://127.0.0.1:3000/guias -H "Content-Type: application/json" \
  -d '{"requisicaoId":"R-002","hospital":"H-Caruaru"}'

# 4b. Parar o servidor (Ctrl+C) e subir COM --warm-containers LAZY
sam local start-api --warm-containers LAZY
# Repetir as 3 chamadas curl acima e observar invocacaoNesteAmbiente: 1 -> 2 -> 3

# 5. Testar o limite de tempo
# Para reproduzir o erro inicial, defina Timeout: 3 em Globals.Function no template.yaml e rode:
sam build
sam local start-api --warm-containers LAZY
# Em outro terminal, envie demorar=true (estoura aos 3 s e retorna HTTP 502):
curl -X POST http://127.0.0.1:3000/guias -H "Content-Type: application/json" \
  -d '{"requisicaoId":"R-003","demorar":true}'
# Em seguida, volte Timeout para 10 (estado final do template.yaml), rode sam build e repita -> HTTP 201
```

> **Dica no Windows PowerShell:** no PowerShell padrão, `curl` aponta para `Invoke-WebRequest` (use `curl.exe`) e `>` grava arquivos em UTF-16LE com BOM (o que pode quebrar o parse de `events/pedido.json` no SAM). Por isso, execute `sam local generate-event ... > events/pedido.json` e `curl` pelo **Git Bash** ou **WSL**.

---

## 📊 Resumo dos Resultados Reais Observados

| Experimento | Modo / Configuração | Duração Lambda (`REPORT`) | Tempo Total (`wall` / `curl`) | `invocacaoNesteAmbiente` / Status |
|---|---|---:|---:|---|
| **Passo 3 — Invocação 1** (`events/pedido.json`) | `sam local invoke` (container `d9948c...`) | `157,78 ms` (Billed `158 ms`) | `11,805 s` | `1` · `statusCode: 201` |
| **Passo 3 — Invocação 2** (`events/pedido.json`) | `sam local invoke` (container `195fdb...`) | `51,35 ms` (Billed `52 ms`) | `7,535 s` | `1` · `statusCode: 201` |
| **Passo 4A — HTTP 1 / 2 / 3** | `sam local start-api` (sem warm containers) | `60,77 ms` / `63,43 ms` / `54,98 ms` | `3,740 s` / `1,833 s` / `1,846 s` | `1`, `1`, `1` · `HTTP 201` (3 containers distintos) |
| **Passo 4B — HTTP 1 (cold)** | `sam local start-api --warm-containers LAZY` | `55,09 ms` | `4,835 s` | `1` · `HTTP 201` (container `f62512...`) |
| **Passo 4B — HTTP 2 (warm)** | `sam local start-api --warm-containers LAZY` | `1,20 ms` | `1,095 s` | `2` · `HTTP 201` (mesmo container `f62512...`) |
| **Passo 4B — HTTP 3 (warm)** | `sam local start-api --warm-containers LAZY` | `1,18 ms` | `1,091 s` | `3` · `HTTP 201` (mesmo container `f62512...`) |
| **Passo 5A — `demorar: true`** | `Timeout: 3` em `Globals.Function` | `3000,00 ms` (`timed out after 3 seconds`) | `4,206 s` | `HTTP 502` (`Internal server error`) |
| **Passo 5A — Pós-timeout (`R-004`)** | Mesmo servidor `--warm-containers LAZY` | `54,19 ms` | `1,135 s` | `1` · `HTTP 201` (ambiente reiniciado pelo timeout) |
| **Passo 5B — `demorar: true`** | `Timeout: 10` + `sam build` | `5057,22 ms` (Billed `5058 ms`) | `8,616 s` | `1` · `HTTP 201` (`G-R-003`) |

---

## ❓ Respostas às Perguntas

### 1. Por que a primeira invocação demorou mais que a segunda? O que acontece na fase de Init?
A primeira invocação é mais lenta porque passa pelo **cold start** (inicialização fria). Na fase de **Init**, o provedor (ou o emulador local via Docker no SAM) precisa alocar e subir o container/microVM isolado, inicializar o runtime do Python 3.12, carregar o código da função (`/var/task/app.py`) e suas dependências, e executar tudo o que está no escopo global do módulo (como os `import`, `JSON_HEADERS` e `contador = 0`) antes de chamar `lambda_handler`.

Na prática, isso apareceu claramente nos dois testes:
- No `sam local invoke` (`events/pedido.json`), a primeira execução teve `Duration: 157,78 ms` e tempo total de **`11,805 s`**, contra `51,35 ms` e **`7,535 s`** na segunda (onde a imagem e os caches do sistema já estavam aquecidos no host, embora cada `invoke` ainda crie um container novo).
- No `sam local start-api --warm-containers LAZY`, o contraste entre *Init* e execução quente ficou ainda mais evidente: a 1ª requisição levou **`4,835 s`** (`Duration: 55,09 ms`), enquanto a 2ª e a 3ª levaram **`1,095 s`** (`1,20 ms`) e **`1,091 s`** (`1,18 ms`) porque pularam totalmente a fase de *Init*.

---

### 2. O que o campo `invocacaoNesteAmbiente` mostrou com e sem `--warm-containers`? O que isso diz sobre guardar estado numa variável global da função?
- **Sem `--warm-containers` (`sam local start-api`):** o campo retornou **`1`, `1`, `1`**. O servidor criou e descartou um `SAM_CONTAINER_ID` distinto para cada requisição (`b50859...`, `3cb74b...`, `dbbd88...`), zerando `contador` a cada chamada.
- **Com `--warm-containers LAZY`:** o campo retornou **`1`, `2`, `3`** dentro do mesmo container (`f62512...`). Porém, quando provocamos um erro de timeout em `R-003` (`Passo 5A`), a chamada seguinte (`R-004`) voltou a retornar **`1`**, comprovando que falhas ou reciclagens reiniciam o ambiente.

**O que isso diz sobre estado em variáveis globais:** não há garantia de persistência nem de unicidade para estado em memória no modelo serverless. A plataforma pode encerrar instâncias ociosas, substituir ambientes após erro/timeout ou criar várias réplicas paralelas em picos de acesso (cada uma com sua própria cópia isolada de `contador`). Logo, **variáveis globais nunca devem guardar estado de negócio ou sessão** (como estoque, fila ou contadores confiáveis); servem apenas para otimizações descartáveis, como reutilizar pools de conexão com banco ou caches efêmeros de leitura. Estado real precisa ser externalizado (PostgreSQL, DynamoDB, Redis, SQS, S3).

---

### 3. O que aconteceu com `demorar = true`? Qual é o tempo máximo de uma execução no Lambda, e o que fazer com um trabalho mais longo?
- Com `Timeout: 3` no `template.yaml`, o `time.sleep(5)` ultrapassou o teto configurado de 3 segundos. O runtime abortou a execução (`Function 'HelloWorldFunction' timed out after 3 seconds`, `Duration: 3000.00 ms`), a API devolveu **`HTTP 502`** (`{"message":"Internal server error"}`) e o processo do container foi reiniciado (resetando `contador` para `1`). Após aumentar `Timeout: 10` e executar `sam build`, a chamada concluiu normalmente em `5057,22 ms` com **`HTTP 201`**.
- **Tempo máximo no AWS Lambda:** **15 minutos (900 segundos)** por invocação (e quando acionado de forma síncrona pelo API Gateway, o gateway impõe um teto HTTP ainda menor, de **29 segundos** por padrão).
- **O que fazer com trabalhos mais longos:** evitar requisições HTTP síncronas. Deve-se responder rapidamente (`202 Accepted`) e enviar a tarefa para processamento assíncrono via fila (**Amazon SQS** + workers), dividir em etapas orquestradas (**AWS Step Functions**), quebrar o lote em sub-tarefas paralelas ou executar em serviços sem limite de 15 minutos, como containers dedicados (**AWS Fargate / ECS**) ou jobs em batch (**AWS Batch**).

---

### 4. Com os preços de `us-east-1` da aula (US$ 0,20 por milhão de requisições e US$ 0,0000166667 por GB-s), quanto custa um milhão de execuções desta função com 128 MB e 100 ms? Mostrem a conta.

Considerando o padrão da AWS Lambda em que $1\text{ GB} = 1024\text{ MB}$:

1. **Custo por requisições:**
   $$1\,000\,000\text{ req} = 1\text{ milhão} \times \text{US\$ } 0,20/\text{milhão} = \mathbf{\text{US\$ } 0,20}$$

2. **Conversão de memória e duração:**
   $$\text{Memória} = \frac{128\text{ MB}}{1024\text{ MB/GB}} = \mathbf{0,125\text{ GB}}$$
   $$\text{Duração} = 100\text{ ms} = \mathbf{0,1\text{ s}}$$

3. **Consumo total de computação (GB-s):**
   $$1\,000\,000 \times 0,125\text{ GB} \times 0,1\text{ s} = \mathbf{12\,500\text{ GB-s}}$$

4. **Custo de computação:**
   $$12\,500\text{ GB-s} \times \text{US\$ } 0,0000166667/\text{GB-s} = \mathbf{\text{US\$ } 0,20833375}$$

5. **Custo total bruto (sem faixa gratuita):**
   $$\text{US\$ } 0,20 + \text{US\$ } 0,20833375 = \mathbf{\text{US\$ } 0,40833375 \approx \text{US\$ } 0,41}$$

> **Nota sobre o plano sempre gratuito (AWS Free Tier):** a faixa gratuita mensal do AWS Lambda cobre **1 milhão de requisições** e **400.000 GB-s** por mês. Portanto, se esse volume ocorrer dentro da cota gratuita mensal, o valor cobrado será **US$ 0,00**; a partir do segundo milhão no mesmo mês, o custo marginal é de aproximadamente **US$ 0,41 por milhão de execuções**.

---

### 5. Em que parte do Rota Vital uma função assim faria sentido, e em qual não faria?

Com base na arquitetura do projeto **Rota Vital** (`Proj-EAD`):

- **Onde FAZ sentido:**
  - **Emissão rápida de guias de transporte (`POST /guias`)**, validações de payload e webhooks de entrega.
  - **Notificações e alertas orientados a evento** (ex.: disparar aviso para hospitais ou equipe de triagem quando uma bolsa estiver perto da validade ou quando uma requisição for atendida). São tarefas *stateless*, curtas (milissegundos) e com demanda intermitente/em rajadas — perfeitas para pagar apenas por uso e escalar automaticamente.

- **Onde NÃO faz sentido:**
  - **Manter estruturas de dados em memória compartilhada**, como a lista encadeada do estoque no modo em memória (`/api/estoque`, perfil `u1`) ou a fila FIFO em memória de requisições emergenciais (`/api/requisicoes`): como ambientes serverless são efêmeros e escalam em instâncias isoladas, os dados seriam perdidos a cada reciclagem/timeout ou divergiriam entre réplicas. Esse estado exige persistência externa (como o PostgreSQL usado no perfil `infra` do Rota Vital).
  - **Cálculo pesado de CPU de longa duração**, como a detecção de duplicatas por distância de Levenshtein (`GET /api/duplicates/detect`), que no benchmark do projeto levou de **7,2 s (8.000 registros / 8 threads) até 97,9 s (16.000 registros / 1 thread)**: além de ultrapassar o timeout síncrono padrão do API Gateway (~29 s) para grandes lotes, manter funções Lambda com alta memória/CPU por dezenas de segundos em chamadas síncronas é mais caro e menos adequado do que containers dedicados ou processamento assíncrono particionado em fila.

---

## 🖼️ Evidências

Os logs brutos completos das execuções reais estão versionados em [`evidencias/logs/`](evidencias/logs/):

- [`01-ambiente-build-e-testes.log`](evidencias/logs/01-ambiente-build-e-testes.log) — Versões (`SAM CLI 1.174.0`, `Python 3.12.10`, `Docker 29.9.3`), `sam validate --lint`, `pytest tests/unit -v` (16/16) e `sam build`.
- [`02-invocacao-evento.log`](evidencias/logs/02-invocacao-evento.log) — Passo 3: `sam build` e duas invocações de `sam local invoke -e events/pedido.json`.
- [`03a-http-sem-warm-cliente.log`](evidencias/logs/03a-http-sem-warm-cliente.log) e [`03b-http-sem-warm-servidor.log`](evidencias/logs/03b-http-sem-warm-servidor.log) — Passo 4A: `sam local start-api` sem reaproveitamento (`invocacaoNesteAmbiente: 1, 1, 1` em 3 containers).
- [`04a-http-warm-lazy-cliente.log`](evidencias/logs/04a-http-warm-lazy-cliente.log) e [`04b-http-warm-lazy-servidor.log`](evidencias/logs/04b-http-warm-lazy-servidor.log) — Passo 4B: `sam local start-api --warm-containers LAZY` (`invocacaoNesteAmbiente: 1 -> 2 -> 3` e queda de latência).
- [`05a-timeout-3s-cliente.log`](evidencias/logs/05a-timeout-3s-cliente.log), [`05b-timeout-3s-servidor.log`](evidencias/logs/05b-timeout-3s-servidor.log), [`05c-timeout-10s-cliente.log`](evidencias/logs/05c-timeout-10s-cliente.log) e [`05d-timeout-10s-servidor.log`](evidencias/logs/05d-timeout-10s-servidor.log) — Passo 5: erro de timeout com `Timeout: 3` (`HTTP 502` + reset pós-timeout) e sucesso após `Timeout: 10` (`HTTP 201`).

---

## 🤖 Uso de IA (PO-CESAR-021)

- **Ferramenta utilizada:** Antigravity (modelo Gemini 4 Hydrogen).
- **Finalidade:** Apoio pontual na depuração de detalhes do AWS SAM CLI no Windows (decodificação de `isBase64Encoded` em `app.py` e ajuste de `warm_containers` no `samconfig.toml`), estruturação dos testes unitários em `pytest` e revisão textual do `README.md`.
- **Como foi validado:** A execução dos comandos SAM/Docker, a conferência dos logs em [`evidencias/logs/`](evidencias/logs/), os testes unitários no `pytest` e o cálculo da conta de custo foram realizados e validados diretamente no ambiente local.
