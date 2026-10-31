import { describe, expect, it } from "vitest";

import type { EDCPreviewView } from "../../api/client";
import {
  initialiseEdcMapping,
  missingRequiredMapping
} from "./ImportPreview";

describe("EDC import mapping", () => {
  const preview = {
    included_sheets: ["Hematology"],
    suggested_mapping: {
      sheets: {
        Hematology: {
          header_row: 1,
          data_start_row: 2,
          included: true,
          columns: {
            subject_external_id: "Subject ID",
            analyte: "Analyte",
            value_raw: "Result",
            collected_on: "Collection Date",
            instance_type: "Instance"
          }
        }
      }
    },
    sheets: [
      {
        name: "Hematology",
        state: "visible",
        header_row: 1
      },
      {
        name: "Internal Notes",
        state: "hidden",
        header_row: 1
      }
    ]
  } as unknown as EDCPreviewView;

  it("adopts confirmed headers and excludes hidden sheets by default", () => {
    const mapping = initialiseEdcMapping(preview);
    expect(mapping.sheets.Hematology.included).toBe(true);
    expect(mapping.sheets.Hematology.columns.value_raw).toBe("Result");
    expect(mapping.sheets["Internal Notes"].included).toBe(false);
    expect(missingRequiredMapping(mapping)).toEqual([]);
  });

  it("requires an initial/repeat identity before confirmation", () => {
    const mapping = initialiseEdcMapping(preview);
    delete mapping.sheets.Hematology.columns.instance_type;
    expect(missingRequiredMapping(mapping)).toContain(
      "Hematology: 初检/复查实例"
    );
  });
});
