import React, { useState, useEffect } from 'react';
import { Search, Sparkles, Database, ArrowRight, Loader2, Sun, Moon, Workflow, MessageSquare, History } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ChatInterface from './components/ChatInterface';
import UserHistoryWidget from './components/UserHistoryWidget';

import dataAgentDiagram from './assets/data_agent_diagram.png';
import dataAgentContextDiagram from './assets/data_agent_context_infographic.png';
import alloydbContext from '../../database_artefacts/alloydb_context.json';
import cloudsqlPgContext from '../../database_artefacts/cloudsql_pg_context.json';
import spannerContext from '../../database_artefacts/spanner_context.json';

const contexts = {
    alloydb: alloydbContext,
    cloudsql_pg: cloudsqlPgContext,
    spanner: spannerContext
};

// --- COMPONENTS ---

const SearchExamples = ({ onSelectQuery }) => {
    const examples = [
        "Show me 2-bedroom apartments in Zurich under 3000 CHF",
        "Show me family apartments in Zurich with a nice view up to 16k",
        "Show me cheap studios in Geneva",
        "Show me Lovely Mountain Cabins under 15k"
    ];

    return (
        <div className="mt-8">
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-3 font-medium">Try these examples:</p>
            <div className="flex flex-wrap gap-2">
                {examples.map((ex, i) => (
                    <button
                        key={i}
                        onClick={() => onSelectQuery(ex)}
                        className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-xs text-slate-600 dark:text-slate-300 hover:border-indigo-400 dark:hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all shadow-sm"
                    >
                        {ex}
                    </button>
                ))}
            </div>
        </div>
    );
};

const PropertyCard = ({ listing }) => {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all border border-slate-100 dark:border-slate-700 group">
            <div className="relative h-48 overflow-hidden bg-slate-100 dark:bg-slate-900">
                {listing.image_gcs_uri ? (
                    <img
                        src={listing.image_gcs_uri}
                        alt={listing.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        loading="lazy"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-400">
                        <span className="text-xs">No Image</span>
                    </div>
                )}
                <div className="absolute top-2 right-2 bg-black/50 backdrop-blur-md text-white px-2 py-1 rounded-md text-xs font-bold">
                    CHF {listing.price}
                </div>
            </div>
            <div className="p-4">
                <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-1 line-clamp-1" title={listing.title}>
                    {listing.title}
                </h3>
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-3">
                    <span>{listing.bedrooms} Beds</span>
                    <span>•</span>
                    <span>{listing.city}, {listing.canton}</span>
                    <span className="hidden sm:inline">• {listing.country}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                    {listing.description}
                </p>
            </div>
        </div>
    );
};

// --- MAIN APP COMPONENT ---

