import { Bot, MessageCircle, Send, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, KeyboardEvent } from 'react';
import { askMihimura } from '../services/api';
import './ChatWidget.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
}

interface ChatWidgetProps {
  province: string;
}

export default function ChatWidget({ province }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      text: 'Hello! I am the Mihimura AI advisor. Ask me about weather risk, crop health, pests, irrigation, or field actions.',
      sender: 'agent',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const question = inputValue.trim();
    if (!question || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      text: question,
      sender: 'user',
    };

    setMessages((current) => [...current, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await askMihimura(question, province);
      const extra = response.recommended_action ? ` ${response.recommended_action}` : '';
      setMessages((current) => [
        ...current,
        {
          id: `agent-${Date.now()}`,
          text: `${response.summary}${extra}`,
          sender: 'agent',
        },
      ]);
    } catch (error) {
      console.error('Unable to reach Mihimura AI.', error);
      setMessages((current) => [
        ...current,
        {
          id: `error-${Date.now()}`,
          text: 'The AI service is currently unavailable. Start the FastAPI backend on port 8000 and try again.',
          sender: 'agent',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        className={`chat-fab${isOpen ? ' hidden' : ''}`}
        onClick={() => setIsOpen(true)}
      >
        <MessageCircle size={18} />
        Ask Mihimura AI
      </button>

      <section className={`chat-window${isOpen ? ' open' : ''}`} aria-label="Mihimura AI assistant">
        <header className="chat-header">
          <div className="chat-header-title">
            <span className="chat-avatar"><Bot size={21} /></span>
            <div>
              <h3>Mihimura AI</h3>
              <p>{province} Province context</p>
            </div>
          </div>
          <button type="button" className="chat-close-btn" onClick={() => setIsOpen(false)} aria-label="Close AI chat">
            <X size={20} />
          </button>
        </header>

        <div className="chat-body">
          {messages.map((message) => (
            <div key={message.id} className={`chat-message-wrapper ${message.sender}`}>
              <div className={`chat-message ${message.sender}`}>{message.text}</div>
            </div>
          ))}
          {isLoading && (
            <div className="chat-message-wrapper agent">
              <div className="chat-message agent loading-dots" aria-label="AI is responding">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-quick-prompts">
          {['Can I fertilize tomorrow?', 'Show the main risk', 'What should I inspect?'].map((prompt) => (
            <button key={prompt} type="button" onClick={() => setInputValue(prompt)}>{prompt}</button>
          ))}
        </div>

        <div className="chat-input-area">
          <input
            type="text"
            placeholder="Ask about crops, weather or actions..."
            value={inputValue}
            onChange={(event: ChangeEvent<HTMLInputElement>) => setInputValue(event.target.value)}
            onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
              if (event.key === 'Enter') void handleSend();
            }}
            disabled={isLoading}
          />
          <button type="button" className="chat-send-btn" onClick={() => void handleSend()} disabled={isLoading || !inputValue.trim()} aria-label="Send message">
            <Send size={17} />
          </button>
        </div>
      </section>
    </>
  );
}
