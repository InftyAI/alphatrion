import { Link } from "react-router-dom";

export default function Breadcrumb({
    items,
}: {
    items: { label: React.ReactNode; href?: string }[];
}) {
    return (
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
            {items.map((item, i) => {
                const last = i === items.length - 1;

                return (
                    <div key={i} className="flex items-center gap-2">
                        {last ? (
                            // IMPORTANT: should directly render label. Do NOT wrap in span.
                            item.label
                        ) : (
                            <Link to={item.href!} className="hover:text-blue-600">
                                {item.label}
                            </Link>
                        )}

                        {!last && <span className="text-gray-400">/</span>}
                    </div>
                );
            })}
        </div>
    );
}
