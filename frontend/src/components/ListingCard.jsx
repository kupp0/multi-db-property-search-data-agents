import React, { useState } from 'react';
import { MapPin, Bed } from 'lucide-react';

const formatCurrency = (number) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'CHF',
        maximumFractionDigits: 0,
    }).format(number);
};

const ListingCard = ({ listing }) => {
    const [imageUrl, setImageUrl] = useState(listing.image_gcs_uri || null);

    React.useEffect(() => {
        setImageUrl(listing.image_gcs_uri || null);
    }, [listing.image_gcs_uri]);

    return (
        <div className="bg-white/80 dark:bg-slate-800/60 backdrop-blur-md rounded-2xl shadow-sm border border-white/40 dark:border-slate-700/50 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col group">
            <div className="h-48 bg-slate-100 relative overflow-hidden group">
                {imageUrl ? (
                    <img src={imageUrl} alt={listing.title || "Property"} className="w-full h-full object-cover hover:scale-105 transition-transform duration-700" />
                ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-900/50">
                        <span className="text-4xl mb-2">🏠</span>
                    </div>
                )}
                <div className="absolute top-3 right-3 bg-white/95 px-2 py-1 rounded shadow-sm font-bold text-sm text-slate-700">
                    {listing.price ? formatCurrency(listing.price) : "N/A"}
                </div>
            </div>
            <div className="p-5 flex flex-col flex-grow">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1 truncate">{listing.title}</h3>
                <div className="flex items-center text-gray-500 dark:text-gray-400 text-sm mb-4"><MapPin className="w-4 h-4 mr-1" /> {listing.city}</div>
                <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-300 mb-4 pb-4 border-b border-gray-100 dark:border-gray-700">
                    {listing.bedrooms !== undefined && <><Bed className="w-4 h-4 text-teal-500 mr-1" /> {listing.bedrooms} Beds</>}
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">{listing.description}</p>
            </div>
        </div>
    );
};

export default ListingCard;
