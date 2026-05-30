# Conteúdo extraído do PDF: Case - AI Engineer (2026)

---

### Página 1

# PARETO

## Case AI Engineer

Desafio para capacidade técnica e estratégica na construção de soluções de IA

## Contexto do Desafio

Você foi contratado como AI Engineer na Pareto para liderar, de forma autônoma, o desenvolvimento de uma solução de IA para um cliente estratégico.

---

### Página 2

O cliente é a **Vigil.AI**, uma empresa de cibersegurança que comercializa uma plataforma SaaS de monitoramento contínuo de postura de segurança cibernética para médias e grandes empresas. A plataforma entrega dashboards em tempo real, alertas de vulnerabilidades, relatórios de conformidade (ISO 27001, LGPD, SOC 2) e recomendações automatizadas de remediação — tudo isso com uma camada de inteligência artificial que prioriza riscos e antecipa ameaças.

A Vigil.AI está organizando seu principal evento do ano: o **Vigil Summit — Segurança para a Era da IA**, um evento corporativo exclusivo, presencial, com capacidade para 120 participantes, voltado a CISOs, CTOs, diretores de TI e gestores de risco de empresas com mais de 200 funcionários.

O objetivo do evento não é apenas educar — é vender. Ao final do dia, a Vigil.AI quer sair com o maior número possível de reuniões comerciais agendadas com decisores que assistiram às apresentações e vivenciaram demos da plataforma.

O problema é que eventos B2B corporativos sofrem com três gargalos clássicos:

- **Geração de leads qualificados**: é difícil encontrar e capturar o contato certo  
- **No-show**: em média 40–60% dos inscritos não comparecem sem uma régua de engajamento eficaz  
- **Follow-up frio**: a maioria dos contatos pós-evento é genérica, sem personalização, e converte pouco  

A Vigil.AI contratou a Pareto para resolver esses três problemas com um agente autônomo de IA que gerencie o funil completo: da captação do lead à reunião comercial agendada.

## O que você precisa construir

### Funil que o agente deve cobrir:

#### Fase 1 — Captação

O agente precisa de um mecanismo de entrada de leads. O candidato tem liberdade para propor a abordagem (landing page, formulário, chatbot de entrada, integração com LinkedIn, etc.), mas deve justificar a escolha com base no perfil do público-alvo (executivos de segurança e TI em empresas B2B).

---

### Página 3

# Fase 2 — Enriquecimento

Antes de qualquer comunicação, o agente deve enriquecer o perfil do lead com informações disponíveis publicamente (cargo real, empresa, setor, tamanho da empresa, presença em redes profissionais, sinais de interesse em segurança). Esse enriquecimento deve alimentar a personalização de todas as comunicações seguintes.

# Fase 3 — Engajamento pré-evento (régua de confirmação)

O agente deve conduzir uma sequência de comunicações proativas entre a inscrição e o dia do evento, com o objetivo de:

*   Confirmar presença
*   Reduzir no-show (meta: taxa de comparecimento acima de 70%)
*   Criar antecipação e relevância em torno do conteúdo do evento

O candidato deve inventar as regras de negócio dessa régua (ex.: lógica de confirmação de acompanhante, mensagem diferente para quem não abriu a anterior, gatilho por proximidade da data). Não existe resposta certa — queremos ver o raciocínio.

# Fase 4 — Pós-evento (régua de follow-up comercial)

Após o evento, o agente deve iniciar uma sequência de follow-up personalizada com o objetivo de agendar uma reunião comercial para apresentação da plataforma Vigil.AI. A abordagem deve usar o contexto do evento (o que o lead viu, o que demonstrou interesse) para personalizar a comunicação.

## Canal de comunicação:

O candidato pode escolher o canal (WhatsApp, Telegram, e-mail ou combinação). A escolha deve ser justificada com base no perfil do público e na natureza do evento.

# Requisitos Técnicos

## Obrigatórios:

| # | Requisito | Detalhe |
| :--- | :--- | :--- |
| 1 | Agente funcional | O agente deve estar operacional e passível de teste pelo time da Pareto |
| 2 | Banco de dados | Uso de banco de dados comprovado (relacional ou não-relacional), com estrutura acessível para validação |
| 3 | Documentação técnica | Documento acessível descrevendo arquitetura, decisões e como usar a solução. A ausência de documentação implica reprovação automática |

---

### Página 4

