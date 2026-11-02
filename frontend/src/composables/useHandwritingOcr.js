/**
 * High-Accuracy Handwritten & Printed Journal OCR
 * Supports:
 * 1. Gemini 2.5 Flash Vision API (via backend /api/ocr or user API key) for cursive & messy handwriting.
 * 2. Upgraded Browser Tesseract.js pipeline with Integral-Image Local Illumination Normalization
 *    (removes phone camera shadows & faint notebook ruled lines) + white border padding + PSM 6 block mode.
 */

/**
 * Clean raw OCR output from Tesseract or Vision by removing stray single-symbol noise lines
 * and normalizing spacing while preserving paragraph breaks and list items.
 * @param {string} rawText
 * @returns {string}
 */
export function cleanOcrText(rawText) {
  if (!rawText || typeof rawText !== "string") return "";
  const lines = rawText
    .replace(/\r\n/g, "\n")
    // Strip markdown code fences if a vision model wrapped the output
    .replace(/^```(?:markdown|md|text)?\s*\n/i, "")
    .replace(/\n```\s*$/i, "")
    .split("\n")
    .map((line) => {
      // Remove isolated pipe/tilde/caret artifacts produced by ruled lines or page edges
      return line
        .replace(/^[|~^_\\/<>{}[\]]+\s*/g, "")
        .replace(/\s*[|~^_\\/<>{}[\]]+$/g, "")
        .replace(/[ \t]+/g, " ")
        .trim();
    })
    .filter((line) => {
      if (line.length === 0) return true;
      // Filter out isolated 1-character non-alphanumeric noise
      if (line.length === 1 && !/[a-zA-Z0-9IiaA]/.test(line)) return false;
      // Filter out lines that are >65% random punctuation symbols (ruled-line OCR noise)
      const alphaNumCount = (line.match(/[a-zA-Z0-9]/g) || []).length;
      if (line.length >= 3 && alphaNumCount / line.length < 0.35) return false;
      return true;
    });

  // Collapse 3+ consecutive empty lines into a single paragraph break
  const collapsed = [];
  let blankRun = 0;
  for (const l of lines) {
    if (l === "") {
      blankRun += 1;
      if (blankRun <= 1) collapsed.push("");
    } else {
      blankRun = 0;
      collapsed.push(l);
    }
  }
  return collapsed.join("\n").trim();
}

/**
 * Merge recognized OCR text into existing Markdown note content.
 * @param {string} existingMd
 * @param {string} ocrText
 * @param {{ includeHeader?: boolean, sourceLabel?: string }} options
 * @returns {string}
 */
export function appendOcrToMarkdown(existingMd, ocrText, options = {}) {
  const cleaned = cleanOcrText(ocrText);
  if (!cleaned) return existingMd || "";

  const includeHeader = options.includeHeader !== false;
  const label = options.sourceLabel || "Handwritten Journal Scan";
  const block = includeHeader ? `### ${label}\n\n${cleaned}` : cleaned;

  const base = (existingMd || "").trimEnd();
  if (!base) return `${block}\n`;
  return `${base}\n\n${block}\n`;
}

/**
 * Convert a File or Blob into a base64 data string for Vision OCR.
 * @param {File | Blob} fileOrBlob
 * @returns {Promise<{ base64: string, mimeType: string }>}
 */
export function fileToBase64(fileOrBlob) {
  return new Promise((resolve, reject) => {
    if (typeof FileReader === "undefined") {
      reject(new Error("FileReader is not available"));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const base64 = result.includes(",") ? result.split(",", 1)[1] : result;
      resolve({
        base64,
        mimeType: fileOrBlob.type || "image/jpeg",
      });
    };
    reader.onerror = () => reject(new Error("Failed to read image file"));
    reader.readAsDataURL(fileOrBlob);
  });
}

