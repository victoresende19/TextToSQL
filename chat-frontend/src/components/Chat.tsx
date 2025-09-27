// src/Chat.tsx

import React, { useState, useRef, useEffect, type FormEvent } from 'react';
import './Chat.css';

// ### NOVA INTERFACE ###
// Para tipar os dados que virão do novo endpoint /tables
interface TableInfo {
    table_name: string;
    description: string;
}

interface Message {
    text: string;
    sender: 'user' | 'bot';
}

const API_URL = import.meta.env.VITE_API_BASE_URL;;

const Chat: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // ### NOVOS ESTADOS ###
    const [configuredTables, setConfiguredTables] = useState<TableInfo[]>([]);
    const [initialLoading, setInitialLoading] = useState(true); // Para o carregamento inicial das tabelas

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Efeito para carregar as tabelas configuradas ao iniciar o componente
    useEffect(() => {
        const fetchTables = async () => {
            try {
                const response = await fetch(`${API_URL}/configure_agent`);
                if (!response.ok) {
                    throw new Error("Agente não configurado no backend.");
                }
                const data: TableInfo[] = await response.json();
                setConfiguredTables(data);

                // Cria a mensagem de boas-vindas com a lista de tabelas
                const tableNames = data.map(t => t.table_name).join(', ');
                setMessages([
                    {
                        text: `Olá! Estou pronto para responder perguntas sobre as seguintes bases: ${tableNames}.`,
                        sender: 'bot'
                    }
                ]);

            } catch (error) {
                console.error("Erro ao buscar tabelas:", error);
                setMessages([
                    {
                        text: "Não consegui carregar a configuração das bases de dados. Verifique se o backend foi configurado corretamente.",
                        sender: 'bot'
                    }
                ]);
            } finally {
                setInitialLoading(false);
            }
        };

        fetchTables();
    }, []); // Array vazio garante que rode apenas uma vez

    // Efeito para rolar para a última mensagem
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSendMessage = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = { text: input, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch(`${API_URL}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: input }),
            });

            if (!response.ok) throw new Error(`Erro na API: ${response.statusText}`);
            const data = await response.json();
            const botMessage: Message = { text: data.answer, sender: 'bot' };
            setMessages(prev => [...prev, botMessage]);
        } catch (error) {
            console.error("Falha ao comunicar com o backend:", error);
            const errorMessage: Message = {
                text: "Desculpe, não consegui processar sua pergunta. Tente novamente.",
                sender: 'bot'
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <header className="chat-header">
                <h1>Converse com a IA</h1>
                {/* ### NOVA SEÇÃO: LISTA DE TABELAS ### */}
                <div className="tables-info">
                    {initialLoading ? (
                        <p>Carregando configuração...</p>
                    ) : configuredTables.length > 0 ? (
                        <>
                            <span>Consultando:</span>
                            <div className="tables-list">
                                {configuredTables.map(table => (
                                    <span key={table.table_name} className="table-tag" title={table.description}>
                                        {table.table_name}
                                    </span>
                                ))}
                            </div>
                        </>
                    ) : (
                        <p>Bases não configuradas.</p>
                    )}
                </div>
            </header>

            <main className="chat-messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        <p>{msg.text}</p>
                    </div>
                ))}
                {isLoading && (
                    <div className="message bot typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </main>

            <footer className="chat-input-form">
                <form onSubmit={handleSendMessage}>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Digite sua pergunta aqui..."
                        disabled={isLoading || initialLoading} // Desabilita enquanto carrega as tabelas
                        autoFocus
                    />
                    <button type="submit" disabled={isLoading || initialLoading}>
                        Enviar
                    </button>
                </form>
            </footer>
        </div>
    );
};

export default Chat;