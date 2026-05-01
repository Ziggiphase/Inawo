import DashboardClient from './DashboardClient';

export default function DashboardPage() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <header style={{ 
        height: '64px', 
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        backgroundColor: 'var(--bg-secondary)'
      }}>
        <div style={{ fontWeight: 600, fontSize: '18px' }}>Inawo AI Workspace</div>
      </header>
      
      <main style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ marginBottom: '8px', fontSize: '28px' }}>Analytics & Control Center</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
          Monitor your AI's performance and seamlessly step in when needed.
        </p>

        <DashboardClient />
      </main>
    </div>
  );
}
