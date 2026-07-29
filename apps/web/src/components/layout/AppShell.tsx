'use client';
import Header from './Header';
import BottomNav from './BottomNav';

export default function AppShell({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen">
      <Header title={title} />
      <main className="flex-1 px-4 py-4 pb-24 max-w-2xl mx-auto w-full">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
