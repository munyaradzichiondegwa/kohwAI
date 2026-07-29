'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/dashboard', icon: '🏠', label: 'Home' },
  { href: '/zunde',     icon: '🌾', label: 'Zunde' },
  { href: '/musika',    icon: '🛒', label: 'Musika' },
  { href: '/mvura',     icon: '💧', label: 'Mvura' },
  { href: '/livestock', icon: '🐄', label: 'Health' },
];

export default function BottomNav() {
  const path = usePathname();
  return (
    <nav className="fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-50">
      <div className="flex justify-around items-center h-16 max-w-2xl mx-auto">
        {NAV_ITEMS.map(item => {
          const active = path.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href}
              className={`flex flex-col items-center text-xs gap-0.5 min-w-[44px] min-h-[44px] justify-center ${active ? 'text-brand-green font-semibold' : 'text-gray-500'}`}
            >
              <span className="text-xl">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