4 Acesso para teste O candidato deve fornecer instruções claras de acesso. O e-mail ramon@pareto.io pode ser usado para acessos temporários necessários
5 Conversas demonstráveis As interações com o agente podem ser simuladas com personas sintéticas ou reais (ex.: testes com amigos). O importante é que o fluxo seja demonstrável de ponta a ponta
6 Stack com LLM A solução deve utilizar um modelo de linguagem (LLM). Damos preferência ao ecossistema Anthropic (família Claude), especialmente para implementações que envolvam agência, uso de ferramentas e raciocínio estruturado

**Opcionais (valorizam a entrega):**

*   **Interface web** com acesso público protegido por senha para visualização e interação com o agente
*   Uso de **plataformas low-code/no-code** de agentes de forma criativa e integrada à solução (ex.: para orquestração ou interface)
*   **Painel de monitoramento** simples mostrando status dos leads no funil (inscritos, confirmados, presentes, reuniões agendadas)

# Entregáveis Esperados

Você deve entregar um documento técnico (formato livre: PDF, Markdown, Notion, repositório GitHub com README bem estruturado, etc.) contendo:

## 1. Arquitetura da Solução

*   Desenho ou descrição detalhada da arquitetura completa
*   Camadas da aplicação (entrada de dados, processamento, LLM, banco de dados, canais de comunicação)
*   Fluxo de dados entre os componentes
*   Onde cada fase do funil (Captação, Enriquecimento, Engajamento, Follow-up) se encaixa

## 2. Stack Tecnológico Justificado

Liste e justifique cada tecnologia escolhida:
*   Modelo de LLM e por quê
*   Framework de agente (LangChain, CrewAI, Agno, SDK nativo, etc.)

---

### Página 5

- Banco de dados e modelo de dados
- Ferramenta de orquestração/workflow (se aplicável)
- Canal de comunicação e integração usada
- Infraestrutura de deploy

### 3. Réguas de Comunicação

- Descreva detalhadamente o fluxo de mensagens das duas réguas (pré e pós-evento)
- Inclua as regras de negócio que você definiu (gatilhos, condições, timing)
- Apresente ao menos um exemplo de mensagem personalizada para cada régua, demonstrando uso do enriquecimento de dados

### 4. Estratégia de Dados e Personalização

- Como os dados dos leads serão coletados, armazenados e utilizados?
- Como o enriquecimento funciona na prática? Quais fontes? Como o dado enriquecido é usado pelo agente?
- Como você garante conformidade com LGPD no tratamento dos dados dos participantes?

### 5. Decisões Estratégicas e Racional

- Quais foram as três principais decisões técnicas ou de produto que você tomou?
- Quais alternativas você considerou e por que as descartou?
- Que referências de mercado, cases ou frameworks embasaram suas escolhas?

### 6. Plano de Execução (Primeiros 5 dias)

- Assuma que você começa amanhã: descreva os primeiros passos técnicos
- O que você provisionaria/configuraria primeiro e por quê?
- Qual fase do funil você atacaria primeiro?

## Cenário de Escala (Pergunta Bônus)

O Vigil Summit foi um sucesso. A Vigil.AI quer replicar o modelo para 10 eventos regionais simultâneos, cada um com perfis de público distintos (manufatura, saúde, financeiro, governo). Como você adaptaria a arquitetura para suportar isso sem reescrever o agente do zero?

---

### Página 6

# Critérios de Avaliação

| Dimensão | O que buscamos |
| --- | --- |
| Entendimento do problema | O candidato compreendeu que o desafio é de negócio (funil, conversão, no-show) e não apenas técnico |
| Qualidade do agente | O agente funciona, tem memória de contexto, usa o enriquecimento para personalizar e toma decisões autônomas coerentes |
| Arquitetura | A solução é coerente, escalável e as escolhas tecnológicas são justificadas |
| Régua de comunicação | As réguas são criativas, personalizadas e orientadas a conversão — não genéricas |
| Documentação | Clara, acessível, suficiente para que outro engenheiro continue o trabalho |
| Raciocínio estratégico | O candidato demonstra opinião fundamentada, não apenas execução mecânica |
| Capacidade de ponta a ponta | A solução cobre o funil completo — captação, engajamento, follow-up — mesmo que com profundidades diferentes em cada etapa |

**Dúvidas?** Entre em contato pelo e-mail gabriel@pareto.io