/**
 * Preprocess a camera photo of a notebook page using Integral-Image Local Illumination
 * Normalization:
 * - Removes uneven phone shadows and warm indoor lighting gradients.
 * - Suppresses faint horizontal ruled notebook lines while preserving pen/pencil ink.
 * - Adds a 24px white margin around the image so Tesseract LSTM does not clip edge words.
 *
 * @param {File | Blob | string} fileOrUrl
 * @param {{ enhanceContrast?: boolean }} options
 * @returns {Promise<Blob | File | string>}
 */
export async function preprocessImageForOcr(fileOrUrl, options = {}) {
  const enhanceContrast = options.enhanceContrast !== false;
  if (
    !enhanceContrast ||
    typeof document === "undefined" ||
    typeof Image === "undefined"
  ) {
    return fileOrUrl;
  }

  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    const objectUrl =
      typeof fileOrUrl === "string"
        ? fileOrUrl
        : URL.createObjectURL(fileOrUrl);

    img.onload = () => {
      try {
        const maxDim = 2000;
        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;
        if (width > maxDim || height > maxDim) {
          const ratio = Math.min(maxDim / width, maxDim / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }

        const pad = 24;
        const canvas = document.createElement("canvas");
        canvas.width = width + pad * 2;
        canvas.height = height + pad * 2;
        const ctx = canvas.getContext("2d");

        // Fill white border padding
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, pad, pad, width, height);

        const imageData = ctx.getImageData(pad, pad, width, height);
        const data = imageData.data;

        // 1. Extract perceptual grayscale luminance and build 2D integral image
        const lum = new Float32Array(width * height);
        const integral = new Float64Array((width + 1) * (height + 1));
        const stride = width + 1;

        for (let y = 0; y < height; y += 1) {
          let rowSum = 0;
          const yOffset = y * width;
          const intRowOffset = (y + 1) * stride;
          const prevIntRowOffset = y * stride;

          for (let x = 0; x < width; x += 1) {
            const idx = (yOffset + x) * 4;
            const val =
              0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
            lum[yOffset + x] = val;
            rowSum += val;
            integral[intRowOffset + x + 1] =
              integral[prevIntRowOffset + x + 1] + rowSum;
          }
        }

        // 2. Local window radius (~1/28th of page dimension) to estimate local paper background
        const radius = Math.max(20, Math.round(Math.min(width, height) / 28));

        for (let y = 0; y < height; y += 1) {
          const y0 = Math.max(0, y - radius);
          const y1 = Math.min(height - 1, y + radius);
          const yOffset = y * width;

          for (let x = 0; x < width; x += 1) {
            const x0 = Math.max(0, x - radius);
            const x1 = Math.min(width - 1, x + radius);
            const count = (x1 - x0 + 1) * (y1 - y0 + 1);

            const sum =
              integral[(y1 + 1) * stride + (x1 + 1)] -
              integral[y0 * stride + (x1 + 1)] -
              integral[(y1 + 1) * stride + x0] +
              integral[y0 * stride + x0];

            const localBg = Math.max(sum / count, 1);
            const pixelLum = lum[yOffset + x];
            // Ratio of pixel luminance to local paper background (1.0 = paper, < 0.88 = ink)
            const ratio = pixelLum / localBg;

            let outVal;
            if (ratio >= 0.91) {
              // Suppress paper texture, lighting gradients, and faint ruled lines to pure white
              outVal = 255;
            } else {
              // Smoothly stretch ink strokes for LSTM recognition
              const normalized = Math.max(0, (ratio - 0.45) / (0.91 - 0.45));
              outVal = Math.round(normalized * 230);
            }

            const idx = (yOffset + x) * 4;
            data[idx] = outVal;
            data[idx + 1] = outVal;
            data[idx + 2] = outVal;
          }
        }

        ctx.putImageData(imageData, pad, pad);
        if (typeof fileOrUrl !== "string") {
          URL.revokeObjectURL(objectUrl);
        }
        canvas.toBlob(
          (blob) => {
            resolve(blob || fileOrUrl);
          },
          "image/png",
          0.95
        );
      } catch {
        if (typeof fileOrUrl !== "string") {
          URL.revokeObjectURL(objectUrl);
        }
        resolve(fileOrUrl);
      }
    };

    img.onerror = () => {
      if (typeof fileOrUrl !== "string") {
        URL.revokeObjectURL(objectUrl);
      }
      resolve(fileOrUrl);
    };

    img.src = objectUrl;
  });
}

