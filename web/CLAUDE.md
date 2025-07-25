# CLAUDE.md - Web Frontend

This file provides guidance to Claude Code when working with the web frontend of Gopie.

## Quick Start

```bash
cd web
bun install
bun run dev
```

## Development Commands

- **Development**: `bun run dev` (includes WASM preparation)
- **Build**: `bun run build`
- **Lint**: `bun run lint`
- **Start production**: `bun run start`
- **Install dependencies**: `bun install`

## Frontend Architecture

### Tech Stack
- **Framework**: Next.js 15 with App Router, React 19
- **Language**: TypeScript
- **Styling**: TailwindCSS with Radix UI components
- **State Management**: 
  - Zustand for global state (auth, chat, SQL, visualization stores)
  - React Query (TanStack Query) for server state
- **Forms**: React Hook Form with Zod validation
- **API Client**: Ky for HTTP requests

### Key Features
- **DuckDB WASM**: Client-side SQL execution with web workers
- **Monaco Editor**: SQL editing with syntax highlighting
- **Data Visualization**: Vega-Lite charts
- **Voice Interface**: LiveKit integration for voice interactions
- **File Upload**: Uppy for dataset uploads
- **Authentication**: Zitadel OAuth integration

## Project Structure

```
web/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── api/               # API routes (auth, chat, proxy)
│   │   ├── auth/              # Authentication pages
│   │   ├── chat/              # Standalone chat interface
│   │   ├── projects/          # Project management pages
│   │   └── settings/          # User settings
│   ├── components/            # React components
│   │   ├── ui/               # Shadcn/ui base components
│   │   ├── chat/             # Chat-related components
│   │   ├── dataset/          # Dataset management components
│   │   ├── project/          # Project components
│   │   └── navigation/       # Navigation components
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utilities and libraries
│   │   ├── api-client.ts     # API client configuration
│   │   ├── queries/          # React Query queries
│   │   ├── mutations/        # React Query mutations
│   │   └── stores/           # Zustand stores
│   └── types/                 # TypeScript type definitions
└── public/                    # Static assets
    ├── duckdb-*.wasm         # DuckDB WASM files
    └── images/               # Icons and logos
```

## Key Components

### Authentication (`src/components/auth/`)
- `auth-provider.tsx`: Context provider for authentication state
- `protected-route.tsx`: Route protection HOC
- Uses Zitadel OAuth with JWT tokens

### Chat Interface (`src/components/chat/`)
- `message.tsx`: Chat message display
- `mention-input.tsx`: Input with dataset/table mentions
- `sql-results.tsx`: SQL query results display
- `visualization-results.tsx`: Chart visualization
- `voice-mode.tsx`: Voice interaction mode

### Dataset Management (`src/components/dataset/`)
- `dataset-upload-wizard.tsx`: Multi-step upload flow
- `schema-table.tsx`: Schema viewer/editor
- `data-preview.tsx`: Dataset preview with DuckDB
- `sql-editor.tsx`: Monaco-based SQL editor

## State Management

### Zustand Stores (`src/lib/stores/`)
- **authStore**: User authentication state
- **chatStore**: Chat messages and state
- **sqlStore**: SQL query state and results
- **visualizationStore**: Chart configurations
- **uploadStore**: File upload progress
- **columnDescriptionStore**: Schema metadata

## API Integration

### API Client (`src/lib/api-client.ts`)
- Ky-based HTTP client with auth interceptors
- Automatic token refresh
- Error handling and retries

### Queries and Mutations
- **Queries** (`src/lib/queries/`): Data fetching with caching
- **Mutations** (`src/lib/mutations/`): Data modifications
- All use React Query for state management

## Environment Configuration

Required environment variables in `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CHAT_API_URL=http://localhost:8001
NEXT_PUBLIC_ZITADEL_REDIRECT_URI=http://localhost:3000/api/auth/oauth/callback
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
```

## Testing Approach

- Component testing with React Testing Library
- E2E testing considerations for auth flows
- Mock API responses for isolated testing

## Performance Considerations

- DuckDB WASM loaded on-demand
- Code splitting with dynamic imports
- Image optimization with Next.js Image
- React Query for efficient data caching

## Common Patterns

### Protected Routes
```typescript
// Use ProtectedRoute wrapper for auth-required pages
<ProtectedRoute>
  <YourComponent />
</ProtectedRoute>
```

### API Calls
```typescript
// Use pre-configured queries/mutations
const { data, isLoading } = useQuery({
  queryKey: ['projects'],
  queryFn: listProjects
});
```

### Form Handling
```typescript
// React Hook Form with Zod validation
const form = useForm<FormData>({
  resolver: zodResolver(formSchema)
});
```

## Development Tips

1. **WASM Files**: Run `bun run prepare-wasm` before development
2. **Type Safety**: Use generated types from API responses
3. **Component Library**: Prefer Radix UI components with Tailwind styling
4. **Error Boundaries**: Wrap features in error boundaries
5. **Loading States**: Always handle loading/error states in UI

## Debugging

- Browser DevTools for client-side debugging
- React Query DevTools for query inspection
- Network tab for API request debugging
- Console logs for DuckDB WASM operations