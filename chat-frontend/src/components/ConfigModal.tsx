// src/ConfigModal.tsx

import React, { useState } from 'react';

// Tipagem para a props do componente
interface ConfigModalProps {
    onConfigSuccess: () => void;
    onClose: () => void;
}

// Tipagem para a estrutura de uma tabela
interface Table {
    table_name: string;
    description: string;
}

const API_URL = "https://texttosql-k8p8.onrender.com/configure_agent";

const ConfigModal: React.FC<ConfigModalProps> = ({ onConfigSuccess }) => {
    // Estados para os campos do formulário
    const [dialect, setDialect] = useState('sqlite');
    const [connectionString, setConnectionString] = useState('sqlite:///db/database.db');
    const [tables, setTables] = useState<Table[]>([
        { table_name: 'clientes', description: 'Esta tabela armazena informações sobre os clientes.' },
        { table_name: 'produtos', description: 'Contém a lista de produtos disponíveis e seus preços.' },
        { table_name: 'vendas', description: 'Registra todas as transações de vendas.' },
    ]);

    // Estados para controle de UI
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Funções para manipular a lista de tabelas
    const handleTableChange = (index: number, field: keyof Table, value: string) => {
        const newTables = [...tables];
        newTables[index][field] = value;
        setTables(newTables);
    };

    const handleAddTable = () => {
        setTables([...tables, { table_name: '', description: '' }]);
    };

    const handleRemoveTable = (index: number) => {
        const newTables = tables.filter((_, i) => i !== index);
        setTables(newTables);
    };

    // Função para enviar a configuração para o backend
    const handleConfigure = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        const payload = {
            db_credentials: { dialect, connection_string: connectionString },
            tables,
        };

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ocorreu um erro desconhecido.');
            }

            // Se a configuração foi bem-sucedida, chama a função do componente pai
            onConfigSuccess();

        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };


    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h2>Configurar Agente de Banco de Dados</h2>
                <p>Forneça as informações de conexão e descreva as tabelas que serão consultadas.</p>

                <form onSubmit={handleConfigure}>
                    <fieldset>
                        <legend>Credenciais do Banco</legend>
                        <label>
                            Dialeto (ex: sqlite, postgresql+psycopg2):
                            <input type="text" value={dialect} onChange={(e) => setDialect(e.target.value)} required />
                        </label>
                        <label>
                            String de Conexão:
                            <input type="text" value={connectionString} onChange={(e) => setConnectionString(e.target.value)} required />
                        </label>
                    </fieldset>

                    <fieldset>
                        <legend>Tabelas para Consulta</legend>
                        {tables.map((table, index) => (
                            <div className="table-entry" key={index}>
                                <input
                                    type="text"
                                    placeholder="Nome da tabela"
                                    value={table.table_name}
                                    onChange={(e) => handleTableChange(index, 'table_name', e.target.value)}
                                    required
                                />
                                <input
                                    type="text"
                                    placeholder="Descrição da tabela"
                                    value={table.description}
                                    onChange={(e) => handleTableChange(index, 'description', e.target.value)}
                                    required
                                />
                                <button type="button" className="remove-btn" onClick={() => handleRemoveTable(index)}>
                                    &times;
                                </button>
                            </div>
                        ))}
                        <button type="button" className="add-btn" onClick={handleAddTable}>
                            + Adicionar Tabela
                        </button>
                    </fieldset>

                    {error && <div className="error-message">{error}</div>}

                    <button type="submit" className="submit-btn" disabled={isLoading}>
                        {isLoading ? 'Configurando...' : 'Iniciar Chat'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ConfigModal;