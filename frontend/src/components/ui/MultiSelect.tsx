import { useState, useRef, useEffect } from "react";
import { ChevronDown } from "lucide-react";

interface MultiSelectProps {
  label: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  colorScheme?: "blue" | "green" | "purple" | "orange";
}

export default function MultiSelect({
  label,
  options,
  selected,
  onChange,
  placeholder = "선택하세요",
  colorScheme = "blue",
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const colorClasses = {
    blue: "bg-blue-100 text-blue-800 border-blue-200",
    green: "bg-green-100 text-green-800 border-green-200",
    purple: "bg-purple-100 text-purple-800 border-purple-200",
    orange: "bg-orange-100 text-orange-800 border-orange-200",
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((item) => item !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  const removeOption = (option: string) => {
    onChange(selected.filter((item) => item !== option));
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>

      {/* Dropdown Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-left focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 flex items-center justify-between"
      >
        <span className="text-sm text-gray-700">
          {selected.length === 0 ? placeholder : `${selected.length}개 선택됨`}
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {/* Selected Items Display */}
      {selected.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {selected.map((item) => (
            <span
              key={item}
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${colorClasses[colorScheme]}`}
            >
              {item}
              <button
                onClick={() => removeOption(item)}
                className="ml-1 hover:opacity-70"
                type="button"
              >
                ×
              </button>
            </span>
          ))}
          <button
            onClick={() => onChange([])}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
            type="button"
          >
            전체 해제
          </button>
        </div>
      )}

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg max-h-60 overflow-auto">
          {options.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500">옵션이 없습니다</div>
          ) : (
            <>
              <div className="px-3 py-2 border-b border-gray-200">
                <button
                  type="button"
                  onClick={() => {
                    if (selected.length === options.length) {
                      onChange([]);
                    } else {
                      onChange([...options]);
                    }
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  {selected.length === options.length ? "전체 해제" : "전체 선택"}
                </button>
              </div>
              {options.map((option) => (
                <label
                  key={option}
                  className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(option)}
                    onChange={() => toggleOption(option)}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{option}</span>
                </label>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
