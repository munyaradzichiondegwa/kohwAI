KohwAI frontend API URL correction

Files included (extract this archive at the KohwAI repository root):
  apps/web/src/lib/api.ts
  apps/web/next.config.js
  apps/web/Dockerfile

What changed:
1. api.ts uses nullish coalescing (??), preserving the intentional distinction:
   - undefined -> localhost API fallback
   - empty string -> same-origin routing behind the production reverse proxy
2. next.config.js retains the same nullish fallback and documents the local build values.
3. Dockerfile exposes NEXT_PUBLIC_WS_URL as a build argument and build-stage environment
   variable, matching NEXT_PUBLIC_API_URL. Both arguments default to empty for production
   same-origin routing. Other existing Dockerfile build arguments and stages are preserved.

Local Windows Docker build (run from the repository root):
  docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 --build-arg NEXT_PUBLIC_WS_URL=ws://localhost:8000 -f apps/web/Dockerfile -t kohwai/web:ci .

Important:
- These NEXT_PUBLIC_* values are embedded into the Next.js bundle at build time.
- localhost:8000 is appropriate for this local browser-based deployment because the browser
  runs on the Windows host. Do not use this value for a deployed production build.
- For production behind a reverse proxy, leave NEXT_PUBLIC_API_URL and
  NEXT_PUBLIC_WS_URL empty (the Dockerfile defaults) so same-origin routing is retained.
- This archive does not modify containers, databases, volumes, or the running application.
