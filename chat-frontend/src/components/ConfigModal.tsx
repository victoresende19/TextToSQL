// src/components/ConfigModal.tsx

import React, { useState } from 'react';
import type { FormEvent } from 'react';

// Tipagem para a props do componente
interface ConfigModalProps {
    // ALTERADO: A função de sucesso agora espera receber a lista de tabelas
    onConfigSuccess: (tables: Table[]) => void;
    onClose: () => void;
}

// Tipagem para a estrutura de uma tabela
interface Table {
    table_name: string;
    description: string;
}

const API_URL = import.meta.env.VITE_API_BASE_URL;

const dialectOptions = [
    { value: 'sqlite', label: 'SQLite', template: 'sqlite:///db/database.db' },
    { value: 'postgresql+psycopg2', label: 'PostgreSQL', template: 'postgresql+psycopg2://user:password@host:5432/database' },
    { value: 'mssql+pyodbc', label: 'SQL Server', template: 'mssql+pyodbc://user:password@host/database?driver=ODBC+Driver+17+for+SQL+Server' }
];

const ConfigModal: React.FC<ConfigModalProps> = ({ onConfigSuccess, onClose }) => {
    const [dialect, setDialect] = useState(dialectOptions[1].value);
    const [connectionString, setConnectionString] = useState(dialectOptions[1].template);
    const [tables, setTables] = useState<Table[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDialectChange = (newDialect: { value: string; template: string; }) => {
        setDialect(newDialect.value);
        setConnectionString(newDialect.template);
        setIsConnected(false);
        setTables([]);
        setError(null);
    };

    const handleConnectAndFetchTables = async () => {
        setIsConnecting(true);
        setError(null);
        const connectionPayload = {
            db_credentials: { dialect, connection_string: connectionString },
            tables: [],
        };
        try {
            const configResponse = await fetch(`${API_URL}/configure_agent`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(connectionPayload),
            });
            if (!configResponse.ok) {
                const errorData = await configResponse.json();
                throw new Error(errorData.detail || 'Falha ao conectar ao banco de dados.');
            }
            const tablesResponse = await fetch(`${API_URL}/tables`);
            if (!tablesResponse.ok) {
                throw new Error('Conexão bem-sucedida, mas falha ao listar as tabelas.');
            }
            const fetchedTables: Table[] = await tablesResponse.json();
            setTables(fetchedTables.map(t => ({ table_name: t.table_name, description: '' })));
            setIsConnected(true);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsConnecting(false);
        }
    };

    const handleTableChange = (index: number, field: keyof Table, value: string) => {
        const newTables = [...tables];
        newTables[index][field] = value;
        setTables(newTables);
    };

    const handleRemoveTable = (indexToRemove: number) => {
        setTables(tables.filter((_, index) => index !== indexToRemove));
    };

    const handleFinalSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError(null);
        const finalPayload = {
            db_credentials: { dialect, connection_string: connectionString },
            tables,
        };
        try {
            const response = await fetch(`${API_URL}/configure_agent`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalPayload),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ocorreu um erro desconhecido.');
            }
            // ALTERADO: Passa a lista final de tabelas para a função de sucesso
            onConfigSuccess(tables);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };


    return (
        <div className="modal-overlay">
            {/* O restante do JSX do modal permanece exatamente o mesmo */}
            {/* ... */}
            <div className="modal-content">
                <button className="close-btn" onClick={onClose}>&times;</button>
                <h2>Configurar Agente de Banco de Dados</h2>
                <p>Siga os passos para conectar e configurar seu banco de dados.</p>
                <form onSubmit={handleFinalSubmit}>
                    <fieldset>
                        <legend>Passo 1: Credenciais do Banco</legend>
                        <label>
                            Dialeto do Banco de Dados:
                            <div className="dialect-selector">
                                {dialectOptions.map((option) => (
                                    <button
                                        type="button"
                                        key={option.value}
                                        className={`dialect-option ${dialect === option.value ? 'active' : ''}`}
                                        onClick={() => handleDialectChange(option)}
                                        disabled={isConnecting || isConnected}
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                        </label>
                        <label>
                            String de Conexão:
                            <input
                                type="text"
                                value={connectionString}
                                onChange={(e) => {
                                    setConnectionString(e.target.value);
                                    setIsConnected(false);
                                    setTables([]);
                                }}
                                required
                                disabled={isConnecting || isConnected}
                            />
                        </label>
                        {!isConnected && (
                            <button
                                type="button"
                                className="connect-btn"
                                onClick={handleConnectAndFetchTables}
                                disabled={isConnecting}
                            >
                                {isConnecting ? 'Conectando...' : 'Conectar e Listar Tabelas'}
                            </button>
                        )}
                    </fieldset>

                    <fieldset disabled={!isConnected}>
                        <legend>Passo 2: Descreva as Tabelas para Consulta</legend>
                        {tables.length > 0 ? (
                            tables.map((table, index) => (
                                <div className="table-entry" key={table.table_name}>
                                    <input
                                        type="text"
                                        placeholder="Nome da tabela"
                                        value={table.table_name}
                                        readOnly
                                        className="readonly-input"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Descrição da tabela para a IA"
                                        value={table.description}
                                        onChange={(e) => handleTableChange(index, 'description', e.target.value)}
                                        required
                                    />
                                    <button
                                        type="button"
                                        className="remove-table-btn"
                                        title="Remover Tabela"
                                        onClick={() => handleRemoveTable(index)}
                                    >
                                        &times;
                                    </button>
                                </div>
                            ))
                        ) : (
                            <p className="placeholder-text">
                                {isConnected ? 'Nenhuma tabela encontrada no banco de dados.' : 'Aguardando conexão para listar as tabelas...'}
                            </p>
                        )}
                    </fieldset>

                    {error && <div className="error-message">{error}</div>}

                    {isConnected && (
                        <button type="submit" className="submit-btn" disabled={isSubmitting}>
                            {isSubmitting ? 'Configurando...' : 'Iniciar Chat'}
                        </button>
                    )}
                </form>
            </div>
        </div>
    );
};

export default ConfigModal;