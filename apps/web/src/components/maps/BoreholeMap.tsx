'use client';
import { useEffect, useRef, useState } from 'react';
import useSWR from 'swr';
import { getBoreholes } from '@/lib/offline';
import type { Borehole } from '@kohwai/shared/types';

const SC: Record<string,string> = { working:'#1A7A4A', low:'#E8A020', dry:'#C0392B', unknown:'#6b7280' };

export default function BoreholeMap({ district }: { district?: string }) {
  const mapRef  = useRef<HTMLDivElement>(null);
  const mapInst = useRef<any>(null);
  const [ready, setReady]       = useState(false);
  const [view,  setView]        = useState<'map'|'list'>('map');
  const { data: bhs = [] } = useSWR<Borehole[]>(
    'boreholes-' + (district || 'all'),
    () => getBoreholes(district));

  useEffect(() => {
    if (!mapRef.current || mapInst.current) return;
    import('maplibre-gl').then(({ default: mgl }) => {
      const map = new mgl.Map({
        container: mapRef.current!,
        style: { version:8, sources:{ osm:{ type:'raster', tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize:256, attribution:'© OSM', maxzoom:19 } }, layers:[{ id:'osm', type:'raster', source:'osm' }] },
        center: [30.0,-19.5], zoom: 6,
      });
      map.addControl(new mgl.NavigationControl(), 'top-right');
      if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => { map.setCenter([p.coords.longitude, p.coords.latitude]); map.setZoom(11); });
      map.on('load', () => setReady(true));
      mapInst.current = map;
    }).catch(() => setView('list'));
    return () => { mapInst.current?.remove(); mapInst.current = null; };
  }, []);

  useEffect(() => {
    if (!ready || !mapInst.current || !bhs.length) return;
    import('maplibre-gl').then(({ default: mgl }) => {
      bhs.forEach(bh => {
        if (!bh.lat || !bh.lng) return;
        const el = document.createElement('div');
        el.style.cssText = 'width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3);cursor:pointer;background:' + (SC[bh.status]||'#6b7280');
        new mgl.Marker({ element:el }).setLngLat([bh.lng, bh.lat])
          .setPopup(new mgl.Popup({ offset:15 }).setHTML('<strong>' + bh.name + '</strong><br>' + bh.village + '<br>Status: ' + bh.status))
          .addTo(mapInst.current);
      });
    });
  }, [ready, bhs]);

  return (
    <div className="rounded-2xl overflow-hidden border border-gray-200">
      <div className="flex border-b border-gray-200 bg-white">
        {(['map','list'] as const).map(m => (
          <button key={m} onClick={() => setView(m)}
            className={'flex-1 py-2.5 text-sm font-medium ' + (view===m ? 'bg-brand-green text-white' : 'text-gray-600')}>
            {m === 'map' ? '🗺️ Map' : '📋 List (' + bhs.length + ')'}
          </button>
        ))}
      </div>
      {view === 'map' && (
        <div className="relative">
          <div ref={mapRef} className="w-full h-[380px]" />
          {!ready && <div className="absolute inset-0 flex items-center justify-center bg-gray-100 text-sm text-gray-500">Loading map…</div>}
        </div>
      )}
      {view === 'list' && (
        <div className="bg-white max-h-[380px] overflow-y-auto divide-y divide-gray-100">
          {!bhs.length && <p className="text-center text-gray-400 py-8 text-sm">No boreholes found.</p>}
          {bhs.map(bh => (
            <div key={bh.id} className="flex items-center justify-between px-4 py-3">
              <div><p className="font-medium text-sm text-gray-900">{bh.name}</p><p className="text-xs text-gray-500">{bh.village}</p></div>
              <span className="text-xs font-semibold text-white px-2.5 py-1 rounded-full" style={{ backgroundColor: SC[bh.status]||'#6b7280' }}>{bh.status}</span>
            </div>
          ))}
        </div>
      )}
      <div className="bg-gray-50 px-4 py-2 flex gap-4 text-xs text-gray-500">
        {Object.entries(SC).map(([s,c]) => (
          <span key={s} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor:c }} />
            {s.charAt(0).toUpperCase()+s.slice(1)}
          </span>
        ))}
      </div>
    </div>
  );
}
