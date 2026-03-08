import React, { useState, useEffect } from 'react';
import { X, Database, Filter, RefreshCw, Loader2 } from 'lucide-react';

const UserHistoryWidget = ({ isOpen, onClose, selectedBackend }) => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedRows, setExpandedRows] = useState(new Set());

    const toggleRow = (index) => {
        const newExpanded = new Set(expandedRows);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            newExpanded.add(index);
        }
        setExpandedRows(newExpanded);
    };

    const [filters, setFilters] = useState([{ column: 'user_prompt', operator: 'ILIKE', value: '' }]);

    const columns = [
        { value: 'user_prompt', label: 'User Prompt' },
        { value: 'query_template_used', label: 'Template Used' },
        { value: 'query_template_id', label: 'Template ID' },
        { value: 'query_explanation', label: 'Explanation' }
    ];

    const operators = [
        { value: 'ILIKE', label: 'contains' },
        { value: '=', label: 'equals' },
        { value: '!=', label: 'is not' },
    ];

    const addFilter = () => {
        setFilters([...filters, { column: 'user_prompt', operator: 'ILIKE', value: '', logic: 'AND' }]);
    };

    const removeFilter = (index) => {
        const newFilters = filters.filter((_, i) => i !== index);
        setFilters(newFilters.length ? newFilters : [{ column: 'user_prompt', operator: 'ILIKE', value: '' }]);
    };

    const updateFilter = (index, field, value) => {
        const newFilters = [...filters];
        newFilters[index] = { ...newFilters[index], [field]: value };
        setFilters(newFilters);
    };

    const handleRunQuery = () => {
        fetchHistory();
    };

    const fetchHistory = async () => {
        setLoading(true);
        setError(null);
        try {
            // Send structured filters instead of raw SQL
            // Filter out empty values
            const activeFilters = filters.filter(f => f.value && f.value.trim() !== '');

            const response = await fetch('/api/history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filters: activeFilters, backend: selectedBackend }),
            });
            if (!response.ok) throw new Error('Failed to fetch history');
            const data = await response.json();
            setHistory(data.rows || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchHistory();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, selectedBackend]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose}>
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col border border-slate-200 dark:border-slate-700 overflow-hidden relative" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                    <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <Database className="w-5 h-5 text-indigo-500" />
                        User Prompt History
                    </h3>
                    <button
                        aria-label="Close History"
                        onClick={(e) => {
                            e.stopPropagation();
                            onClose();
                        }}
                        className="relative z-50 p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-500 dark:text-slate-400"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Controls */}
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-3">
                    <div className="flex flex-col gap-2">
                        {filters.map((filter, index) => (
                            <div key={index} className="flex items-center gap-2 flex-wrap">
                                {index > 0 && (
                                    <select
                                        value={filter.logic}
                                        onChange={(e) => updateFilter(index, 'logic', e.target.value)}
                                        className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-2 py-1 text-xs font-bold text-indigo-500"
                                    >
                                        <option value="AND">AND</option>
                                        <option value="OR">OR</option>
                                    </select>
                                )}
                                {index === 0 && <span className="text-xs font-bold text-slate-400 w-[50px]">WHERE</span>}

                                <select
                                    value={filter.column}
                                    onChange={(e) => updateFilter(index, 'column', e.target.value)}
                                    className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-3 py-2 text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500/50"
                                >
                                    {columns.map(col => (
                                        <option key={col.value} value={col.value}>{col.label}</option>
                                    ))}
                                </select>

                                <select
                                    value={filter.operator}
                                    onChange={(e) => updateFilter(index, 'operator', e.target.value)}
                                    className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-3 py-2 text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500/50"
                                >
                                    {operators.map(op => (
                                        <option key={op.value} value={op.value}>{op.label}</option>
                                    ))}
                                </select>

                                <input
                                    type="text"
                                    aria-label="Filter Value"
                                    value={filter.value}
                                    onChange={(e) => updateFilter(index, 'value', e.target.value)}
                                    placeholder="Value..."
                                    className="flex-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-3 py-2 text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500/50 min-w-[150px]"
                                    onKeyDown={(e) => e.key === 'Enter' && handleRunQuery()}
                                />

                                <button
                                    aria-label="Remove Filter"
                                    onClick={() => removeFilter(index)}
                                    className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-400 hover:text-red-500 rounded transition-colors"
                                    title="Remove filter"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>

                    <div className="flex justify-between items-center mt-2">
                        <button
                            onClick={addFilter}
                            className="text-xs font-medium text-indigo-500 hover:text-indigo-600 flex items-center gap-1"
                        >
                            + Add Filter
                        </button>

                        <button
                            onClick={handleRunQuery}
                            disabled={loading}
                            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 shadow-sm"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                            Run Query
                        </button>
                    </div>
                </div>

                {/* Table Content */}
                <div className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-950 relative">
                    {error && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm text-center border-b border-red-200 dark:border-red-800">
                            {error}
                        </div>
                    )}

                    <table className="w-full text-left text-sm border-collapse">
                        <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0 z-10 shadow-sm">
                            <tr>
                                <th className="px-4 py-3 font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap w-1/4">User Prompt</th>
                                <th className="px-4 py-3 font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap w-1/6">Template Used</th>
                                <th className="px-4 py-3 font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap w-24">ID</th>
                                <th className="px-4 py-3 font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap">Explanation</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                            {history.map((row, i) => {
                                const isExpanded = expandedRows.has(i);
                                return (
                                    <tr
                                        key={i}
                                        onClick={() => toggleRow(i)}
                                        className={`hover:bg-white dark:hover:bg-slate-900 transition-colors cursor-pointer ${isExpanded ? 'bg-white dark:bg-slate-900' : ''}`}
                                    >
                                        <td className={`px-4 py-3 text-slate-700 dark:text-slate-300 align-top ${isExpanded ? 'whitespace-pre-wrap break-words' : 'max-w-xs truncate'}`} title={!isExpanded ? row.user_prompt : ''}>
                                            {row.user_prompt}
                                        </td>
                                        <td className={`px-4 py-3 text-slate-600 dark:text-slate-400 align-top ${isExpanded ? 'whitespace-pre-wrap break-words' : 'max-w-xs truncate'}`} title={!isExpanded ? String(row.query_template_used) : ''}>
                                            {row.query_template_used === true ? 'true' : row.query_template_used === false ? 'false' : '-'}
                                        </td>
                                        <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-500 align-top">
                                            {row.query_template_id}
                                        </td>
                                        <td className={`px-4 py-3 text-slate-600 dark:text-slate-400 align-top ${isExpanded ? 'whitespace-pre-wrap break-words' : 'max-w-md truncate'}`} title={!isExpanded ? row.query_explanation : ''}>
                                            {row.query_explanation}
                                        </td>
                                    </tr>
                                );
                            })}
                            {history.length === 0 && !loading && (
                                <tr>
                                    <td colSpan={4} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                                        No history found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="p-2 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-500 text-center">
                    Showing up to 1000 rows
                </div>
            </div>
        </div>
    );
};

export default UserHistoryWidget;
