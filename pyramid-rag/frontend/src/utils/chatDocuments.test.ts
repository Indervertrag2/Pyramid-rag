import { describe, it, expect } from 'vitest';

import {
  buildUploadAcknowledgement,
  normalizeConversationDocuments,
  normalizeUploadedDocument,
} from './chatDocuments';

describe('normalizeUploadedDocument', () => {
  it('normalizes backend payload with meta_data', () => {
    const raw = {
      document_id: '1234',
      stored_filename: 'stored.pdf',
      original_filename: 'original.pdf',
      scope: 'GLOBAL',
      file_type: 'pdf',
      mime_type: 'application/pdf',
      content: 'Hallo Welt',
      content_length: 10,
      meta_data: { allowed_departments: ['ALL'], title: 'Quartalsbericht' },
      department: 'Management',
      access_departments: ['ALL'],
      uploaded_by: 'user-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    };

    const normalized = normalizeUploadedDocument(raw);

    expect(normalized.id).toBe('1234');
    expect(normalized.documentId).toBe('1234');
    expect(normalized.scope).toBe('GLOBAL');
    expect(normalized.source).toBe('knowledge_base');
    expect(normalized.filename).toBe('stored.pdf');
    expect(normalized.originalFilename).toBe('original.pdf');
    expect(normalized.fileType).toBe('pdf');
    expect(normalized.mimeType).toBe('application/pdf');
    expect(normalized.content).toBe('Hallo Welt');
    expect(normalized.contentPreview).toBe('Hallo Welt');
    expect(normalized.contentLength).toBe(10);
    expect(normalized.metadata?.allowed_departments).toEqual(['ALL']);
    expect(normalized.department).toBe('Management');
    expect(normalized.accessDepartments).toEqual(['ALL']);
    expect(normalized.uploadedBy).toBe('user-1');
    expect(normalized.createdAt).toBe('2024-01-01T00:00:00Z');
    expect(normalized.updatedAt).toBe('2024-01-02T00:00:00Z');
  });

  it('normalizes stored payload and respects overrides', () => {
    const stored = {
      id: 'doc-1',
      documentId: 'doc-1',
      title: 'Notiz',
      filename: 'note.txt',
      originalFilename: 'note.txt',
      scope: 'CHAT',
      fileType: 'text',
      mimeType: 'text/plain',
      content: 'A'.repeat(50),
      contentLength: 50,
      metadata: { allowed_departments: ['IT'] },
      createdAt: '2024-03-01T00:00:00Z',
      updatedAt: '2024-03-02T00:00:00Z',
    };

    const normalized = normalizeUploadedDocument(stored, {
      contentLength: 100,
      department: 'IT',
    });

    expect(normalized.scope).toBe('CHAT');
    expect(normalized.source).toBe('chat');
    expect(normalized.contentLength).toBe(100);
    expect(normalized.metadata?.allowed_departments).toEqual(['IT']);
    expect(normalized.department).toBe('IT');
    expect(normalized.filename).toBe('note.txt');
    expect(normalized.contentPreview).toBe('A'.repeat(50));
    expect(normalized.createdAt).toBe('2024-03-01T00:00:00Z');
  });
});

describe('normalizeConversationDocuments', () => {
  it('normalizes chat documents', () => {
    const docs = normalizeConversationDocuments([
      {
        document_id: 'chat-1',
        scope: 'CHAT',
        title: 'Chat Doc',
        content_preview: 'Preview text',
        mime_type: 'text/plain'
      }
    ]);

    expect(docs).toHaveLength(1);
    expect(docs[0]).toEqual({
      id: 'chat-1',
      documentId: 'chat-1',
      title: 'Chat Doc',
      scope: 'CHAT',
      source: 'chat',
      contentPreview: 'Preview text',
      mimeType: 'text/plain',
      chunkId: undefined,
      score: undefined,
    });
  });

  it('normalizes knowledge-base citations', () => {
    const docs = normalizeConversationDocuments([
      {
        document_id: 'kb-1',
        scope: 'GLOBAL',
        document_title: 'KB Doc',
        chunk_id: 'chunk-1',
        content_preview: 'Some snippet',
        score: 0.92
      }
    ]);

    expect(docs[0].source).toBe('knowledge_base');
    expect(docs[0].scope).toBe('GLOBAL');
    expect(docs[0].chunkId).toBe('chunk-1');
    expect(docs[0].score).toBeCloseTo(0.92);
  });
});

describe('buildUploadAcknowledgement', () => {
  const sampleDocs = [
    normalizeUploadedDocument({
      id: '1',
      documentId: '1',
      title: 'A',
      filename: 'a.txt',
      originalFilename: 'a.txt',
      scope: 'GLOBAL',
    }),
    normalizeUploadedDocument({
      id: '2',
      documentId: '2',
      title: 'B',
      filename: 'b.txt',
      originalFilename: 'b.txt',
      scope: 'CHAT',
    })
  ];

  it('prefers notices when provided', () => {
    const message = buildUploadAcknowledgement(['Upload A ok', 'Upload B ok'], sampleDocs);
    expect(message).toContain('Upload A ok');
    expect(message).toContain('Upload B ok');
  });

  it('falls back to document summary when notices are empty', () => {
    const message = buildUploadAcknowledgement([], sampleDocs);
    expect(message).toContain('• A (Firmendatenbank)');
    expect(message).toContain('• B (Chat-Kontext)');
  });
});
