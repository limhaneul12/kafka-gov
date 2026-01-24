import React, { useState } from 'react';
import { Filter, Search as SearchIcon, X } from 'lucide-react';
import { Button } from '../common/Button';
import { Input } from '../common/Input';

interface SearchBarProps {
    onSearch: (query: string, owner: string | null) => void;
}

export const SearchBar = ({ onSearch }: SearchBarProps) => {
    const [query, setQuery] = useState('');
    const [owner, setOwner] = useState('');

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        onSearch(query, owner || null);
    };

    const handleClear = () => {
        setQuery('');
        setOwner('');
        onSearch('', null);
    };

    return (
        <form
            onSubmit={handleSearch}
            className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex gap-4 items-center flex-wrap"
        >
            <div className="flex-1 min-w-[200px]">
                <Input
                    icon={SearchIcon}
                    placeholder="Search by subject name..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
            </div>
            <div className="min-w-[150px]">
                <Input
                    icon={Filter}
                    placeholder="Filter by owner..."
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                />
            </div>
            <Button type="submit">Search</Button>
            {(query || owner) && (
                <Button
                    type="button"
                    variant="ghost"
                    onClick={handleClear}
                    className="p-2 text-slate-500 hover:text-rose-500"
                    title="Clear Filters"
                >
                    <X className="w-5 h-5" />
                </Button>
            )}
        </form>
    );
};
