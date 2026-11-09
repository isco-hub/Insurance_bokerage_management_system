import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Building2,
  Car,
  FileText,
  HeartPulse,
  Receipt,
  Search,
  ShieldCheck,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { api, getErrorMessage } from '../api/client';

interface SearchItem {
  id: string;
  title: string;
  subtitle: string;
  type: string;
}

interface SearchGroup {
  type: string;
  label: string;
  items: SearchItem[];
}

interface SearchData {
  query: string;
  groups: SearchGroup[];
}

const TYPE_ICONS: Record<string, LucideIcon> = {
  client: Users,
  policy: ShieldCheck,
  quotation: FileText,
  claim: HeartPulse,
  motor: Car,
  insurer: Building2,
  invoice: Receipt,
};

const TYPE_PATHS: Record<string, string> = {
  client: '/clients',
  policy: '/policies',
  quotation: '/quotations',
  claim: '/claims',
  motor: '/risks',
  insurer: '/insurers',
  invoice: '/invoices',
};

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';
  const [input, setInput] = useState(query);
  const [data, setData] = useState<SearchData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setInput(query);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    if (query.trim().length < 2) {
      setData(null);
      setLoading(false);
      return;
    }
    async function load() {
      setLoading(true);
      setError('');
      try {
        const response = await api.get('/search/', { params: { q: query } });
        if (!cancelled) setData(response.data.data as SearchData);
      } catch (caught) {
        if (!cancelled) setError(getErrorMessage(caught));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [query]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (trimmed.length < 2) {
      setSearchParams({}, { replace: true });
      return;
    }
    setSearchParams({ q: trimmed });
  };

  return (
    <div className="page search-page">
      <div className="search-hero">
        <span className="page-eyebrow">Global search</span>
        <h1 className="page-title">Find anything, fast.</h1>
        <p className="page-subtitle">
          Search clients, policies, quotations, claims, invoices, insurers and
          vehicle registration numbers from one place.
        </p>
        <form className="search-form" onSubmit={submit} role="search">
          <Search size={20} />
          <input
            type="search"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Try a client name, policy number, claim number or vehicle registration…"
            autoFocus
            aria-label="Search the system"
          />
          <button type="submit" className="btn btn-primary">
            Search
          </button>
        </form>
      </div>

      {error ? <div className="alert alert-danger">{error}</div> : null}

      {loading ? (
        <div className="content-card report-loading">
          <span className="spinner spinner-dark" />
          <p>Searching…</p>
        </div>
      ) : null}

      {!loading && query.trim().length >= 2 && data ? (
        data.groups.length === 0 ? (
          <div className="empty-state content-card">
            <Search size={32} />
            <h2>No results for “{query}”</h2>
            <p>Try a different spelling, a partial name or a reference number.</p>
          </div>
        ) : (
          <div className="search-results">
            {data.groups.map((group) => (
              <section className="content-card search-group" key={group.type}>
                <div className="mini-section-head">
                  <h2>{group.label}</h2>
                  <span className="badge badge-neutral">{group.items.length}</span>
                </div>
                <div className="search-group-list">
                  {group.items.map((item) => {
                    const Icon = TYPE_ICONS[item.type] ?? FileText;
                    const path = TYPE_PATHS[item.type];
                    return (
                      <Link
                        key={`${group.type}-${item.id}`}
                        to={path ? `${path}?search=${encodeURIComponent(item.title)}` : '/dashboard'}
                        className="search-result"
                      >
                        <span className="search-result-icon">
                          <Icon size={18} />
                        </span>
                        <span>
                          <strong>{item.title}</strong>
                          <small>{item.subtitle}</small>
                        </span>
                      </Link>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )
      ) : null}

      {!loading && query.trim().length < 2 ? (
        <div className="empty-state content-card">
          <Search size={32} />
          <h2>Start typing to search</h2>
          <p>Enter at least two characters to search across the system.</p>
        </div>
      ) : null}
    </div>
  );
}

export default SearchPage;
