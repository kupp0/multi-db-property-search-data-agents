import React, { useState } from 'react';
import { X, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import dataAgentArch from '../assets/data_agent_diagram.png';
import alloydbDeepDive from '../assets/alloydb_ai_nl_architecture.png';

const ArchitectureModal = ({ isOpen, onClose }) => {
    const [currentSlide, setCurrentSlide] = useState(0);

    if (!isOpen) return null;

    const slides = [
        {
            title: "Data Agent Architecture",
            image: dataAgentArch,
            description: "High-level overview of the Data Agent architecture."
        },
        {
            title: "AlloyDB NL Deep Dive",
            image: alloydbDeepDive,
            description: "Detailed view of the AlloyDB Natural Language integration."
        }
    ];

    const nextSlide = () => {
        setCurrentSlide((prev) => (prev + 1) % slides.length);
    };

    const prevSlide = () => {
        setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col border border-slate-200 dark:border-slate-700 overflow-hidden">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-slate-800">
                    <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <Info className="w-5 h-5 text-indigo-500" />
                        System Architecture
                    </h3>
                    <button
                        aria-label="Close Modal"
                        onClick={onClose}
                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-500 dark:text-slate-400"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto p-6 bg-slate-50 dark:bg-slate-950/50 flex flex-col items-center justify-center relative">
                    <div className="relative w-full h-full flex items-center justify-center">
                        <img
                            src={slides[currentSlide].image}
                            alt={slides[currentSlide].title}
                            className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-lg border border-slate-200 dark:border-slate-700"
                        />
                    </div>

                    <div className="mt-4 text-center">
                        <h4 className="text-lg font-semibold text-slate-900 dark:text-white">{slides[currentSlide].title}</h4>
                        <p className="text-slate-500 dark:text-slate-400 text-sm">{slides[currentSlide].description}</p>
                    </div>

                    {/* Navigation Buttons */}
                    <button
                        aria-label="Previous Slide"
                        onClick={prevSlide}
                        className="absolute left-0 top-1/2 -translate-y-1/2 p-3 bg-white/80 dark:bg-slate-800/80 backdrop-blur hover:bg-white dark:hover:bg-slate-800 rounded-r-xl shadow-lg border-y border-r border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 transition-all hover:pl-4"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <button
                        aria-label="Next Slide"
                        onClick={nextSlide}
                        className="absolute right-0 top-1/2 -translate-y-1/2 p-3 bg-white/80 dark:bg-slate-800/80 backdrop-blur hover:bg-white dark:hover:bg-slate-800 rounded-l-xl shadow-lg border-y border-l border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 transition-all hover:pr-4"
                    >
                        <ChevronRight className="w-6 h-6" />
                    </button>
                </div>

                {/* Footer / Dots */}
                <div className="p-4 border-t border-slate-100 dark:border-slate-800 flex justify-center gap-2 bg-white dark:bg-slate-900">
                    {slides.map((_, index) => (
                        <button
                            key={index}
                            aria-label={`Go to slide ${index + 1}`}
                            onClick={() => setCurrentSlide(index)}
                            className={`w-2.5 h-2.5 rounded-full transition-all ${currentSlide === index
                                    ? 'bg-indigo-500 w-6'
                                    : 'bg-slate-300 dark:bg-slate-600 hover:bg-slate-400 dark:hover:bg-slate-500'
                                }`}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ArchitectureModal;
