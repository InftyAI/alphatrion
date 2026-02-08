# AlphaTrion Dashboard

Web dashboard for AlphaTrion AI observability platform.

## Quick Start

### Development Mode

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will start on `http://localhost:5173`.

### Production Build

```bash
npm run build
```

Built files will be in `./static` directory.

## Documentation

- **[Setup Guide](../docs/dashboard/setup.md)** - Complete setup and troubleshooting guide
- **[CLI Guide](../docs/dashboard/dashboard-cli.md)** - Using the `alphatrion dashboard` command
- **[Architecture](../docs/dashboard/dashboard-architecture.md)** - Technical architecture and deployment

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **React Router** - Client-side routing
- **TanStack Query** - Data fetching with smart polling
- **Recharts** - Data visualization

## Project Structure

```
dashboard/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── ui/          # shadcn/ui primitives
│   │   ├── dashboard/   # Dashboard-specific components
│   │   └── metrics/     # Metrics visualization
│   ├── pages/           # Route components
│   │   ├── dashboard/   # Dashboard overview
│   │   ├── projects/    # Projects pages
│   │   ├── experiments/ # Experiments pages
│   │   ├── runs/        # Runs pages
│   │   └── artifacts/   # Artifacts browser
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Core utilities
│   ├── context/         # React contexts
│   └── types/           # TypeScript type definitions
├── static/              # Production build output
└── docs/                # Developer documentation
```

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend server running on `http://localhost:8000`

### Commands

- `npm run dev` - Start dev server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Environment Variables

Create a `.env` file:

```bash
VITE_GRAPHQL_URL=http://localhost:8000/graphql
```

## Contributing

See the main [Contributing Guide](../docs/dev/development.md).
