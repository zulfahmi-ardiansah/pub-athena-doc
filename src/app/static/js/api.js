/**
 * api.js - Athena REST API client for health, document schemas, and extraction execution.
 */
(() => {
  'use strict';

  const AthenaAPI = {
    /**
     * Checks backend health and active engine / model status.
     * @returns {Promise<Object>}
     */
    async checkHealth() {
      try {
        const res = await fetch('/health', { cache: 'no-store' });
        if (!res.ok) {
          throw new Error(`Health check returned HTTP ${res.status}`);
        }
        return await res.json();
      } catch (err) {
        return { status: 'offline', error: err.message };
      }
    },

    /**
     * Fetches registered document types and JSON schemas from DocumentRegistry.
     * @returns {Promise<Array<{slug: string, name: string, description: string, json_schema: Object}>>}
     */
    async fetchDocumentTypes() {
      try {
        const res = await fetch('/api/v1/documents', { cache: 'no-store' });
        if (!res.ok) {
          throw new Error(`Failed to fetch documents: HTTP ${res.status}`);
        }
        const data = await res.json();
        return Array.isArray(data.documents) ? data.documents : [];
      } catch (err) {
        console.warn('Could not fetch documents from API, using fallback defaults:', err);
        return [
          { slug: 'identity_card', name: 'Identity Card (KTP)', description: 'Indonesian National ID Card (e-KTP)' },
          { slug: 'tax_number', name: 'Tax Number Card (NPWP)', description: 'Indonesian Taxpayer Registration Card (NPWP)' }
        ];
      }
    },

    /**
     * Executes extraction against Athena backend.
     * @param {Object} params
     * @param {string} params.documentType - Document slug identifier
     * @param {Blob|File} params.fileBlob - The file or cropped image Blob
     * @param {string} params.filename - Original or cropped filename
     * @param {boolean} [params.trace=true] - Whether to capture stage evolution trace
     * @param {boolean} [params.keepTrace] - Override whether to keep trace on disk
     * @returns {Promise<{ok: boolean, status: number, data: Object}>}
     */
    async extractDocument({ documentType, fileBlob, filename, trace = true, keepTrace = null }) {
      const formData = new FormData();
      formData.append('file', fileBlob, filename || 'document.jpg');

      const keepTraceQuery = keepTrace === null ? '' : `&keep_trace=${Boolean(keepTrace)}`;
      const url = `/api/v1/extract/${encodeURIComponent(documentType)}?trace=${Boolean(trace)}${keepTraceQuery}`;

      const response = await fetch(url, {
        method: 'POST',
        body: formData
      });

      let jsonPayload;
      try {
        jsonPayload = await response.json();
      } catch (parseErr) {
        jsonPayload = {
          success: false,
          error: `Failed to parse response JSON: ${parseErr.message}`,
          detail: `Server returned HTTP ${response.status} ${response.statusText}`
        };
      }

      return {
        ok: response.ok && jsonPayload.success !== false,
        status: response.status,
        data: jsonPayload
      };
    }
  };

  window.AthenaAPI = AthenaAPI;
})();
