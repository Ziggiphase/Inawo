"use client";

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem('inawo_token');
    router.push('/login');
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      {/* Sidebar Navigation */}
      <nav style={{ width: '250px', backgroundColor: 'var(--bg-secondary)', borderRight: '1px solid var(--border-color)', padding: '32px 24px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: '48px', fontSize: '24px', fontWeight: 'bold' }}>
          Inawo <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>Business</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          <SidebarLink href="/dashboard" label="Overview / Analytics" active={pathname === '/dashboard'} />
          <SidebarLink href="/dashboard/orders" label="Live Orders & Chat" active={pathname === '/dashboard/orders'} />
          <SidebarLink href="/dashboard/upload" label="Catalog Training" active={pathname === '/dashboard/upload'} />
          <SidebarLink href="/dashboard/settings" label="Store Settings" active={pathname === '/dashboard/settings'} />
        </div>

        <button onClick={handleLogout} style={{ padding: '12px 16px', textAlign: 'left', color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', fontWeight: 500, borderRadius: 'var(--radius-sm)' }}>
          Sign Out
        </button>
      </nav>

      {/* Main Content Area */}
      <main style={{ flex: 1, overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  );
}

function SidebarLink({ href, label, active }: { href: string, label: string, active: boolean }) {
  return (
    <Link href={href} style={{
      padding: '12px 16px',
      borderRadius: 'var(--radius-sm)',
      textDecoration: 'none',
      fontSize: '14px',
      fontWeight: 500,
      backgroundColor: active ? 'var(--bg-tertiary)' : 'transparent',
      color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
      transition: 'all 0.2s'
    }}>
      {label}
    </Link>
  );
}
