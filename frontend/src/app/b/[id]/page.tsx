"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

interface Product {
  id: number;
  name: string;
  price: number;
  description: string;
}

interface BusinessProfile {
  id: number;
  name: string;
  category: string;
  rating: number;
  description: string;
  brand_color: string;
  products: Product[];
}

export default function BusinessStorefront() {
  const params = useParams();
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await fetch(`http://localhost:10000/api/public/business/${params.id}`);
        if (!res.ok) throw new Error('Business not found');
        setProfile(await res.json());
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    if (params.id) fetchProfile();
  }, [params.id]);

  if (isLoading) return <div style={{ padding: '64px', textAlign: 'center' }}>Loading storefront...</div>;
  if (error) return <div style={{ padding: '64px', textAlign: 'center', color: '#ef4444' }}>{error}</div>;
  if (!profile) return null;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      {/* Dynamic Brand Banner */}
      <div style={{ height: '200px', backgroundColor: profile.brand_color, position: 'relative' }}>
        <div style={{ position: 'absolute', bottom: '-40px', left: '48px', width: '120px', height: '120px', borderRadius: '16px', backgroundColor: 'var(--bg-secondary)', border: '4px solid var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', fontWeight: 'bold' }}>
          {profile.name.charAt(0)}
        </div>
      </div>

      <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '64px 48px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: '36px', fontWeight: 600, marginBottom: '8px' }}>{profile.name}</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '16px', maxWidth: '600px' }}>{profile.description}</p>
            <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
              <span style={{ padding: '4px 12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-full)', fontSize: '13px', fontWeight: 500 }}>{profile.category}</span>
              <span style={{ padding: '4px 12px', background: 'rgba(245,158,11,0.1)', color: '#f59e0b', borderRadius: 'var(--radius-full)', fontSize: '13px', fontWeight: 500 }}>★ {profile.rating} Rating</span>
            </div>
          </div>
          
          <button className="button-primary" style={{ padding: '16px 32px', fontSize: '16px' }}>
            Chat with AI on WhatsApp ↗
          </button>
        </div>

        {/* Product Catalog Grid */}
        <div style={{ marginTop: '64px' }}>
          <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Product Catalog</h2>
          {profile.products.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>This business has not uploaded their catalog yet.</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
              {profile.products.map(p => (
                <div key={p.id} className="glass-panel" style={{ padding: '24px' }}>
                  <h3 style={{ fontSize: '18px', fontWeight: 500, marginBottom: '8px' }}>{p.name}</h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '16px', height: '40px', overflow: 'hidden' }}>{p.description}</p>
                  <p style={{ fontSize: '18px', fontWeight: 600 }}>₦{p.price.toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
