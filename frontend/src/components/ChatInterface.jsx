import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Sparkles, X } from 'lucide-react';


const ChatInterface = ({ selectedBackend, onClose, onResultsFound }) => {
    const [messages, setMessages] = useState([
        { role: 'model', text: "Hello! I'm your AI real estate assistant. I can help you find properties using natural language. Try asking 'Find me a modern apartment in Zurich' or 'Show me 3 bedroom houses near the lake'." }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        // Generate a unique session ID when the component mounts
        setSessionId(`session-${Math.random().toString(36).substring(2, 15)}`);
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = { role: 'user', text: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch('/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage.text, session_id: sessionId, backend: selectedBackend }),
            });

            if (!response.ok) {
                throw new Error(`Error: ${response.statusText}`);
            }

            const data = await response.json();
            let responseText = data.response;
            let properties = [];

            // Parse JSON properties block
            const jsonRegex = /```json_properties\n([\s\S]*?)\n```/;
            const match = responseText.match(jsonRegex);

            if (match) {
                try {
                    properties = JSON.parse(match[1]);
                    // Transform gs:// and https://storage.googleapis.com/ URIs to /api/image URLs
                    properties = properties.map(prop => {
                        if (prop.image_gcs_uri) {
                            if (prop.image_gcs_uri.startsWith('gs://') || prop.image_gcs_uri.startsWith('https://storage.googleapis.com/')) {
                                return {
                                    ...prop,
                                    image_gcs_uri: `/api/image?gcs_uri=${encodeURIComponent(prop.image_gcs_uri)}`
                                };
                            }
                        }
                        return prop;
                    });

                    // Remove the JSON block from the text to display
                    responseText = responseText.replace(match[0], '').trim();
                } catch (e) {
                    console.error("Failed to parse properties JSON:", e);
                }
            }

            const botMessage = { role: 'model', text: responseText, properties };
            setMessages(prev => [...prev, botMessage]);

            // Notify parent component about found properties AND system details
            if (onResultsFound) {
                // We pass properties (if any), the user message (or better, the USED prompt), and tool details
                onResultsFound(
                    properties,
                    data.used_prompt || userMessage.text, // Use the actual prompt sent to tool if available
                    data.tool_details // Pass the raw tool output (SQL, explanation, etc.)
                );
            }
        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, { role: 'model', text: "Sorry, I encountered an error processing your request. Please try again." }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg">
                        <Bot className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-900 dark:text-white">AI Agent</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                            Online • Powered by Gemini 3
                        </p>
                    </div>
                </div>
                {onClose && (
                    <button onClick={onClose} aria-label="Close chat" className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors text-slate-500 dark:text-slate-400">
                        <X className="w-5 h-5" />
                    </button>
                )}
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div className={`flex max-w-[85%] gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-indigo-500 text-white' : 'bg-teal-500 text-white'}`}>
                                {msg.role === 'user' ? <User className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
                            </div>
                            <div className={`p-4 rounded-2xl shadow-sm ${msg.role === 'user'
                                ? 'bg-indigo-500 text-white rounded-tr-none'
                                : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-100 dark:border-slate-700 rounded-tl-none'
                                }`}>
                                <p className="whitespace-pre-wrap leading-relaxed text-sm">{msg.text}</p>
                            </div>
                        </div>


                    </div>
                ))}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="flex max-w-[80%] gap-3">
                            <div className="w-8 h-8 rounded-full bg-teal-500 text-white flex items-center justify-center flex-shrink-0">
                                <Sparkles className="w-5 h-5" />
                            </div>
                            <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl rounded-tl-none border border-slate-100 dark:border-slate-700 flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                                <span className="text-sm text-slate-400">Thinking...</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                        placeholder="Ask about properties..."
                        aria-label="Chat message"
                        className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all dark:text-white placeholder-slate-400"
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        aria-label="Send message"
                        className="bg-indigo-600 hover:bg-indigo-700 text-white p-3 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/20"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
