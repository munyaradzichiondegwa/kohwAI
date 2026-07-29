'use client';
import { Suspense } from 'react';
import Header from '@/components/layout/Header';
import BottomNav from '@/components/layout/BottomNav';
import AlertCarousel from '@/components/ui/AlertCarousel';
import InsightsPanel from '@/components/ui/InsightsPanel';
import PillarCard from '@/components/ui/PillarCard';

const PILLARS = [
  { key: 'zunde',     label: 'Zunde',     icon: '🌾', href: '/zunde',     desc: 'Crops & Early Warning' },
  { key: 'mvura',     label: 'Mvura',     icon: '💧', href: '/mvura',     desc: 'Water Security' },
  { key: 'simba',     label: 'Simba',     icon: '☀️', href: '/simba',     desc: 'Energy & Solar' },
  { key: 'musika',    label: 'Musika',    icon: '🛒', href: '/musika',    desc: 'Marketplace' },
  { key: 'livestock', label: 'Livestock', icon: '🐄', href: '/livestock', desc: 'Animal Health' },
] as const;

export default function DashboardPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 px-4 py-4 pb-20 max-w-2xl mx-auto w-full">
        <Suspense fallback={<div className="h-32 bg-gray-200 rounded-xl animate-pulse" />}>
          <AlertCarousel />
        </Suspense>
        <InsightsPanel />
        <section className="mt-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Your Dashboard</h2>
          <div className="grid grid-cols-2 gap-3">
            {PILLARS.map(({ key, ...p }) => <PillarCard key={key} {...p} />)}
          </div>
        </section>
      </main>
      <BottomNav />
    </div>
  );
}
