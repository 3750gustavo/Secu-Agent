### O meu Brainstorm:

Okay, o problema pede um agente de IA que gere leads, reduza no-shows e agende reuniões.

O problema principal é o fato que muitos inscritos não comparecem e o follow-up é frio. Precisamos de um agente que personaliza as interações.

**Captação de leads**: Qualquer entrada de dados. Pode ser landing page, formulário ou integração com LinkedIn, como não sei criar chatbots no linkedin essa opção fica fora de questão, poderia ser envio de emails? isso está dentro do aceitavel pelos requisitos? Hmm, na captação de leads, o usuário tem que inserir as informações. Pode se fazer mais sentido criar uma landing page para que as pessoas se inscrevam e simplesmente divulgar a mesma via posts no linkedin, assim temos o melhor dos dois mundos, "integração com linkedin" sem a parte complicada.

Podemos criar um SPA elegante que usa somente CDNS para front (vantagem funciona em buckets S3 ou provedores estaticos baratos), e usando fastapi pra o backend (possuo alguns outros projetos em fast que posso usar de molde evitando ter que começar do zero).

**Banco de Dados**: SQLite, fácil de setup e não precisa de infraestrutura. Modelagem de dados: tabela leads (id, name, email, company, job_title, source, status). Tabela messages (id, lead_id, message_text, timestamp, channel).

**Enriquecimento**: Vamos precisar de uma API para enriquecer os dados e precisa ser obrigatoriamente gratuita, não vou gastar pra um teste de vaga. Primeiro, o que é "enriquecimento" nesse contexto? O que estamos REALMENTE tentando conseguir aqui: dados sobre a empresa, cargo, etc. que já estão disponíveis em fontes públicas.

Espera, eu não poderia simplesmente solicitar alguns campos chaves na landing page ao se inscrever e apartir desses dados conseguir achar mais sem precisar fazer o candidato prencher uma biblia de campos? Alem disso temos que pensar quais campos são considerados sensiveis ou não.

Ex: campos na landing page:

- Nome Completo
- E-mail
- Empresa
- Cargo

Com essas informações, podemos usar a API de enriquecimento para complementar com:
- Tamanho da empresa
- Setor/Indústria
- Presença em redes profissionais (LinkedIn, Twitter)
- Sinais de interesse em segurança da informação

Mas qual API gratuita pode nos ajudar? Acho que por enquanto irei pular esse requisito e se der tempo eu volto nele após implementar todo o resto. Ou talvez eu possa simular isso com um mock.

**Canal de comunicação**: Email é o mais profissional para o público-alvo (C-levels). WhatsApp pode ser invasivo. Telegram é mais informal. Vamos com email. Usamos a API do google (Gmail) para enviar mensagens.

**LLM**: Irei usar minha propria API custom OAI Compatible e  deixo claro que com pequenos ajustes de compatibilidade eu consigo adaptar meu codigo pra funcionar com a anthropic (isso pois vou fazer sem sdk usando requests, então fica facil migrar). Ajustar os endpoints e o payload de acordo com a API Claude 2.

**Arquitetura**:

Frontend: Quais são os grandes frameworks com opcao de uso via CDN que consigo por muito em poucas linhas pra dar aquele look de site proficional nivel SAAS do silicio valei? Alpine.js ou SvelteKit? Talvez Alpine.js com TailwindCSS, já que sou mais familiarizado com ele.

Backend: FastAPI, pois posso rapidamente montar rotas REST para CRUD de leads e disparo de emails. Além disso ele vem com OpenAPI automatica, o que ajuda na documentação.

Database: SQLite com SQLAlchemy. Facil de configurar e não preciso lidar com servidores de BD.

Enriquecimento: Simulação via mocks na versão inicial, se eu terminar antes do prazo eu revisito esse ponto.

Engajamento pré-evento: Regras de negocio que incluem envio de lembretes com intervalos decrescentes conforme a data se aproxima. Exemplo: envia um email 3 dias antes, outro 24h antes, e um SMS no dia (SMS via Twilio, mas se nao tiver creditos, omito).

Follow-up pós-evento: Envio de email personalizado, mencionando pontos do evento que o lead pode ter gostado, e propondo agendar uma reuniao. Exemplo: "Soubemos que voce participou da sesso sobre [topico]. Queremos mostrar como nossa plataforma resolveu X problema. Podemos marcar uma ligacao?"

**LGPD Compliance**: Armazenar os dados minimos necessarios, consentimento explicito na landing page, e permitir opt-out. Na documentação, descrever as politicas de privacidade.

**Implementação Passo a Passo**:

1. Configurar frontend com Alpine.js/Tailwind.
2. Backend FastAPI com rotas para cadastro de lead, atualizacao de status, etc.
3. Banco SQLite com schema para leads e mensagens.
4. Integração com Claude para geração de textos personalizados.
5. Sistema de agendamento de envios de emails via Gmail API.
6. Testes unitários básicos.
7. Documentação técnica.

Além disso, teremos que lidar com a regua de negocio para o envio de emails pré e pós evento, com condições como:

- Se o lead não confirmou presença, enviar lembrete
- Se abriu o email mas não respondeu, enviar follow-up
- Se compareceu, enviar mensagem de agradecimento e oferta de demo

Para a regua de negocio, usarei um sistema de fila de processamento assincrono, onde o backend verifica periodicamente quais leads precisam de acoes e agenda os envios.

Finalmente, irei hospedar no Heroku por ser simples e possuir integração automatica com github pra deploys zero terminal. Alem disso, posso fornecer o link do app para o Pareto testar.

**Potenciais Problemas**:

- Atraso na API de enriquecimento, que afeta a personalização.
- Limites nas APIs de email (gmail tem limite diario).
- Dificuldade em sincronizar a fila de envios com horario real.

**Mitigações**:

- Usar mocks para enriquecimento inicial.
- Implementar retry logic nos envios de email.
- Usar um scheduler como celery ou background tasks com redis para processar as filas.

Espera, redis é gratuito? melhor pensar em um scheduler mais a moda antiga que seja 100% free garantido e só um pip install de distancia. Pode ser o APScheduler do Python.

**Cronograma de Implementação**:

1. Dia 1: Setup do ambiente de dev, criação do frontend basico.
2. Dia 2: Implementar backend e banco de dados.
3. Dia 3: Integrar Claude para gerar textos.
4. Dia 4: Sistema de envio de emails.
5. Dia 5: Testes finais e documentação.

Preciso garantir que tudo funcione em conjunto, e que o agente mantenha o contexto de cada lead durante todo o funil.