import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FlaskConical } from 'lucide-react';

export default function Sidebar() {
    const location = useLocation();

    const isActive = (path: string) => location.pathname === path;

    const navItems = [
        { path: '/', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/experiments', label: 'Experiments', icon: FlaskConical },
    ];

    return (
        <div className="w-64 min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 text-white">
            {/* Logo */}
            <div className="p-6 border-b border-gray-700">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                        <span className="text-2xl">🔬</span>
                    </div>
                    <div>
                        <h1 className="text-xl font-bold">LLM Observatory</h1>
                        <p className="text-xs text-gray-400">Experiment Tracking</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="p-4 space-y-2">
                {navItems.map(({ path, label, icon: Icon }) => (
                    <Link
                        key={path}
                        to={path}
                        className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${isActive(path)
                            ? 'bg-gradient-to-r from-primary-600 to-accent-600 shadow-lg'
                            : 'hover:bg-gray-700/50'
                            }`}
                    >
                        <Icon size={20} />
                        <span className="font-medium">{label}</span>
                    </Link>
                ))}
            </nav>
        </div>
    );
}