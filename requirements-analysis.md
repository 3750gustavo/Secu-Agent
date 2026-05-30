# Análise de Requisitos - Case AI Engineer Pareto

## Objetivo
Este documento serve como guia de referência para brainstorm, identificando claramente o que é obrigatório, opcional ou flexível nos requisitos do case. O foco é evitar escolhas de tecnologias incompatíveis com as exigências do problema.

## ⚠️ IMPORTANTE: O Que Precisa Ser Entregue

**NÃO é apenas um plano/documento!** O case exige que você:

1. **Construa e implemente um agente funcional** que esteja operacional e passível de teste pelo time da Pareto
2. **Forneça acesso para teste** com instruções claras
3. **Crie um documento técnico** descrevendo a solução (arquitetura, stack, réguas, etc.)
4. **Demonstre o fluxo de ponta a ponta** com conversas simuladas ou reais

O "Plano de Execução (Primeiros 5 dias)" é APENAS uma seção do documento técnico que descreve como você começaria a implementação caso fosse contratado. Não é o prazo para entregar o case!

**Resumo**: Você precisa implementar a solução completa + documentar tudo, não apenas planejar.

---

# RESUMO DO PROBLEMA/DESAFIO

## Contexto
A **Vigil.AI** é uma empresa de cibersegurança que comercializa uma plataforma SaaS de monitoramento contínuo de postura de segurança cibernética. Eles estão organizando seu principal evento do ano: o **Vigil Summit — Segurança para a Era da IA**.

## O Evento
- **Tipo**: Corporativo exclusivo, presencial
- **Capacidade**: 120 participantes
- **Público-alvo**: CISOs, CTOs, diretores de TI, gestores de risco de empresas com mais de 200 funcionários
- **Objetivo**: Vender - ao final do dia, querem sair com o maior número possível de reuniões comerciais agendadas

## Os Três Problemas a Resolver
Eventos B2B corporativos sofrem com três gargalos clássicos que a Vigil.AI precisa resolver:

1. **Geração de leads qualificados**: É difícil encontrar e capturar o contato certo
2. **No-show**: Em média 40–60% dos inscritos não comparecem sem uma régua de engajamento eficaz
3. **Follow-up frio**: A maioria dos contatos pós-evento é genérica, sem personalização, e converte pouco

## A Solução Solicitada
Construir um **agente autônomo de IA** que gerencie o funil completo: da captação do lead à reunião comercial agendada.

### O Agente Deve Cobrir 4 Fases:

**Fase 1 — Captação**
- Mecanismo de entrada de leads (landing page, formulário, chatbot, LinkedIn, etc.)
- Deve ser justificado com base no perfil do público-alvo

**Fase 2 — Enriquecimento**
- Enriquecer o perfil do lead com informações públicas (cargo, empresa, setor, tamanho, redes profissionais, sinais de interesse)
- Esses dados alimentam a personalização de todas as comunicações seguintes

**Fase 3 — Engajamento pré-evento**
- Sequência de comunicações proativas entre inscrição e evento
- Objetivos: confirmar presença, reduzir no-show (meta: >70% comparecimento), criar antecipação
- O candidato deve inventar as regras de negócio dessa régua

**Fase 4 — Pós-evento**
- Sequência de follow-up personalizada após o evento
- Objetivo: agendar reunião comercial para apresentação da plataforma
- Deve usar o contexto do evento para personalizar a comunicação

## Métricas de Sucesso
- **Taxa de comparecimento**: Acima de 70% (para reduzir no-show de 40-60%)
- **Conversão**: Número de reuniões comerciais agendadas

## O Que Está em Jogo
A Vigil.AI contratou a Pareto para resolver esses três problemas com um agente de IA. O sucesso do evento depende da capacidade do agente de:
- Capturar leads qualificados
- Garantir que eles compareçam
- Converter presença em reuniões comerciais

---

## 1. REQUISITOS OBRIGATÓRIOS (NÃO NEGOCIÁVEIS)

### 1.1 Funcionalidades do Agente
- **Agente funcional e operacional**: Deve estar pronto para teste pelo time da Pareto
- **Cobertura completa do funil**:
  - Fase 1: Captação de leads
  - Fase 2: Enriquecimento de perfil do lead
  - Fase 3: Engajamento pré-evento (régua de confirmação)
  - Fase 4: Follow-up pós-evento (régua comercial)
- **Memória de contexto**: O agente deve manter contexto entre interações
- **Personalização baseada em enriquecimento**: As comunicações devem usar dados enriquecidos
- **Decisões autônomas coerentes**: O agente deve tomar decisões lógicas

### 1.2 Banco de Dados
- **Uso obrigatório de banco de dados**: Pode ser relacional OU não-relacional
- **Estrutura acessível para validação**: Deve ser possível inspecionar/validar os dados
- **NOTA**: O tipo específico (SQLite, PostgreSQL, MongoDB, etc.) é FLEXÍVEL

### 1.3 LLM (Large Language Model)
- **Uso obrigatório de LLM**: A solução DEVE utilizar um modelo de linguagem
- **Preferência (não obrigação)**: Ecossistema Anthropic (família Claude), especialmente para:
  - Implementações com agência
  - Uso de ferramentas
  - Raciocínio estruturado
