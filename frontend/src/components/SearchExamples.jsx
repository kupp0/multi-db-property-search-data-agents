import React from 'react';

const EXAMPLES = [
    "Show me 2-bedroom apartments in Zurich under 3000 CHF",
    "Show me family apartments in Zurich with a nice view up to 10K",
    "Show me cheap studios in Geneva",
    "Show me Lovely Mountain Cabins under 1.5K"
];

<<<<<<< HEAD
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
=======
const SearchExamples = ({ currentQuery, onSelectQuery }) => {
    const [activeExample, setActiveExample] = useState(null);
    const [showInfo, setShowInfo] = useState(false);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    const handleSelect = (example) => {
        onSelectQuery(example.query);
        setActiveExample(example);
        setIsDropdownOpen(false);
    };

    // If the user types something manually that matches an example, highlight it
    const matchedExample = EXAMPLES.find(e => e.query === currentQuery) || activeExample;

    // If current query doesn't match the active example anymore (user edited it), clear active
    React.useEffect(() => {
        if (currentQuery && activeExample && currentQuery !== activeExample.query) {
            setActiveExample(null);
        }
        if (!currentQuery) {
            setActiveExample(null);
        }
    }, [currentQuery, activeExample]);

    return (
        <div className="w-full mb-8 flex items-center gap-4">
            <div className="relative flex-1 group z-30">
                <div className={`absolute -inset-0.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-xl opacity-30 group-hover:opacity-100 transition duration-500 blur ${isDropdownOpen ? 'opacity-100' : ''}`}></div>
                <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="relative w-full text-left px-5 py-4 bg-white rounded-xl shadow-sm flex justify-between items-center transition-all hover:bg-slate-50"
                >
                    <span className={`font-semibold text-lg ${matchedExample ? 'text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600' : 'text-slate-500'}`}>
                        {matchedExample ? matchedExample.label : "Select a search example..."}
                    </span>
                    <ChevronRight className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${isDropdownOpen ? '-rotate-90 text-indigo-500' : 'rotate-90'}`} />
                </button>

                {isDropdownOpen && (
                    <>
                        <div className="fixed inset-0 z-30" onClick={() => setIsDropdownOpen(false)} />
                        <div className="absolute top-full left-0 right-0 mt-3 bg-white/90 backdrop-blur-xl rounded-xl shadow-2xl border border-white/20 ring-1 ring-black/5 z-40 overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300">
                            {EXAMPLES.map((ex) => (
                                <button
                                    key={ex.id}
                                    onClick={() => handleSelect(ex)}
                                    className={`w-full text-left px-5 py-4 text-sm transition-all border-b border-slate-100/50 last:border-0 flex items-center justify-between group/item ${matchedExample?.id === ex.id
                                        ? 'bg-gradient-to-r from-indigo-50 to-purple-50'
                                        : 'hover:bg-gradient-to-r hover:from-indigo-500 hover:to-purple-500'
                                        }`}
                                >
                                    <span className={`font-medium ${matchedExample?.id === ex.id ? 'text-indigo-700' : 'text-slate-600 group-hover/item:text-white'}`}>
                                        {ex.label}
                                    </span>
                                    {matchedExample?.id === ex.id && <ChevronRight className="w-4 h-4 text-indigo-500" />}
                                    {matchedExample?.id !== ex.id && <ChevronRight className="w-4 h-4 text-white opacity-0 group-hover/item:opacity-100 -translate-x-2 group-hover/item:translate-x-0 transition-all" />}
                                </button>
                            ))}
                        </div>
                    </>
                )}
            </div>

            <div className="relative z-30">
                <button
                    onClick={() => setShowInfo(!showInfo)}
                    className={`p-4 rounded-xl transition-all duration-300 shadow-sm ${showInfo
                        ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-indigo-200 shadow-lg scale-110'
                        : 'bg-white text-slate-400 hover:text-indigo-500 hover:shadow-md'
                        }`}
                    title="How it works"
                    aria-label="Show how it works"
                >
                    <Info className="w-6 h-6" />
                </button>

                {showInfo && createPortal(
                    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-8">
                        <div
                            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity duration-500"
                            onClick={() => setShowInfo(false)}
                        />
                        <div className="relative w-full max-w-6xl max-h-[90vh] overflow-y-auto custom-scrollbar bg-white/95 backdrop-blur-2xl rounded-3xl shadow-2xl border border-white/50 animate-in fade-in zoom-in-95 duration-300 ring-1 ring-black/5 flex flex-col">
                            {/* Header with Gradient */}
                            <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-6 sm:p-8 text-white relative overflow-hidden shrink-0">
                                <div className="absolute top-0 right-0 -mt-10 -mr-10 w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
                                <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-64 h-64 bg-black/10 rounded-full blur-3xl"></div>

                                <div className="flex justify-between items-start relative z-10">
                                    <div className="flex items-center gap-4">
                                        <div className="p-3 bg-white/20 backdrop-blur-md rounded-2xl border border-white/30 shadow-inner">
                                            <Lightbulb className="w-8 h-8 text-yellow-300" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-2xl tracking-tight">How it works</h3>
                                            <p className="text-indigo-100 text-base font-medium">Inside the Hybrid Engine</p>
                                        </div>
                                    </div>
                                    <button onClick={() => setShowInfo(false)} className="text-white/70 hover:text-white hover:bg-white/20 p-2 rounded-full transition-all" aria-label="Close info modal">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>
                            </div>

                            {matchedExample ? (
                                <div className="p-6 sm:p-8 space-y-8 overflow-y-auto">
                                    <div>
                                        <h4 className="text-3xl font-bold text-slate-800 mb-4 tracking-tight">{matchedExample.title}</h4>
                                        <div className="text-base font-mono bg-slate-900/5 p-6 rounded-2xl border border-slate-200/50 text-slate-600 shadow-inner">
                                            "{matchedExample.query}"
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                                        <div className="relative">
                                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-500 to-purple-500 rounded-full"></div>
                                            <div className="pl-8">
                                                <h5 className="text-sm font-bold text-indigo-500 uppercase tracking-widest mb-4">What it showcases</h5>
                                                <p className="text-xl text-slate-700 leading-relaxed font-medium">
                                                    {matchedExample.what}
                                                </p>
                                            </div>
                                        </div>

                                        <div>
                                            <h5 className="text-sm font-bold text-purple-500 uppercase tracking-widest mb-4">Why it works</h5>
                                            <div className="space-y-4">
                                                {matchedExample.why.map((item, idx) => (
                                                    <div key={idx} className="flex items-start gap-5 p-5 rounded-2xl bg-white/50 border border-slate-100 shadow-sm hover:shadow-md hover:bg-white hover:border-indigo-100 transition-all duration-300 group/card">
                                                        <div className="mt-1.5 w-2.5 h-2.5 rounded-full bg-gradient-to-r from-teal-400 to-emerald-400 flex-shrink-0 group-hover/card:scale-150 transition-transform" />
                                                        <div>
                                                            <span className="font-bold text-slate-800 text-lg block mb-1 group-hover/card:text-indigo-600 transition-colors">{item.label}</span>
                                                            <span className="text-slate-600 text-base leading-relaxed">{item.desc}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="p-20 text-center">
                                    <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6 text-indigo-400">
                                        <Lightbulb className="w-12 h-12" />
                                    </div>
                                    <p className="text-slate-900 font-bold text-2xl mb-3">Select an example</p>
                                    <p className="text-slate-500 text-lg">Choose a query from the dropdown menu to reveal the magic behind the search engine.</p>
                                </div>
                            )}
                        </div>
                    </div>,
                    document.body
                )}
>>>>>>> origin/palette-ux-improvements-17997682408231380857
            </div>
        </div>
    );
});

export default SearchExamples;
