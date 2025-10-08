# 🤖 Agente de Chat com Banco de Dados
    Converse com seus dados em linguagem natural usando o poder da Inteligência Artificial.

Este projeto é uma aplicação web completa que permite a usuários não-técnicos fazerem perguntas complexas a um banco de dados (como SQLite, SQL Server, PostgreSQL, etc.) usando apenas a linguagem do dia a dia. A IA traduz a pergunta em uma consulta SQL, executa no banco e devolve a resposta de forma clara e compreensível.

![alt text](image.png)

# ✨ Funcionalidades Principais
- **Interface de Chat Intuitiva:** Uma interface de chat moderna e responsiva construída com React e TypeScript.
- **Configuração Dinâmica:** Um modal de configuração permite que o usuário conecte a aplicação a qualquer banco de dados suportado pelo SQLAlchemy, sem precisar alterar o código.
- **Tradução de Linguagem Natural para SQL:** Utiliza um modelo de linguagem avançado (LLM) para converter perguntas como "Qual cliente comprou mais teclados?" em consultas SQL válidas.
- **Suporte a Múltiplos Bancos:** Graças ao SQLAlchemy, a aplicação é compatível com diversos sistemas de banco de dados.
- **Gerenciamento de Contexto:** A conversa possui memória e capacidade de resumir interações longas para otimizar o desempenho e economizar tokens.

# 🛠️ Tecnologias Utilizadas
- Backend:
    - Python
    - FastAPI
    - Langgraph
    - OpenAI
    - ChormaDB
    - SQLAlchemy
- Frontend:
    - TypeScript
    - React
    - Vite


# 📋 Pré-requisitos
Antes de começar, garanta que você tenha os seguintes softwares instalados:

- **Python 3.9+**
- **Node.js 18+** e **npm**
- Uma **chave de API da OpenAI**
- Acesso a um banco de dados (ex: um arquivo SQLite ou credenciais para um servidor SQL Server, PostgreSQL, etc.)

# ⚙️ Instalação e Execução
O projeto é dividido em duas partes: Backend (servidor FastAPI) e Frontend (aplicação React). Você precisará de dois terminais para executá-los simultaneamente.

1. Backend (Servidor FastAPI)

    a. Clone o repositório e prepare o ambiente:
    ```
    # Ambiente virtual
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate

    # Instale as bibliotecas
    pip install requirements.txt
    ```

    b. Configure sua chave de API:
    Crie um arquivo chamado .env na raiz da pasta backend e adicione sua chave da OpenAI:
    ```
    OPENAI_API_KEY="sk-sua-chave-aqui"
    ```

    c. Execute o servidor:
    ```
    uvicorn main:app --reload
    ```
    O backend estará rodando em http://127.0.0.1:8000.

2. Frontend (Aplicação React)

    a. Navegue até a pasta do frontend e instale as dependências:
    ```
    # Em um novo terminal
    cd ../frontend
    npm install
    ```

    b. Configure sua URL da API:
    Crie um arquivo chamado .env na raiz da pasta chat-frontend e adicione sua URL da API backend:
    ```
    VITE_API_BASE_URL=http://127.0.0.1:8000
    ```

    c. Execute a aplicação:
    ```
    npm run dev
    ```
    O frontend estará acessível em http://localhost:5173 (ou outra porta indicada no terminal).

