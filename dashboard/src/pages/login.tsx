import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logoImage from '../assets/logo.png';

// Use runtime config (Kubernetes) > build-time env (Docker) > localhost dev
const getApiBaseUrl = () => {
  // @ts-ignore - window.ENV is injected at runtime by entrypoint.sh
  if (typeof window !== 'undefined' && window.ENV?.VITE_API_URL) {
    // @ts-ignore
    return window.ENV.VITE_API_URL;
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
};

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Login failed');
      }

      const data = await response.json();

      // Store JWT token and user info
      localStorage.setItem('alphatrion_token', data.access_token);
      localStorage.setItem('alphatrion_user', JSON.stringify(data.user));

      // Store user_id and org_id for GraphQL headers
      const payload = JSON.parse(atob(data.access_token.split('.')[1]));
      localStorage.setItem('alphatrion_user_id', data.user.id);
      localStorage.setItem('alphatrion_org_id', payload.org_id);

      // Store first team if available
      if (data.user.teams && data.user.teams.length > 0) {
        localStorage.setItem('alphatrion_team_id', data.user.teams[0].id);
      }

      // Redirect to dashboard (reload to initialize app with new auth)
      window.location.href = '/';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <div className="flex items-center justify-center gap-3 mb-2">
            <img
              src={logoImage}
              alt="AlphaTrion Logo"
              className="h-12 w-12"
            />
            <h2 className="text-3xl font-bold text-gray-900">
              AlphaTrion
            </h2>
          </div>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to your account
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
