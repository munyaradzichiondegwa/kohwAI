'use client';
import Link from 'next/link';

interface Props {
  icon: string; label: string;
  href: string; desc: string;
}

export default function PillarCard({ icon, label, href, desc }: Props) {
  return (
    <Link href={href}
      className="flex flex-col items-start bg-white rounded-2xl shadow-sm p-4 hover:shadow-md transition-shadow min-h-[120px] border border-gray-100"
    >
      <span className="text-3xl mb-2">{icon}</span>
      <p className="font-semibold text-gray-900">{label}</p>
      <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
    </Link>
  );
}
