import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  Package,
  Github,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import logoImage from '../../assets/logo.png';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description?: string;
}

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'Overview and statistics',
  },
  {
    title: 'Projects',
    href: '/projects',
    icon: FolderKanban,
    description: 'Browse projects, experiments, and runs',
  },
  {
    title: 'Artifacts',
    href: '/artifacts',
    icon: Package,
    description: 'ORAS registry artifacts',
  },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-card">
      {/* Logo */}
      <Link to="/" className="flex h-16 items-center gap-3 border-b px-6 hover:bg-accent/50 transition-colors">
        <img
          src={logoImage}
          alt="AlphaTrion Logo"
          className="h-8 w-8"
        />
        <h1 className="text-xl font-bold text-foreground">AlphaTrion</h1>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.href ||
            (item.href !== '/' && location.pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex flex-col gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              )}
            >
              <div className="flex items-center gap-3">
                <Icon className="h-5 w-5" />
                {item.title}
              </div>
              {item.description && (
                <span className="text-xs text-muted-foreground pl-8">
                  {item.description}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-4">
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <a
            href="https://github.com/InftyAI/alphatrion"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            title="View on GitHub"
          >
            <Github className="h-4 w-4" />
          </a>
          <span>v0.1.0</span>
        </div>
      </div>
    </div>
  );
}