function App() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [generatedSql, setGeneratedSql] = useState('');
    const [nlAnswer, setNlAnswer] = useState('');
    const [systemDetails, setSystemDetails] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [darkMode, setDarkMode] = useState(true);
    const [showArchitecture, setShowArchitecture] = useState(false);
    const [showChat, setShowChat] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [isOutputExpanded, setIsOutputExpanded] = useState(false);
    const [selectedBackend, setSelectedBackend] = useState('alloydb');

    // Toggle Dark Mode
    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }, [darkMode]);

    const handleSearch = async (e) => {
        e?.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        setResults([]);
        setGeneratedSql('');
        setNlAnswer('');
        setIsOutputExpanded(false); // Reset expansion on new search

        try {
            // Call the backend API
            // Note: We use a relative URL because Vite proxies /api to the backend
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, backend: selectedBackend }),
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.statusText}`);
            }

            const data = await response.json();
            setResults(data.listings || []);
            setGeneratedSql(data.sql || '');
            setNlAnswer(data.nl_answer || '');
            setSystemDetails(data.details || {});

            if (data.listings?.length === 0 && !data.sql) {
                setError("No results found. Try a different query.");
            }
        } catch (err) {
            console.error("Search failed:", err);
            setError(err.message || "An unexpected error occurred.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#1a1b2e] to-slate-950' : 'bg-slate-50'}`}>

            {/* ARCHITECTURE MODAL */}
            {showArchitecture && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setShowArchitecture(false)}>
                    <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl border border-slate-200 dark:border-slate-700 relative" onClick={e => e.stopPropagation()}>
                        <button onClick={() => setShowArchitecture(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                            ✕
                        </button>
                        <h2 className="text-2xl font-bold mb-6 text-slate-800 dark:text-white flex items-center gap-2">
                            <Workflow className="w-6 h-6 text-indigo-500" />
                            System Architecture
                        </h2>
                        <div className="flex flex-col items-center gap-8">
                            {/* Architecture Diagram */}
                            <div className="w-full">
                                <h3 className="text-lg font-semibold mb-3 text-slate-700 dark:text-slate-300">Architecture Overview</h3>
                                <img
                                    src={dataAgentDiagram}
                                    alt="Architecture Diagram"
                                    className="w-full h-auto rounded-lg shadow-lg border border-slate-200 dark:border-slate-700"
                                />
                            </div>

                            {/* Context Diagram */}
                            <div className="w-full">
                                <h3 className="text-lg font-semibold mb-3 text-slate-700 dark:text-slate-300">Data Agent Context</h3>
                                <img
                                    src={dataAgentContextDiagram}
                                    alt="Data Agent Context Diagram"
                                    className="w-full h-auto rounded-lg shadow-lg border border-slate-200 dark:border-slate-700"
                                />
                            </div>


                        </div>
                    </div>
                </div>
            )}

            <UserHistoryWidget isOpen={showHistory} onClose={() => setShowHistory(false)} selectedBackend={selectedBackend} />

            {/* FLOATING CHAT BUTTON */}
            <button
                onClick={() => setShowChat(!showChat)}
                className={`fixed bottom-6 right-6 z-50 p-4 rounded-full shadow-2xl transition-all duration-300 hover:scale-110 active:scale-95 flex items-center justify-center ${showChat ? 'bg-slate-800 text-white rotate-90' : 'bg-indigo-600 hover:bg-indigo-700 text-white'}`}
                title={showChat ? "Close Chat" : "Open AI Agent Chat"}
            >
                {showChat ? <ArrowRight className="w-6 h-6" /> : <MessageSquare className="w-6 h-6" />}
            </button>

            {/* CHAT INTERFACE SIDE PANEL */}
            <div className={`fixed bottom-24 right-6 z-40 w-[90vw] sm:w-[400px] h-[600px] max-h-[calc(100vh-120px)] transition-all duration-300 transform origin-bottom-right ${showChat ? 'scale-100 opacity-100 translate-y-0' : 'scale-95 opacity-0 translate-y-10 pointer-events-none'}`}>
                <div className="w-full h-full bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-700 flex flex-col">
                    <ChatInterface
                        selectedBackend={selectedBackend}
                        onClose={() => setShowChat(false)}
                        onResultsFound={(listings, usedPrompt, toolDetails) => {
                            setResults(listings);
                            setQuery(usedPrompt); // Update search bar with the ACTUAL prompt used

                            if (toolDetails) {
                                // Map tool details to system output state
                                // The tool returns keys like: generatedQuery, naturalLanguageAnswer, intentExplanation, queryResult

                                const generatedSql = toolDetails.generatedQuery || toolDetails.queryResult?.query || '';
                                const explanation = toolDetails.intentExplanation || '';
                                const totalRowCount = toolDetails.queryResult?.totalRowCount || "0";
                                const rows = toolDetails.queryResult?.rows || [];
                                const cols = toolDetails.queryResult?.columns || [];
                                const nlAnswer = toolDetails.naturalLanguageAnswer || '';

                                // Construct display SQL similar to backend
                                let displaySql = `// GEMINI DATA AGENT CALL\n// Tool Prompt: ${usedPrompt}\n// Generated SQL: ${generatedSql}\n// Answer: ${nlAnswer}`;
                                if (explanation) {
                                    displaySql += `\n// Explanation: ${explanation}`;
                                }

                                setGeneratedSql(displaySql);
                                setNlAnswer(nlAnswer);

                                setSystemDetails({
                                    generated_query: generatedSql,
                                    intent_explanation: explanation,
                                    total_row_count: totalRowCount,
                                    query_result_preview: {
                                        columns: cols,
                                        rows: rows.slice(0, 3) // Preview first 3 rows
                                    }
                                });
                            } else {
                                // Flush system output if no tool was used
                                setGeneratedSql('');
                                setNlAnswer('');
                                setSystemDetails({});
                            }

                            // Keep chat open for smooth interaction, or close if preferred.
                            // For now, keeping it open allows for follow-up questions.
                        }}
                    />
                </div>
            </div>

            {/* TOP HEADER BAR */}
            <header className="w-full px-6 py-4 flex justify-between items-center relative z-20">
                <div className="flex items-center gap-2">
                    {/* Placeholder for logo if needed later, currently empty based on feedback */}
                </div>
                <div className="flex items-center gap-3">
                    <button onClick={() => setShowArchitecture(true)} className="px-4 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all text-sm font-medium flex items-center gap-2 shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-500 outline-none">
                        <Workflow className="w-4 h-4" /> Architecture
                    </button>
                    <button onClick={() => setShowHistory(true)} className="px-4 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all text-sm font-medium flex items-center gap-2 shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-500 outline-none">
                        <History className="w-4 h-4" /> History
                    </button>
                    <button onClick={() => setDarkMode(!darkMode)} aria-label="Toggle dark mode" className="p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-500 outline-none">
                        {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                    </button>
                </div>
            </header>

            <main className="container mx-auto px-4 py-12 max-w-5xl relative z-10">

                {/* SEARCH PANEL CARD */}
                <div className="mb-12 relative overflow-hidden group">

                    {/* HEADER */}
                    <div className="flex flex-col items-center mb-8 text-center relative z-10">
                        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white mb-3 tracking-tight">
                            Swiss Property Search 🇨🇭
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed text-base">
                            Powered by Conversational Data Agents API connected to AlloyDB, Spanner, and Cloud SQL.
                        </p>
                    </div>

                    {/* SEARCH BAR */}
                    <div className="max-w-3xl mx-auto relative z-10">
                        {/* DATABASE TOGGLE */}
                        <div className="flex flex-wrap items-center justify-center gap-1 bg-slate-100/50 dark:bg-slate-800/50 p-1.5 rounded-xl border border-slate-200/50 dark:border-slate-700/50 mb-6 backdrop-blur-sm mx-auto w-fit">
                            {[
                                { id: 'alloydb', label: 'AlloyDB' },
                                { id: 'spanner', label: 'Spanner' },
                                { id: 'cloudsql_pg', label: 'Cloud SQL' }
                            ].map(db => (
                                <button
                                    key={db.id}
                                    onClick={() => setSelectedBackend(db.id)}
                                    className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${selectedBackend === db.id ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-slate-600' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'}`}
                                >
                                    {db.label}
                                </button>
                            ))}
                        </div>

                        <form onSubmit={handleSearch} className="relative group/search mb-8">
                            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl blur-lg opacity-50 group-hover/search:opacity-100 transition duration-500"></div>
                            <div className="relative flex items-center bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200/80 dark:border-slate-700/80 overflow-hidden p-1">
                                <div className="pl-5 text-slate-400">
                                    <Search className="w-5 h-5" />
                                </div>
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder='Describe your dream home, for example: "3-bedroom apartment in Zurich"...'
                                    aria-label="Search properties"
                                    className="w-full px-4 py-4 bg-transparent border-none focus:ring-0 text-slate-800 dark:text-slate-100 placeholder-slate-400 text-base"
                                />
                                <button
                                    type="submit"
                                    disabled={loading || !query.trim()}
                                    className="m-1 px-6 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-md"
                                >
                                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="hidden sm:inline">Search</span>}
                                    {!loading && <ArrowRight className="w-4 h-4" />}
                                </button>
                            </div>
                        </form>
                        <SearchExamples onSelectQuery={setQuery} />
                    </div>
                </div>

                {/* ERROR MESSAGE */}
                {error && (
                    <div className="max-w-2xl mx-auto mb-8 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-600 dark:text-red-400 text-sm text-center animate-in fade-in slide-in-from-top-2">
                        {error}
                    </div>
                )}

                {/* RESULTS SECTION */}
                {(results.length > 0 || generatedSql) && (
                    <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">

                        {/* SYSTEM OUTPUT (SQL + Answer) */}
                        {generatedSql && (
                            <div className="w-full mb-12">
                                <div
                                    className={`bg-slate-900 rounded-xl shadow-2xl border border-slate-800 transition-all duration-300 cursor-pointer group ${isOutputExpanded ? 'max-h-[800px] overflow-y-auto' : 'max-h-[160px] overflow-hidden'}`}
                                    onClick={() => setIsOutputExpanded(!isOutputExpanded)}
                                >
                                    <div className="bg-slate-950/50 px-4 py-3 text-xs font-mono font-bold text-slate-400 flex justify-between items-center border-b border-slate-800 sticky top-0 z-10 backdrop-blur-md">
                                        <div className="flex items-center gap-2">
                                            <Database className="w-3 h-3 text-indigo-400" />
                                            <span>SYSTEM OUTPUT</span>
                                        </div>
                                        <span className="text-[10px] bg-slate-800 px-2 py-1 rounded text-slate-500 group-hover:text-slate-300 transition-colors">
                                            {isOutputExpanded ? 'CLICK TO COLLAPSE' : 'CLICK TO EXPAND'}
                                        </span>
                                    </div>
                                    <div className="p-6 space-y-6">
                                        {/* INTENT EXPLANATION */}
                                        {systemDetails?.intent_explanation && (
                                            <div>
                                                <h4 className="text-xs font-bold text-indigo-400 mb-2 uppercase tracking-wider">Intent Explanation</h4>
                                                <p className="text-sm text-slate-300 leading-relaxed font-mono bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                                                    {systemDetails.intent_explanation}
                                                </p>
                                            </div>
                                        )}

                                        {/* APPLIED TEMPLATES & FACETS */}
                                        {(() => {
                                            const explanation = systemDetails?.intent_explanation || nlAnswer || '';
                                            if (!explanation) return null;

                                            // Extract template and facet numbers (1-based in text, 0-based for array access)
                                            const templateMatches = [...explanation.matchAll(/Template\s+(\d+)/gi)];
                                            const facetMatches = [...explanation.matchAll(/(?:Fragment|Facet)\s+(\d+)/gi)];

                                            // Templates seem to be 1-based in the LLM output
                                            const dataAgentContext = contexts[selectedBackend];
                                            const matchedTemplates = [...new Set(templateMatches.map(m => parseInt(m[1], 10) - 1))].filter(idx => idx >= 0 && idx < dataAgentContext.templates.length);
                                            const facetsList = dataAgentContext.facets || [];
                                            // Facets seem to be 1-based in the LLM output
                                            const matchedFacets = [...new Set(facetMatches.map(m => parseInt(m[1], 10) - 1))].filter(idx => idx >= 0 && idx < facetsList.length);

                                            if (matchedTemplates.length === 0 && matchedFacets.length === 0) return null;

                                            return (
                                                <div>
                                                    <h4 className="text-xs font-bold text-amber-400 mb-2 uppercase tracking-wider">Applied Templates & Facets</h4>
                                                    <div className="space-y-3">
                                                        {matchedTemplates.map(idx => {
                                                            const dataAgentContext = contexts[selectedBackend];
                                                            const template = dataAgentContext.templates[idx];
                                                            return (
                                                                <div key={`template-${idx}`} className="bg-slate-950/50 p-3 rounded-lg border border-amber-900/30">
                                                                    <div className="text-xs font-bold text-amber-300 mb-1">Template {idx + 1}: {template.intent}</div>
                                                                    <div className="text-xs font-mono text-slate-400 bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto whitespace-pre-wrap">
                                                                        {template.parameterized?.parameterized_sql || template.sql}
                                                                    </div>
                                                                </div>
                                                            );
                                                        })}
                                                        {matchedFacets.map(idx => {
                                                            const dataAgentContext = contexts[selectedBackend];
                                                            const facetsList = dataAgentContext.facets || [];
                                                            const facet = facetsList[idx];
                                                            if (!facet) return null;
                                                            const snippet = facet.parameterized?.parameterized_sql_snippet || facet.parameterized?.parameterized_facet || facet.sql_snippet || facet.facet;
                                                            return (
                                                                <div key={`facet-${idx}`} className="bg-slate-950/50 p-3 rounded-lg border border-orange-900/30">
                                                                    <div className="text-xs font-bold text-orange-300 mb-1">Facet {idx + 1}: {facet.intent}</div>
                                                                    <div className="text-xs font-mono text-slate-400 bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto whitespace-pre-wrap">
                                                                        {snippet}
                                                                    </div>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            );
                                        })()}

                                        {/* GENERATED SQL */}
                                        <div>
                                            <h4 className="text-xs font-bold text-emerald-400 mb-2 uppercase tracking-wider">Generated SQL</h4>
                                            <div className="font-mono text-sm overflow-x-auto bg-slate-950/50 p-3 rounded-lg border border-slate-800 max-h-64 overflow-y-auto custom-scrollbar">
                                                <ReactMarkdown
                                                    components={{
                                                        code({ className, children, ...props }) {
                                                            return (
                                                                <code className={`${className} text-emerald-300 bg-transparent`} {...props}>
                                                                    {children}
                                                                </code>
                                                            );
                                                        }
                                                    }}
                                                >
                                                    {`\`\`\`sql\n${(() => {
                                                        const sql = systemDetails?.generated_query || generatedSql;
                                                        // Simple SQL formatting
                                                        return sql
                                                            .replace(/\s+/g, ' ') // Normalize whitespace
                                                            .replace(/\s+(SELECT|FROM|WHERE|AND|ORDER BY|LIMIT|GROUP BY|HAVING|LEFT JOIN|RIGHT JOIN|INNER JOIN|OUTER JOIN)\s+/gi, '\n$1 ')
                                                            .replace(/;\s*$/, ';\n') // Newline after semicolon
                                                            .trim();
                                                    })()}\n\`\`\``}
                                                </ReactMarkdown>
                                            </div>
                                        </div>

                                        {/* QUERY RESULT PREVIEW */}
                                        {systemDetails?.query_result_preview && (
                                            <div>
                                                <div className="flex items-center justify-between mb-2">
                                                    <h4 className="text-xs font-bold text-blue-400 uppercase tracking-wider">Query Result Preview</h4>
                                                    <span className="text-[10px] text-slate-500">Total Rows: {systemDetails.total_row_count}</span>
                                                </div>
                                                <div className="overflow-x-auto bg-slate-950/50 rounded-lg border border-slate-800">
                                                    <table className="w-full text-left text-xs font-mono text-slate-400">
                                                        <thead className="bg-slate-900 text-slate-300">
                                                            <tr>
                                                                {systemDetails.query_result_preview.columns.map((col, i) => (
                                                                    <th key={i} className="px-3 py-2 border-b border-slate-800 whitespace-nowrap">{col.name}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {systemDetails.query_result_preview.rows.map((row, i) => (
                                                                <tr key={i} className="border-b border-slate-800 last:border-0 hover:bg-slate-900/50">
                                                                    {row.values.map((val, j) => (
                                                                        <td key={j} className="px-3 py-2 whitespace-nowrap max-w-[200px] truncate" title={val.value}>
                                                                            {val.value}
                                                                        </td>
                                                                    ))}
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        )}

                                        {/* RAW ANSWER */}
                                        {nlAnswer && (
                                            <div>
                                                <h4 className="text-xs font-bold text-purple-400 mb-2 uppercase tracking-wider">Natural Language Answer</h4>
                                                <p className="text-sm text-slate-300 leading-relaxed font-mono bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                                                    {nlAnswer}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* LISTINGS GRID */}
                        {results.length > 0 && (
                            <>
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                                        Found {results.length} Properties
                                    </h2>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {results.map((listing, index) => (
                                        <PropertyCard key={index} listing={listing} />
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;