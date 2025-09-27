# 🤖 Agente de Chat com Banco de Dados
    Converse com seus dados em linguagem natural usando o poder da Inteligência Artificial.

Este projeto é uma aplicação web completa que permite a usuários não-técnicos fazerem perguntas complexas a um banco de dados (como SQLite, SQL Server, PostgreSQL, etc.) usando apenas a linguagem do dia a dia. A IA traduz a pergunta em uma consulta SQL, executa no banco e devolve a resposta de forma clara e compreensível.

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
    # Clone o repositório (caso ainda não tenha feito)
    git clone https://seu-repositorio.com/projeto.git
    cd projeto/backend

    # Crie e ative um ambiente virtual (recomendado)
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate

    # Instale as bibliotecas
    pip install requirements.txt
    ```

    b. Configure sua chave de API:
    Crie um arquivo chamado .env na raiz da pasta backend e adicione sua chave da OpenAI:
    ```
    OPENAI_API_KEY="sk-sua-chave-secreta-aqui"
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

    b. Execute a aplicação:
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