import React from 'react';

const EXAMPLES = [
    "Show me 2-bedroom apartments in Zurich under 3000 CHF",
    "Show me family apartments in Zurich with a nice view up to 10K",
    "Show me cheap studios in Geneva",
    "Show me Lovely Mountain Cabins under 1.5K"
];

const SearchExamples = React.memo(({ onSelectQuery }) => {
    return (
        <div className="w-full mt-4 flex flex-col items-start gap-3">
            <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                Try these examples:
            </span>
            <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((query, index) => (
                    <button
                        key={index}
                        onClick={() => onSelectQuery(query)}
                        className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 transition-all shadow-sm"
                    >
                        {query}
                    </button>
                ))}
            </div>
        </div>
    );
});

export default SearchExamples;
