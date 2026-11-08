import type { ScopeResponse } from "../../api/client";

export type WorkspaceSelection = {
  studyId: string;
  siteId: string | null;
};

const STORAGE_KEY = "cra.workspace.selection.v1";

export function resolveStoredSelection(
  studies: ScopeResponse["studies"],
  raw: string | null
): WorkspaceSelection | null {
  let stored: Partial<WorkspaceSelection> = {};
  if (raw) {
    try {
      stored = JSON.parse(raw) as Partial<WorkspaceSelection>;
    } catch {
      stored = {};
    }
  }

  for (const study of studies) {
    if (study.id !== stored.studyId) {
      continue;
    }
    const matchingSite = study.sites.find((site) => site.id === stored.siteId);
    if (matchingSite) {
      return { studyId: study.id, siteId: matchingSite.id };
    }
    if (study.sites.length === 0) {
      return { studyId: study.id, siteId: null };
    }
  }

  const firstStudy = studies[0];
  if (!firstStudy) {
    return null;
  }
  return {
    studyId: firstStudy.id,
    siteId: firstStudy.sites[0]?.id ?? null
  };
}

export function readStoredSelection(): string | null {
  return window.localStorage.getItem(STORAGE_KEY);
}

export function storeSelection(selection: WorkspaceSelection): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
}
