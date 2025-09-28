// src/App.tsx

import { useState } from 'react';
import Chat from './components/Chat';
import ConfigModal from './components/ConfigModal';
import LandingPage from './components/LandingPage';

// Importe todos os CSS necessários
import './components/Chat.css';
import './components/Modal.css';
import './components/LandingPage.css';

// Define os possíveis estados da nossa aplicação
type AppState = 'landing' | 'configuring' | 'chat';

// NOVO: Define a tipagem da tabela para ser usada aqui
interface TableInfo {
  table_name: string;
  description: string;
}

function App() {
  const [appState, setAppState] = useState<AppState>('landing');
  // NOVO: Estado para armazenar a lista de tabelas configuradas
  const [configuredTables, setConfiguredTables] = useState<TableInfo[]>([]);

  const handleStartConfiguration = () => {
    setAppState('configuring');
  };

  // ALTERADO: A função agora recebe a lista de tabelas do modal
  const handleConfigSuccess = (finalTables: TableInfo[]) => {
    setConfiguredTables(finalTables); // Armazena a lista de tabelas
    setAppState('chat'); // Muda para a tela de chat
  };

  const handleCloseModal = () => {
    setAppState('landing');
  };

  return (
    <div className="App">
      {appState === 'chat' ? (
        // ALTERADO: Passa a lista de tabelas configuradas como prop para o Chat
        <Chat configuredTables={configuredTables} />
      ) : (
        <>
          <LandingPage onStartConfiguration={handleStartConfiguration} />
          {appState === 'configuring' && (
            <ConfigModal
              onConfigSuccess={handleConfigSuccess}
              onClose={handleCloseModal}
            />
          )}
        </>
      )}
    </div>
  );
}

export default App;