- **NOTA**: Outros LLMs são aceitáveis, mas Claude é preferido

### 1.4 Documentação
- **Documento técnico obrigatório**: Ausência implica reprovação automática
- **Conteúdo mínimo exigido**:
  1. Arquitetura da solução
  2. Stack tecnológico justificado
  3. Réguas de comunicação (pré e pós-evento)
  4. Estratégia de dados e personalização
  5. Decisões estratégicas e racional
  6. Plano de execução (primeiros 5 dias)
- **Formato livre**: PDF, Markdown, Notion, GitHub com README, etc.

### 1.5 Acesso e Testes
- **Instruções claras de acesso**: O e-mail ramon@pareto.io pode ser usado para acessos temporários
- **Conversas demonstráveis**: Fluxo de ponta a ponta deve ser demonstrável
- **Testes possíveis**: Pode usar personas sintéticas ou reais

### 1.6 Conformidade Legal
- **LGPD**: A solução deve garantir conformidade com LGPD no tratamento de dados

---

## 2. REQUISITOS Opcionais (Valorizam a Entrega)

### 2.1 Interface
- **Interface web com acesso público protegido por senha**: Para visualização e interação com o agente

### 2.2 Plataformas Low-Code/No-Code
- **Uso criativo e integrado**: Para orquestração ou interface

### 2.3 Monitoramento
- **Painel de monitoramento simples**: Mostrando status dos leads no funil (inscritos, confirmados, presentes, reuniões agendadas)

---

## 3. REQUISITOS FLEXÍVEIS (EM ABERTO)

### 3.1 Arquitetura de Alto Nível
- **Tipo de solução**: O case NÃO especifica se deve ser:
  - Site + servidor
  - Servidor que interage com API (WhatsApp, Telegram, email)
  - Aplicação desktop
  - Serviço backend-only
  - Combinação de qualquer um dos acima
- **NOTA**: A escolha deve ser justificada com base no público-alvo e natureza do evento

### 3.2 Mecanismo de Captação de Leads (Fase 1)
- **Abordagem em aberto**: Pode ser qualquer um dos seguintes:
  - Landing page
  - Formulário
  - Chatbot de entrada
  - Integração com LinkedIn
  - Outra abordagem criativa
- **Requisito**: Deve justificar a escolha com base no perfil do público-alvo (executivos de segurança e TI em empresas B2B)

### 3.3 Canal de Comunicação
- **Opções disponíveis**:
  - WhatsApp
  - Telegram
  - E-mail
  - Combinação de canais
- **Requisito**: Deve justificar a escolha com base no perfil do público e natureza do evento

### 3.4 Stack Tecnológico Específico

#### 3.4.1 Framework de Agente
- **Opções mencionadas**:
  - LangChain
  - CrewAI
  - Agno
  - SDK nativo do LLM
  - Outros não mencionados
- **NOTA**: Escolha livre, mas deve ser justificada

#### 3.4.2 Banco de Dados Específico
- **Tipo**: Relacional OU não-relacional (ambos aceitos)
- **Exemplos possíveis**:
  - Relacional: SQLite, PostgreSQL, MySQL, MariaDB
  - Não-relacional: MongoDB, Firebase, DynamoDB
- **NOTA**: SQLite é uma opção válida para reduzir dependências e complexidade

#### 3.4.3 Orquestração/Workflow
- **Uso opcional**: Ferramenta de orquestração/workflow
- **Exemplos**: Airflow, Prefect, n8n, Make, ou solução customizada
- **NOTA**: Se usado, deve ser justificado

#### 3.4.4 Infraestrutura de Deploy
- **Em aberto**: Pode ser qualquer abordagem:
  - Cloud (AWS, GCP, Azure)
  - VPS
  - Local
  - Serverless
  - Container (Docker, Kubernetes)
- **NOTA**: Deve ser justificado

### 3.5 Réguas de Comunicação
- **Regras de negócio**: O candidato deve inventar as regras
- **Exemplos de regras a definir**:
  - Lógica de confirmação de acompanhante
  - Mensagem diferente para quem não abriu a anterior
  - Gatilho por proximidade da data
  - Outras regras criativas
- **NOTA**: Não existe resposta certa — o importante é o raciocínio

### 3.6 Estratégia de Enriquecimento
- **Fontes de dados**: Em aberto
- **Tipo de dados**: Em aberto (cargo real, empresa, setor, tamanho, redes profissionais, sinais de interesse)
- **Método de enriquecimento**: Em aberto
- **NOTA**: Deve ser descrito como funciona na prática

### 3.7 Formato de Entrega
- **Documento técnico**: Formato livre (PDF, Markdown, Notion, GitHub com README, etc.)
- **NOTA**: Qualquer formato é aceitável desde que contenha todos os itens obrigatórios

---

## 4. REQUISITOS DE NEGÓCIO (Contexto)

### 4.1 Público-Alvo
- **Perfil**: CISOs, CTOs, diretores de TI, gestores de risco
- **Tipo de empresa**: Empresas com mais de 200 funcionários
- **Setor**: B2B corporativo

