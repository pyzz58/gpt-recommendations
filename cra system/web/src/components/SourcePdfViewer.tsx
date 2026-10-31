import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

type Props = {
  url: string;
  pageNumber: number;
  bbox?: number[] | null;
};

export function SourcePdfViewer({ url, pageNumber, bbox }: Props) {
  const [pageSize, setPageSize] = useState<{
    width: number;
    height: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const highlightStyle =
    bbox && pageSize
      ? {
          left: `${(bbox[0] / pageSize.width) * 100}%`,
          top: `${(bbox[1] / pageSize.height) * 100}%`,
          width: `${((bbox[2] - bbox[0]) / pageSize.width) * 100}%`,
          height: `${((bbox[3] - bbox[1]) / pageSize.height) * 100}%`
        }
      : null;

  return (
    <div className="pdf-viewer">
      {error ? (
        <p className="inline-error" role="alert">
          源 PDF 无法显示：{error}
        </p>
      ) : (
        <Document
          file={url}
          options={{ withCredentials: true }}
          onLoadError={(reason) => setError(reason.message)}
          loading={<p className="viewer-loading">正在读取私有源 PDF…</p>}
          noData={<p className="viewer-loading">当前版本没有可显示页面。</p>}
        >
          <div className="pdf-page-frame">
            <Page
              pageNumber={pageNumber}
              width={720}
              renderAnnotationLayer
              renderTextLayer
              onLoadSuccess={(page) => {
                setPageSize({
                  width: page.originalWidth,
                  height: page.originalHeight
                });
              }}
            />
            {highlightStyle && (
              <span
                className="source-highlight"
                style={highlightStyle}
                aria-label="来源定位高亮"
              />
            )}
          </div>
        </Document>
      )}
    </div>
  );
}
