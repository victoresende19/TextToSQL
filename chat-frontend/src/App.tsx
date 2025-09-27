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

function App() {
  const [appState, setAppState] = useState<AppState>('landing');

  // Funções para transitar entre os estados
  const handleStartConfiguration = () => {
    setAppState('configuring');
  };

  const handleConfigSuccess = () => {
    setAppState('chat');
  };

  const handleCloseModal = () => {
    setAppState('landing');
  };

  return (
    <div className="App">
      {/* O Chat é exclusivo e substitui a página inicial */}
      {appState === 'chat' ? (
        <Chat />
      ) : (
        <>
          {/* A página de boas-vindas fica sempre ao fundo */}
          <LandingPage onStartConfiguration={handleStartConfiguration} />

          {/* O modal aparece sobre a página de boas-vindas quando estamos configurando */}
          {appState === 'configuring' && (
            <ConfigModal
              onConfigSuccess={handleConfigSuccess}
              onClose={handleCloseModal} // Passamos uma função para fechar o modal
            />
          )}
        </>
      )}
    </div>
  );
}

export default App;