### 4.2 Evento
- **Nome**: Vigil Summit — Segurança para a Era da IA
- **Tipo**: Corporativo exclusivo, presencial
- **Capacidade**: 120 participantes
- **Objetivo**: Vender (agendar reuniões comerciais)

### 4.3 Métricas de Sucesso
- **Taxa de comparecimento**: Meta acima de 70% (para reduzir no-show de 40-60%)
- **Conversão**: Agendar reuniões comerciais

### 4.4 Problemas a Resolver
1. Geração de leads qualificados
2. No-show (40-60% dos inscritos não comparecem)
3. Follow-up frio (contatos genéricos, sem personalização)

---

## 5. CENÁRIO DE ESCALA (BÔNUS)

### 5.1 Requisito de Escala
- **Situação**: Replicar para 10 eventos regionais simultâneos
- **Perfis distintos**: Manufatura, saúde, financeiro, governo
- **Desafio**: Adaptar arquitetura sem reescrever o agente do zero
- **NOTA**: É uma pergunta bônus, não é obrigatório implementar

---

## 6. CRITÉRIOS DE AVALIAÇÃO

### 6.1 O que é Avaliado
1. **Entendimento do problema**: Compreensão de que é um desafio de negócio (funil, conversão, no-show)
2. **Qualidade do agente**: Funcionalidade, memória, personalização, decisões autônomas
3. **Arquitetura**: Coerência, escalabilidade, justificativa das escolhas
4. **Régua de comunicação**: Criatividade, personalização, orientação a conversão
5. **Documentação**: Clareza, acessibilidade, suficiência para continuidade
6. **Raciocínio estratégico**: Opinião fundamentada, não execução mecânica
7. **Capacidade de ponta a ponta**: Cobertura do funil completo

---

## 7. RESUMO VISUAL

| Categoria | Obrigatório | Opcional | Flexível |
|-----------|-------------|----------|----------|
| **Arquitetura** | Cobrir funil completo | Interface web | Tipo (site/servidor/API) |
| **Banco de Dados** | Usar banco de dados | - | Tipo (relacional/não-relacional) |
| **LLM** | Usar LLM | - | Modelo (preferência Claude) |
| **Framework Agente** | - | - | Qualquer um (LangChain, etc.) |
| **Canal Comunicação** | - | - | WhatsApp/Telegram/Email |
| **Captação Leads** | - | - | Landing page/form/chatbot/LinkedIn |
| **Documentação** | Documento técnico | - | Formato (PDF/Markdown/etc.) |
| **Orquestração** | - | - | Qualquer ferramenta ou custom |
| **Deploy** | - | - | Qualquer infraestrutura |
| **Monitoramento** | - | Painel simples | - |
| **Low-Code/No-Code** | - | Uso criativo | - |

---

## 8. PONTOS DE ATENÇÃO PARA BRAINSTORM

### ✅ PODE (Flexível)
- Usar SQLite como banco de dados
- Escolher qualquer framework de agente
- Implementar apenas backend sem interface web
- Usar WhatsApp, Telegram ou e-mail como canal
- Criar landing page simples ou usar formulário
- Deploy local ou em qualquer cloud
- Usar ou não ferramenta de orquestração

### ⚠️ DEVE (Obrigatório)
- Implementar as 4 fases do funil
- Usar algum tipo de banco de dados
- Usar um LLM (preferencialmente Claude)
- Criar documentação técnica completa
- Fornecer instruções de acesso
- Garantir conformidade com LGPD
- O agente deve ter memória de contexto
- Personalizar comunicações com dados enriquecidos

### ❌ NÃO PODE (Restrições)
- Entregar sem documentação técnica
- Não usar banco de dados
- Não usar LLM
- Não cobrir o funil completo
- Ignorar LGPD
- Não fornecer acesso para teste

---

## 9. DECISÕES TÉCNICAS A JUSTIFICAR

No documento final, você precisará justificar:

1. **Escolha do LLM**: Por que este modelo específico?
2. **Framework de agente**: Por que esta ferramenta?
3. **Banco de dados**: Por que este tipo e implementação?
4. **Canal de comunicação**: Por que este canal para este público?
5. **Mecanismo de captação**: Por que esta abordagem?
6. **Infraestrutura**: Por que esta escolha de deploy?
7. **Orquestração** (se usado): Por que necessária?

---

## 10. CONCLUSÃO

O case oferece **grande flexibilidade** na escolha de tecnologias específicas, mas é **rigoroso** quanto à:
- Funcionalidade completa do agente
- Cobertura de todo o funil
- Uso de LLM e banco de dados
- Documentação técnica
- Acesso para testes

A chave para o sucesso não é escolher a tecnologia mais moderna, mas sim:
1. Justificar bem cada escolha
2. Entregar um agente que funciona de ponta a ponta
3. Demonstrar raciocínio estratégico
4. Criar réguas de comunicação criativas e personalizadas
5. Documentar tudo de forma clara

**SQLite é uma opção válida** para o banco de dados, desde que justificada (ex: reduzir complexidade, facilitar deploy, adequado para escala do projeto).