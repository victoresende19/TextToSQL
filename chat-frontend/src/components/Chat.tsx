// src/components/Chat.tsx

import React, { useState, useRef, useEffect, type FormEvent } from 'react';
import './Chat.css';

interface TableInfo {
    table_name: string;
    description: string;
}

interface Message {
    text: string;
    sender: 'user' | 'bot';
}

// NOVO: Define a tipagem das props que o Chat agora recebe
interface ChatProps {
    configuredTables: TableInfo[];
}

const API_URL = import.meta.env.VITE_API_BASE_URL;

const Chat: React.FC<ChatProps> = ({ configuredTables }) => { // ALTERADO: Recebe configuredTables como prop
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // ALTERADO: O useEffect agora apenas monta a mensagem de boas-vindas.
    // Ele não busca mais os dados, pois já os recebeu via props.
    useEffect(() => {
        if (configuredTables.length > 0) {
            const tableNames = configuredTables.map(t => t.table_name).join(', ');
            setMessages([
                {
                    text: `Olá! Estou pronto para responder perguntas sobre as seguintes bases: ${tableNames}.`,
                    sender: 'bot'
                }
            ]);
        } else {
            setMessages([
                {
                    text: "Olá! Parece que nenhuma tabela foi configurada para consulta.",
                    sender: 'bot'
                }
            ]);
        }
    }, [configuredTables]); // Depende de configuredTables para re-renderizar se necessário

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
                <div className="tables-info">
                    {/* ALTERADO: A exibição agora depende diretamente da prop */}
                    {configuredTables.length > 0 ? (
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
                        <p>Nenhuma base configurada.</p>
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
                        disabled={isLoading}
                        autoFocus
                    />
                    <button type="submit" disabled={isLoading}>
                        Enviar
                    </button>
                </form>
            </footer>
        </div>
    );
};

export default Chat;    