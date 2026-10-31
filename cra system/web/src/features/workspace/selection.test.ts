import { describe, expect, it } from "vitest";

import type { ScopeResponse } from "../../api/client";
import { resolveStoredSelection } from "./selection";

const studies: ScopeResponse["studies"] = [
  {
    id: "study-a",
    code: "SYN-001",
    title: "Synthetic study",
    revision: 1,
    roles: ["cra"],
    sites: [
      {
        id: "site-a",
        code: "A01",
        name: "Site A",
        revision: 1
      },
      {
        id: "site-b",
        code: "B01",
        name: "Site B",
        revision: 1
      }
    ]
  }
];

describe("workspace selection", () => {
  it("restores a still-authorized project and center", () => {
    const selection = resolveStoredSelection(
      studies,
      JSON.stringify({ studyId: "study-a", siteId: "site-b" })
    );
    expect(selection).toEqual({ studyId: "study-a", siteId: "site-b" });
  });

  it("falls back to the first authorized center after revocation or stale data", () => {
    const selection = resolveStoredSelection(
      studies,
      JSON.stringify({ studyId: "study-a", siteId: "revoked-site" })
    );
    expect(selection).toEqual({ studyId: "study-a", siteId: "site-a" });
  });

  it("returns no context when the actor has no authorized center", () => {
    expect(
      resolveStoredSelection(
        [
          {
            ...studies[0],
            sites: []
          }
        ],
        null
      )
    ).toBeNull();
  });
});
