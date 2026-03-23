import { apiFetch } from './api';

export type FxResponse = {
  source: string;
  fetched_at: string;
  usd_to_rub: number;
  eur_to_rub: number;
  rub_to_usd: number;
  rub_to_eur: number;
};

export function getFxRates(): Promise<FxResponse> {
  return apiFetch('/api/fx/rub/');
}