/**
 * Run OCR on a photo of a handwritten or printed journal page.
 * Automatically uses Gemini 2.5 Flash Vision (via /api/ocr) if a Gemini API key is configured,
 * and falls back to the Adaptive Local Illumination Normalized Tesseract.js pipeline.
 *
 * @param {File | Blob | string} imageSource
 * @param {{
 *   enhanceContrast?: boolean,
 *   apiBase?: string,
 *   geminiApiKey?: string,
 *   useServerOcr?: boolean,
 *   onProgress?: (info: { status: string, progress: number }) => void
 * }} options
 * @returns {Promise<{ text: string, confidence: number, engine: string }>}
 */
export async function runBrowserHandwritingOcr(imageSource, options = {}) {
  const onProgress = options.onProgress || (() => {});
  const apiBase = options.apiBase || "/api";
  const geminiApiKey = (options.geminiApiKey || "").trim();
  const useServerOcr = Boolean(options.useServerOcr || geminiApiKey);

  // 1. If Gemini Vision OCR is available (via user key or server key), use it for cursive handwriting
  if (useServerOcr && typeof imageSource !== "string") {
    try {
      onProgress({ status: "Reading handwriting with AI Vision…", progress: 35 });
      const { base64, mimeType } = await fileToBase64(imageSource);
      const res = await fetch(`${apiBase}/ocr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: base64,
          mime_type: mimeType,
          gemini_api_key: geminiApiKey || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const cleanedVision = cleanOcrText(data.text || "");
        if (cleanedVision) {
          onProgress({ status: "AI Handwriting scan complete", progress: 100 });
          return {
            text: cleanedVision,
            confidence: 98,
            engine: "gemini-vision",
          };
        }
      }
    } catch {
      // Fall through to adaptive local-normalized browser Tesseract OCR
    }
  }

  // 2. Adaptive Local Illumination Normalized Browser OCR (Tesseract.js)
  onProgress({
    status: "Removing paper shadows & ruled lines…",
    progress: 12,
  });

  const processedSource = await preprocessImageForOcr(imageSource, {
    enhanceContrast: options.enhanceContrast !== false,
  });

  onProgress({ status: "Loading OCR engine…", progress: 22 });
  const TesseractModule = await import("tesseract.js");
  const createWorkerFn =
    TesseractModule.createWorker || TesseractModule.default?.createWorker;
  const recognizeFn =
    TesseractModule.recognize || TesseractModule.default?.recognize;

  let rawText = "";
  let confidence = 0;

  if (typeof createWorkerFn === "function") {
    const worker = await createWorkerFn("eng", 1, {
      logger: (msg) => {
        if (msg && typeof msg.progress === "number") {
          const pct = Math.min(99, Math.max(25, Math.round(25 + msg.progress * 74)));
          const humanStatus =
            msg.status === "recognizing text"
              ? `Scanning journal lines… ${pct}%`
              : "Initializing handwriting model…";
          onProgress({ status: humanStatus, progress: pct });
        }
      },
    });
    try {
      // PSM 6 = Assume a single uniform block of text; preserve interword spaces
      await worker.setParameters({
        tessedit_pageseg_mode: "6",
        preserve_interword_spaces: "1",
      });
      const result = await worker.recognize(processedSource);
      rawText = result?.data?.text || "";
      confidence = Number(result?.data?.confidence || 0);
    } finally {
      await worker.terminate();
    }
  } else if (typeof recognizeFn === "function") {
    const result = await recognizeFn(processedSource, "eng");
    rawText = result?.data?.text || "";
    confidence = Number(result?.data?.confidence || 0);
  } else {
    throw new Error("Tesseract.js OCR engine is unavailable");
  }

  const cleaned = cleanOcrText(rawText);
  onProgress({ status: "Scan complete", progress: 100 });
  return {
    text: cleaned,
    confidence,
    engine: "tesseract-adaptive",
  };
}
