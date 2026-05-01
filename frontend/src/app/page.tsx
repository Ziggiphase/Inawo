import styles from './page.module.css';

export default function Home() {
  return (
    <div className={styles.container}>
      {/* Navigation */}
      <nav className={styles.nav}>
        <div className={styles.logo}>Inawo AI</div>
        <div className={styles.navLinks}>
          <a href="/explore">Marketplace</a>
          <a href="/pricing">Pricing</a>
          <a href="/login" className="button-secondary" style={{ padding: '8px 16px', fontSize: '14px' }}>Log in</a>
          <a href="/signup" className="button-primary" style={{ padding: '8px 16px', fontSize: '14px' }}>Get Started</a>
        </div>
      </nav>

      {/* Hero Section */}
      <main className={styles.main}>
        <div className={styles.heroGlow}></div>
        
        <div className={styles.heroContent}>
          <div className={styles.badge}>
            <span className={styles.badgeDot}></span>
            Now open to all MSMEs
          </div>
          
          <h1 className={styles.title}>
            The Operating System<br />
            <span className={styles.titleGradient}>For Modern Commerce.</span>
          </h1>
          
          <p className={styles.subtitle}>
            Instantly turn your PDFs and catalogs into a 24/7 AI sales agent on WhatsApp. 
            Join the premium marketplace where customers discover and interact with the best businesses.
          </p>
          
          <div className={styles.ctaGroup}>
            <button className="button-primary" style={{ padding: '16px 32px', fontSize: '16px' }}>
              Create Business Profile
            </button>
            <button className="button-secondary" style={{ padding: '16px 32px', fontSize: '16px' }}>
              Explore Marketplace
            </button>
          </div>
        </div>

        {/* Dashboard Preview / Glass Mockup */}
        <div className={styles.dashboardMockup}>
          <div className={`glass-panel ${styles.mockupHeader}`}>
            <div className={styles.mockupDots}>
              <span></span><span></span><span></span>
            </div>
            <div className={styles.mockupTitle}>dashboard.inawo.ai</div>
          </div>
          <div className={styles.mockupBody}>
            <div className={styles.sidebar}>
              <div className={styles.sidebarItem} data-active="true">Analytics</div>
              <div className={styles.sidebarItem}>AI Config</div>
              <div className={styles.sidebarItem}>Live Chats</div>
              <div className={styles.sidebarItem}>Orders</div>
            </div>
            <div className={styles.mainContent}>
              <div className={styles.statsGrid}>
                <div className={`glass-panel ${styles.statCard}`}>
                  <p className={styles.statLabel}>AI Conversion Rate</p>
                  <p className={styles.statValue}>68.4%</p>
                </div>
                <div className={`glass-panel ${styles.statCard}`}>
                  <p className={styles.statLabel}>Human Handoffs</p>
                  <p className={styles.statValue}>2.1%</p>
                </div>
                <div className={`glass-panel ${styles.statCard}`}>
                  <p className={styles.statLabel}>Avg. Customer Rating</p>
                  <p className={styles.statValue}>4.9/5</p>
                </div>
              </div>
              <div className={`glass-panel ${styles.chartArea}`}>
                <div className={styles.chartBar} style={{height: '60%'}}></div>
                <div className={styles.chartBar} style={{height: '80%'}}></div>
                <div className={styles.chartBar} style={{height: '40%'}}></div>
                <div className={styles.chartBar} style={{height: '90%'}}></div>
                <div className={styles.chartBar} style={{height: '100%'}}></div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
