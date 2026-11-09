import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BarChart3,
  Building2,
  CheckCircle2,
  CircleDollarSign,
  FileCheck2,
  Fingerprint,
  Gauge,
  Globe2,
  Layers,
  LockKeyhole,
  Menu,
  PieChart,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Wallet,
  X,
  Zap,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import './LandingPage.css';

const features = [
  {
    icon: Users,
    title: 'Client intelligence',
    copy: 'A complete client view with contacts, directors, KYC, risks and policy history in one place.',
  },
  {
    icon: FileCheck2,
    title: 'Quote to policy',
    copy: 'Compare insurer quotes, bind cover and issue policies without double entry or lost paperwork.',
  },
  {
    icon: TrendingUp,
    title: 'Renewals on radar',
    copy: 'Stay ahead of expiries, endorsements and renewal opportunities with a live operational pipeline.',
  },
  {
    icon: Wallet,
    title: 'Money, reconciled',
    copy: 'Premiums, invoices, receipts, commissions and remittances flow through one auditable ledger.',
  },
  {
    icon: PieChart,
    title: 'Claims command',
    copy: 'Register, assess, approve and settle claims with clear ownership and a visible next step.',
  },
  {
    icon: BarChart3,
    title: 'Decisions on demand',
    copy: 'Thirteen ready-made reports and global search turn live brokerage data into confident answers.',
  },
];

const workflow = [
  {
    number: '01',
    title: 'Capture the client',
    copy: 'Build a clean client and risk profile from the very first conversation.',
  },
  {
    number: '02',
    title: 'Quote with confidence',
    copy: 'Invite insurer quotes, compare terms and select the right cover.',
  },
  {
    number: '03',
    title: 'Bind and issue',
    copy: 'Create the policy, premium schedule, invoice and commission in one flow.',
  },
  {
    number: '04',
    title: 'Collect and reconcile',
    copy: 'Allocate receipts, track debtors and keep every balance transparent.',
  },
  {
    number: '05',
    title: 'Renew and grow',
    copy: 'Turn policy milestones and performance insight into the next opportunity.',
  },
];

const security = [
  {
    icon: Fingerprint,
    title: 'Role-based access',
    copy: 'Granular module permissions keep every person focused on exactly what they should see.',
  },
  {
    icon: Building2,
    title: 'Branch-aware visibility',
    copy: 'Head office sees the whole picture while branch teams stay scoped to their own book.',
  },
  {
    icon: ShieldCheck,
    title: 'Full audit trail',
    copy: 'Important actions are recorded with the who, what and when for dependable accountability.',
  },
  {
    icon: LockKeyhole,
    title: 'Hardened foundations',
    copy: 'JWT sessions, login lockout, shared rate limiting and HTTPS-ready security controls.',
  },
];

const reports = [
  'Premium production',
  'Commission ageing',
  'Outstanding premiums',
  'Claims register',
  'Renewals',
  'Lost business',
];