# 📖 Como Usar
- **Acesse a Aplicação:** Abra seu navegador e acesse a URL do frontend (ex: http://localhost:5173).
- **Página de Boas-Vindas:** Você verá uma página explicando o projeto. Clique no botão "Configurar Base de Dados".
- **Configure o Agente:** Um modal aparecerá. Preencha os seguintes campos:
    - **Dialeto do SQLAlchemy:** O dialeto específico para o seu banco (ex: sqlite, mssql+pyodbc).
    - **String de Conexão:** A string de conexão completa do seu banco de dados.
    - **Tabelas para Consulta:** Adicione o nome e uma boa descrição para cada tabela que a IA deve ser capaz de consultar. A qualidade da descrição impacta diretamente a performance da IA.
- **Inicie o Chat:** Clique em "Iniciar Chat". Se a conexão com o banco for bem-sucedida, o modal se fechará.
- **Converse com seus Dados:** A interface de chat será carregada. Você verá as tabelas configuradas no cabeçalho e uma mensagem de boas-vindas. Agora é só fazer suas perguntas!

Obs.: A aplicação ja possui dados de exemplo. Dessa forma você pode testar de maneira simples.
- **Exemplo:** "Qual cliente da cidade de São Paulo gastou mais no total?"
- **Exemplo:** "Liste os 5 produtos mais vendidos no último mês."

# Fluxo Agente
O processo todo pode ser dividido em duas grandes fases: primeiro, preparamos a "biblioteca" de conhecimento do agente e, segundo, descrevemos como o "bibliotecário" (o agente) usa essa biblioteca para encontrar respostas.

**Fase 1 - Construindo a "Biblioteca Inteligente" (A Base de Conhecimento)**

Antes de qualquer pergunta, precisamos organizar o conhecimento para a IA. É como montar uma biblioteca e catalogar os livros.

1. **O "Endereço" da Biblioteca (String de Conexão):** Primeiro, você informa ao sistema onde a "biblioteca" de dados brutos está localizada. A string de conexão é o endereço exato que o agente usará para acessar o banco de dados.

2. **As "Etiquetas" dos Livros (Descrição das Tabelas:** Um banco de dados pode ter dezenas de tabelas ("livros"). Em vez de a IA ter que ler todos eles, você cria uma "etiqueta" (a descrição) para cada tabela de interesse. Esta é a etapa mais importante, pois uma boa etiqueta (ex: "Tabela com dados de vendas, incluindo cliente e produto") permite que a IA entenda rapidamente o conteúdo de cada "livro".

3. **Criando o "Catálogo Inteligente" (Banco Vetorial com ChromaDB):** É aqui que a mágica acontece. O sistema pega apenas a descrição de cada tabela e a transforma em um "endereço" numérico único (o embedding) dentro de um "mapa de significados". O schema técnico (```CREATE TABLE...```) não é transformado em endereço, mas é guardado como uma "anotação" junto a esse endereço. Ao final, temos um catálogo que não busca por palavras, mas por proximidade de significado.


**Fase 2 - O Fluxo de uma Pergunta (A Conversa com o "Bibliotecário")**

Agora que a biblioteca está organizada, você pode conversar com o agente. Veja como ele "pensa":
**Sua Pergunta:** "Qual ano teve mais terremotos?"

1. **Roteamento (O Bibliotecário Encontra a Prateleira Certa) - ```Route Tables```:** O agente transforma sua pergunta em um "endereço" no mesmo "mapa de significados". Em seguida, ele consulta o "catálogo inteligente" (ChromaDB) e pergunta: "Qual etiqueta de livro tem o endereço mais próximo do endereço da minha pergunta?". Ele identifica que a tabela terremotos é a mais relevante para responder.
   
2. **Geração de SQL (O Bibliotecário Lê o Índice do Livro) - ```Generate SQL```:** Com a tabela certa em mãos, o agente agora pega o schema técnico dela (a "anotação" que estava guardada). O schema funciona como o índice de um livro, mostrando todas as colunas e seus tipos. A IA, então, usa sua pergunta e este schema específico para escrever o código SQL exato necessário para encontrar a informação.

3. **Execução do SQL (O Bibliotecário Busca a Informação) - ```Execute SQL```:** Em vez de "folhear" a tabela inteira e deixar a IA "decidir" a resposta (o que seria lento, caro e imprevisível), o sistema executa a query SQL diretamente no banco de dados via Python. Isso garante que o resultado seja preciso, rápido e determinístico. O agente recebe de volta apenas os dados brutos e relevantes, como ```[{'Year': 2011, 'total': 500}]```.

4. **Validação (A Checagem de Qualidade) - ```Validate Relevance```:** Antes de prosseguir, uma parte especializada da IA faz uma verificação rápida: "O resultado que eu obtive (```[{'Year': 2011, 'total': 500}]```) parece responder à pergunta original ('Qual ano teve mais terremotos?')?". Se a resposta for "não" (por exemplo, se a query retornou o local em vez do ano), o processo volta para a etapa 2 para tentar uma nova abordagem (isso acontece até 3 vezes).

5. **Resposta Final (A Explicação em Linguagem Humana) - ```Generate Final Answer```:** Com o resultado validado, os dados brutos são entregues à parte final da IA, que age como um tradutor. Ela pega os dados ([{'Year': 2011, 'total': 500}]) e os transforma em uma resposta amigável e fácil de entender: "O ano com mais terremotos registrados foi 2011, com um total de 500 ocorrências."

![alt text](image-1.png)
