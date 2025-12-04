import { Link } from "react-router-dom";

function short(id?: string, len = 8) {
    return id ? id.slice(0, len) : "";
}

export interface BreadcrumbProps {
    items: {
        label: string;
        href?: string;   // no href to last item not clickable
    }[];
    className?: string;
}

export default function Breadcrumb({ items, className }: BreadcrumbProps) {
    return (
        <div
            className={cn(
                "flex items-center gap-2 text-sm text-gray-500 mb-4",
                className
            )}
        >
            {items.map((item, i) => {
                const isLast = i === items.length - 1;

                return (
                    <div key={i} className="flex items-center gap-2">
                        {isLast ? (
                            <span className="text-gray-900 font-medium">
                                {item.label}
                            </span>
                        ) : (
                            <Link
                                to={item.href!}
                                className="hover:text-blue-600 transition-colors"
                            >
                                {item.label}
                            </Link>
                        )}

                        {!isLast && <span className="text-gray-400">/</span>}
                    </div>
                );
            })}
        </div>
    );
}
