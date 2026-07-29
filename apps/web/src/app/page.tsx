import { redirect } from 'next/navigation';

// Root redirects to dashboard (auth guard handled in middleware)
export default function RootPage() {
  redirect('/dashboard');
}
