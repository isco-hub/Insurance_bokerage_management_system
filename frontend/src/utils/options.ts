import { useEffect, useState } from 'react';
import { fetchOptions } from '../api/client';
import type { Option } from '../types';

type OptionLabel = string | ((item: Record<string, unknown>) => string);

const cache = new Map<string, Option[]>();
const inflight = new Map<string, Promise<Option[]>>();

const CACHE_TTL_MS = 60_000;
const cacheTimestamps = new Map<string, number>();

function cacheKey(url: string, label?: OptionLabel, value = 'id'): string {
  const labelKey =
    typeof label === 'function' ? label.toString() : String(label ?? '');
  return `${url}|${labelKey}|${value}`;
}

export function invalidateOptionsCache(urlPrefix?: string) {
  if (!urlPrefix) {
    cache.clear();
    cacheTimestamps.clear();
    return;
  }
  for (const key of Array.from(cache.keys())) {
    if (key.startsWith(urlPrefix)) {
      cache.delete(key);
      cacheTimestamps.delete(key);
    }
  }
}

export function loadOptions(
  url: string,
  label?: OptionLabel,
  value = 'id',
): Promise<Option[]> {
  const key = cacheKey(url, label, value);
  const cached = cache.get(key);
  const ts = cacheTimestamps.get(key) ?? 0;
  if (cached && Date.now() - ts < CACHE_TTL_MS) return Promise.resolve(cached);
  const pending = inflight.get(key);
  if (pending) return pending;
  const request = fetchOptions(url, label, value)
    .then((options) => {
      cache.set(key, options);
      cacheTimestamps.set(key, Date.now());
      return options;
    })
    .finally(() => {
      inflight.delete(key);
    });
  inflight.set(key, request);
  return request;
}

export function useRemoteOptions(
  url?: string,
  label?: OptionLabel,
  value = 'id',
): Option[] {
  const [options, setOptions] = useState<Option[]>(() =>
    url ? cache.get(cacheKey(url, label, value)) ?? [] : [],
  );

  useEffect(() => {
    if (!url) {
      setOptions([]);
      return;
    }
    let cancelled = false;
    loadOptions(url, label, value)
      .then((loaded) => {
        if (!cancelled) setOptions(loaded);
      })
      .catch(() => {
        if (!cancelled) setOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [url, label, value]);

  return options;
}