export function LandingPage() {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const primaryHref = user ? '/dashboard' : '/login';
  const primaryLabel = user ? 'Open dashboard' : 'Sign in';
  const year = new Date().getFullYear();

  const closeMenu = () => setMenuOpen(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };
    const handleResize = () => {
      if (window.innerWidth > 980) setMenuOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="landing">
      <a href="#main-content" className="landing-skip-link">
        Skip to content
      </a>
      <div className="landing-top">
        <header className="landing-header">
          <div className="landing-container landing-nav">
            <Link to="/" className="landing-brand" aria-label="IBMS home">
              <span className="landing-brand-mark">
                <ShieldCheck size={22} />
              </span>
              <span className="landing-brand-copy">
                <strong>IBMS</strong>
                <small>Brokerage, in control.</small>
              </span>
            </Link>

            <nav
              className={`landing-nav-links${menuOpen ? ' is-open' : ''}`}
              id="landing-navigation"
              aria-label="Landing page navigation"
            >
              <a href="#platform" onClick={closeMenu}>
                Platform
              </a>
              <a href="#workflow" onClick={closeMenu}>
                Workflow
              </a>
              <a href="#insights" onClick={closeMenu}>
                Insights
              </a>
              <a href="#security" onClick={closeMenu}>
                Security
              </a>
              <Link to={primaryHref} className="landing-mobile-cta" onClick={closeMenu}>
                {primaryLabel} <ArrowRight size={16} />
              </Link>
            </nav>

            <div className="landing-nav-actions">
              <Link to={primaryHref} className="landing-signin">
                {primaryLabel} <ArrowRight size={16} />
              </Link>
              <button
                type="button"
                className="landing-menu-button"
                aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
                aria-expanded={menuOpen}
                aria-controls="landing-navigation"
                onClick={() => setMenuOpen((current) => !current)}
              >
                {menuOpen ? <X size={21} /> : <Menu size={21} />}
              </button>
            </div>
          </div>
        </header>

        <main id="main-content">
          <section className="landing-hero">
            <div className="landing-container landing-hero-grid">
              <div className="landing-hero-copy">
                <span className="landing-eyebrow landing-eyebrow-light">
                  <Sparkles size={14} /> Built for the detail behind every policy
                </span>
                <h1>
                  Run the whole brokerage.
                  <span>Without the busywork.</span>
                </h1>
                <p>
                  IBMS brings clients, risks, quotations, policies, collections,
                  commissions and claims into one secure workspace — so your team can
                  focus on growth, not admin.
                </p>

                <div className="landing-hero-actions">
                  <Link to={primaryHref} className="landing-button landing-button-primary">
                    {user ? 'Open dashboard' : 'Enter workspace'} <ArrowRight size={17} />
                  </Link>
                  <a href="#platform" className="landing-button landing-button-ghost">
                    Explore the platform <ArrowUpRight size={17} />
                  </a>
                </div>

                <ul className="landing-hero-trust">
                  <li>
                    <CheckCircle2 size={15} /> Role-based access
                  </li>
                  <li>
                    <CheckCircle2 size={15} /> Full audit trail
                  </li>
                  <li>
                    <CheckCircle2 size={15} /> Multi-branch ready
                  </li>
                </ul>
              </div>

              <div className="landing-hero-visual" aria-hidden="true">
                <div className="preview-orbit preview-orbit-one" />
                <div className="preview-orbit preview-orbit-two" />

                <div className="preview-window">
                  <div className="preview-bar">
                    <span className="preview-dots">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span className="preview-url">
                      <LockKeyhole size={11} /> app.ibms.local/dashboard
                    </span>
                    <span className="preview-avatar">AM</span>
                  </div>

                  <div className="preview-body">
                    <aside className="preview-side">
                      <div className="preview-logo">
                        <ShieldCheck size={15} /> IBMS
                      </div>
                      <div className="preview-nav">
                        <span className="active">
                          <Gauge size={13} /> Dashboard
                        </span>
                        <span>
                          <Users size={13} /> Clients
                        </span>
                        <span>
                          <FileCheck2 size={13} /> Policies
                        </span>
                        <span>
                          <Wallet size={13} /> Collections
                        </span>
                        <span>
                          <PieChart size={13} /> Claims
                        </span>
                        <span>
                          <BarChart3 size={13} /> Reports
                        </span>
                      </div>
                      <div className="preview-side-card">
                        <ShieldCheck size={15} />
                        <span>
                          Audit trail
                          <small>Every change logged</small>
                        </span>
                      </div>
                    </aside>

                    <div className="preview-main">
                      <div className="preview-head">
                        <div>
                          <span>Workspace overview</span>
                          <strong>Good morning, Alex</strong>
                        </div>
                        <span className="preview-live">
                          <i /> Live
                        </span>
                      </div>

                      <div className="preview-stats">
                        <div>
                          <span>Policies in force</span>
                          <strong>1,284</strong>
                          <small>+8.4% this quarter</small>
                        </div>
                        <div>
                          <span>Collected MTD</span>
                          <strong>USh 482M</strong>
                          <small>92.6% of target</small>
                        </div>
                        <div>
                          <span>Open claims</span>
                          <strong>18</strong>
                          <small>4 awaiting approval</small>
                        </div>
                      </div>

                      <div className="preview-chart-card">
                        <div className="preview-chart-head">
                          <span>Premium collections</span>
                          <strong>
                            <TrendingUp size={12} /> +18.2%
                          </strong>
                        </div>
                        <svg
                          className="preview-chart"
                          viewBox="0 0 340 96"
                          preserveAspectRatio="none"
                        >
                          <defs>
                            <linearGradient id="landingChartFill" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#2491a6" stopOpacity="0.3" />
                              <stop offset="100%" stopColor="#2491a6" stopOpacity="0" />
                            </linearGradient>
                          </defs>
                          <path
                            d="M0,78 C28,70 42,58 68,62 C95,66 108,41 138,45 C167,49 182,30 208,35 C235,40 250,18 276,24 C302,30 320,12 340,16 L340,96 L0,96 Z"
                            fill="url(#landingChartFill)"
                          />
                          <path
                            d="M0,78 C28,70 42,58 68,62 C95,66 108,41 138,45 C167,49 182,30 208,35 C235,40 250,18 276,24 C302,30 320,12 340,16"
                            fill="none"
                            stroke="#2491a6"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                          />
                        </svg>
                      </div>

                      <div className="preview-table">
                        <div className="preview-row preview-row-head">
                          <span>Client</span>
                          <span>Policy</span>
                          <span>Status</span>
                        </div>
                        <div className="preview-row">
                          <span>Northstar Logistics</span>
                          <span>POL-2026-0184</span>
                          <span className="preview-pill preview-pill-green">Active</span>
                        </div>
                        <div className="preview-row">
                          <span>Lakeside Hospitality</span>
                          <span>POL-2026-0179</span>
                          <span className="preview-pill preview-pill-amber">Renewal</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="preview-float preview-float-one">
                  <span>
                    <BadgeCheck size={18} />
                  </span>
                  <div>
                    <strong>Policy issued</strong>
                    <small>Cover bound in minutes</small>
                  </div>
                </div>

                <div className="preview-float preview-float-two">
                  <span>
                    <CircleDollarSign size={18} />
                  </span>
                  <div>
                    <strong>Payment matched</strong>
                    <small>Ledger fully reconciled</small>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="landing-proof">
            <div className="landing-container landing-proof-inner">
              <div className="landing-proof-lead">
                <span className="landing-eyebrow">
                  <Layers size={14} /> One connected system
                </span>
                <p>Built around the way brokerages actually work.</p>
              </div>
              <div className="landing-proof-stats">
                <div>
                  <strong>30</strong>
                  <span>connected modules</span>
                </div>
                <div>
                  <strong>13</strong>
                  <span>operational reports</span>
                </div>
                <div>
                  <strong>10</strong>
                  <span>role profiles</span>
                </div>
                <div>
                  <strong>1</strong>
                  <span>source of truth</span>
                </div>
              </div>
            </div>
          </section>

          <section id="platform" className="landing-section">
            <div className="landing-container">
              <div className="landing-section-head">
                <span className="landing-eyebrow">
                  <Zap size={14} /> The platform
                </span>
                <h2>Everything your team needs. Nothing it doesn't.</h2>
                <p>
                  Purpose-built modules for the full insurance brokerage lifecycle,
                  designed to feel like one calm, coherent product.
                </p>
              </div>

              <div className="landing-feature-grid">
                {features.map((feature) => {
                  const Icon = feature.icon;
                  return (
                    <article key={feature.title} className="landing-feature-card">
                      <span className="landing-feature-icon">
                        <Icon size={21} />
                      </span>
                      <h3>{feature.title}</h3>
                      <p>{feature.copy}</p>
                      <span className="landing-feature-arrow">
                        <ArrowUpRight size={17} />
                      </span>
                    </article>
                  );
                })}
              </div>
            </div>
          </section>

          <section id="workflow" className="landing-workflow">
            <div className="landing-container">
              <div className="landing-workflow-head">
                <div>
                  <span className="landing-eyebrow landing-eyebrow-light">
                    <Globe2 size={14} /> The workflow
                  </span>
                  <h2>From first quote to final settlement.</h2>
                </div>
                <p>
                  A clear operational spine keeps every handoff visible, every number
                  accountable and every client conversation informed.
                </p>
              </div>

              <div className="landing-workflow-grid">
                {workflow.map((step) => (
                  <article key={step.number} className="landing-workflow-step">
                    <span className="landing-step-number">{step.number}</span>
                    <h3>{step.title}</h3>
                    <p>{step.copy}</p>
                  </article>
                ))}
              </div>

              <div className="landing-workflow-foot">
                <span>
                  <CheckCircle2 size={16} /> One source of truth from enquiry to renewal
                </span>
                <Link to={primaryHref} className="landing-text-link">
                  See it in the workspace <ArrowRight size={15} />
                </Link>
              </div>
            </div>
          </section>

          <section id="insights" className="landing-section landing-insights">
            <div className="landing-container landing-insights-grid">
              <div className="landing-insights-copy">
                <span className="landing-eyebrow">
                  <BarChart3 size={14} /> Live insight
                </span>
                <h2>Know the story behind the numbers.</h2>
                <p>
                  Leadership gets a role-aware overview. Finance sees the exposure.
                  Operations sees the next action. Everyone works from the same live
                  data.
                </p>
                <ul className="landing-check-list">
                  <li>
                    <CheckCircle2 size={17} />
                    A dashboard tuned to each role and branch
                  </li>
                  <li>
                    <CheckCircle2 size={17} />
                    Thirteen reports across production, finance and claims
                  </li>
                  <li>
                    <CheckCircle2 size={17} />
                    Global search that finds clients, policies and claims fast
                  </li>
                </ul>
                <Link to={primaryHref} className="landing-button landing-button-dark">
                  Explore the dashboard <ArrowRight size={17} />
                </Link>
              </div>

              <div className="landing-report-board" aria-hidden="true">
                <div className="landing-report-card">
                  <div className="landing-report-head">
                    <div>
                      <span>Executive snapshot</span>
                      <strong>Business performance</strong>
                    </div>
                    <span className="landing-report-live">
                      <i /> Live
                    </span>
                  </div>

                  <div className="landing-report-kpis">
                    <div>
                      <span>Gross written premium</span>
                      <strong>USh 2.84B</strong>
                      <small>+12.6%</small>
                    </div>
                    <div>
                      <span>Commission earned</span>
                      <strong>USh 318M</strong>
                      <small>+9.1%</small>
                    </div>
                  </div>

                  <div className="landing-report-bars">
                    {[52, 68, 46, 79, 64, 88, 72, 95].map((height, index) => (
                      <span key={index} style={{ height: `${height}%` }} />
                    ))}
                  </div>

                  <div className="landing-report-chips">
                    {reports.map((report) => (
                      <span key={report}>{report}</span>
                    ))}
                  </div>
                </div>

                <div className="landing-report-float">
                  <span>
                    <TrendingUp size={18} />
                  </span>
                  <div>
                    <strong>Renewal opportunity</strong>
                    <small>27 policies due this month</small>
                  </div>
                  <ArrowUpRight size={16} />
                </div>
              </div>
            </div>
          </section>

          <section id="security" className="landing-section landing-security">
            <div className="landing-container">
              <div className="landing-section-head">
                <span className="landing-eyebrow">
                  <ShieldCheck size={14} /> Secure by design
                </span>
                <h2>Confidence is a feature.</h2>
                <p>
                  Sensitive client, policy and financial data deserves more than good
                  intentions. IBMS builds protection into the way the platform works.
                </p>
              </div>

              <div className="landing-security-grid">
                {security.map((item) => {
                  const Icon = item.icon;
                  return (
                    <article key={item.title} className="landing-security-card">
                      <span>
                        <Icon size={20} />
                      </span>
                      <h3>{item.title}</h3>
                      <p>{item.copy}</p>
                    </article>
                  );
                })}
              </div>

              <div className="landing-quote">
                <span className="landing-quote-mark">“</span>
                <blockquote>
                  From the first client conversation to the final commission
                  reconciliation, everyone works from the same source of truth.
                </blockquote>
                <p>The IBMS principle</p>
              </div>
            </div>
          </section>

          <section className="landing-cta">
            <div className="landing-container landing-cta-inner">
              <div>
                <span className="landing-eyebrow landing-eyebrow-light">
                  <Sparkles size={14} /> Ready when you are
                </span>
                <h2>Bring the whole brokerage into focus.</h2>
                <p>
                  Sign in to your workspace and bring every policy, premium and claim
                  into one clear view.
                </p>
              </div>
              <div className="landing-cta-actions">
                <Link
                  to={primaryHref}
                  className="landing-button landing-button-primary landing-button-large"
                >
                  {user ? 'Open dashboard' : 'Enter the workspace'} <ArrowRight size={18} />
                </Link>
                <a href="#platform" className="landing-button landing-button-ghost">
                  Explore capabilities <ArrowUpRight size={17} />
                </a>
              </div>
            </div>
          </section>
        </main>

        <footer className="landing-footer">
          <div className="landing-container landing-footer-top">
            <div className="landing-footer-brand">
              <Link to="/" className="landing-brand" aria-label="IBMS home">
                <span className="landing-brand-mark">
                  <ShieldCheck size={22} />
                </span>
                <span className="landing-brand-copy">
                  <strong>IBMS</strong>
                  <small>Brokerage, in control.</small>
                </span>
              </Link>
              <p>
                The complete insurance brokerage management system for teams who value
                clarity, control and client service.
              </p>
            </div>

            <div className="landing-footer-links">
              <div>
                <strong>Platform</strong>
                <a href="#platform">Capabilities</a>
                <a href="#workflow">Workflow</a>
                <a href="#insights">Reporting</a>
              </div>
              <div>
                <strong>Trust</strong>
                <a href="#security">Security</a>
                <a href="#security">Permissions</a>
                <a href="#security">Audit trail</a>
              </div>
              <div>
                <strong>Access</strong>
                <Link to={primaryHref}>{primaryLabel}</Link>
                <Link to="/login">Sign in</Link>
              </div>
            </div>
          </div>

          <div className="landing-container landing-footer-bottom">
            <span>© {year} IBMS. All rights reserved.</span>
            <span>
              <ShieldCheck size={14} /> Secure by design · Built for brokers
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default LandingPage;
