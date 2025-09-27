// src/components/LandingPage.tsx

import React from 'react';

interface LandingPageProps {
    onStartConfiguration: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onStartConfiguration }) => {
    return (
        <div className="landing-container">
            <div className="landing-content">
                <h1>Bem-vindo ao Agente de Consulta a Banco de Dados</h1>
                <p>
                    Esta é uma interface de chat inteligente que se conecta diretamente à sua base de dados.
                    Converse em linguagem natural e obtenha insights sem precisar escrever uma única linha de SQL.
                </p>
                <div className="landing-steps">
                    <div className="step">
                        <span>1</span>
                        <p>Clique no botão abaixo e configure as credenciais do seu banco de dados.</p>
                    </div>
                    <div className="step">
                        <span>2</span>
                        <p>Informe e descreva quais tabelas você deseja que a IA possa consultar.</p>
                    </div>
                    <div className="step">
                        <span>3</span>
                        <p>Comece a conversar e fazer perguntas sobre seus dados!</p>
                    </div>
                </div>
                <button className="landing-button" onClick={onStartConfiguration}>
                    Configurar Base de Dados
                </button>
            </div>
        </div>
    );
};

export default LandingPage;