import React from "react";

export type TabItem = {
    id: string;
    label: string | React.ReactNode;
};

type TabsProps = {
    tabs: TabItem[];
    active: string;
    onChange: (id: string) => void;
};

export default function Tabs({ tabs, active, onChange }: TabsProps) {
    return (
        <div className="border-b border-gray-200 mb-6">
            <nav className="flex gap-4">
                {tabs.map((tab) => {
                    const isActive = active === tab.id;

                    return (
                        <button
                            key={tab.id}
                            onClick={() => onChange(tab.id)}
                            className={`py-2 px-4 border-b-2 font-medium text-sm transition-colors ${isActive
                                ? "border-blue-600 text-blue-600"
                                : "border-transparent text-gray-500 hover:text-gray-700"
                                }`}
                        >
                            {tab.label}
                        </button>
                    );
                })}
            </nav>
        </div>
    );
}
