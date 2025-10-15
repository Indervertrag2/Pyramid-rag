import type { ConversationDocument, UploadedDocumentInfo } from '../types';

const fallbackId = () => `temp-${Date.now()}`;

export const normalizeUploadedDocument = (
  doc: any,
  overrides: Partial<UploadedDocumentInfo> = {}
): UploadedDocumentInfo => {
  const meta = (doc?.metadata ?? doc?.meta_data ?? {}) as Record<string, any>;

  const rawId =
    overrides.id ??
    doc?.documentId ??
    doc?.document_id ??
    doc?.id ??
    doc?.filename ??
    fallbackId();

  const scopeValue = (overrides.scope ?? doc?.scope) === 'GLOBAL' ? 'GLOBAL' : 'CHAT';

  const contentValue = overrides.content ?? (typeof doc?.content === 'string' ? doc.content : undefined);
  const contentPreview =
    overrides.contentPreview ??
    (typeof doc?.contentPreview === 'string'
      ? doc.contentPreview
      : typeof doc?.content_preview === 'string'
        ? doc.content_preview
        : contentValue
          ? contentValue.slice(0, 200)
          : undefined);
  const contentLengthCandidate =
    overrides.contentLength ??
    doc?.contentLength ??
    doc?.content_length;
  const contentLength =
    typeof contentLengthCandidate === 'number'
      ? contentLengthCandidate
      : contentValue?.length;

  const filename = overrides.filename ?? doc?.stored_filename ?? doc?.filename ?? doc?.originalFilename ?? '';
  const originalFilename =
    overrides.originalFilename ?? doc?.original_filename ?? doc?.originalFilename ?? doc?.filename ?? '';

  const title = (
    overrides.title ??
    doc?.title ??
    meta?.title ??
    originalFilename ??
    filename ??
    'Datei'
  )
    .toString()
    .trim();

  const metadataValue = overrides.metadata ?? meta;

  return {
    id: String(rawId),
    documentId: String(overrides.documentId ?? doc?.documentId ?? doc?.document_id ?? rawId),
    title,
    filename,
    originalFilename,
    scope: scopeValue,
    fileType: overrides.fileType ?? doc?.fileType ?? doc?.file_type,
    mimeType: overrides.mimeType ?? doc?.mimeType ?? doc?.mime_type,
    content: contentValue,
    contentPreview,
    contentLength,
    metadata: metadataValue,
    department: overrides.department ?? doc?.department ?? metadataValue?.department,
    accessDepartments:
      overrides.accessDepartments ??
      doc?.accessDepartments ??
      doc?.access_departments ??
      metadataValue?.allowed_departments,
    uploadedBy: overrides.uploadedBy ?? doc?.uploadedBy ?? doc?.uploaded_by,
    createdAt: overrides.createdAt ?? doc?.createdAt ?? doc?.created_at,
    updatedAt: overrides.updatedAt ?? doc?.updatedAt ?? doc?.updated_at,
    source: overrides.source ?? (scopeValue === 'GLOBAL' ? 'knowledge_base' : 'chat'),
  };
};

export const normalizeConversationDocuments = (docs: any[]): ConversationDocument[] => {
  return (docs || []).map((doc: any, index: number) => {
    const scope: 'GLOBAL' | 'CHAT' = doc?.scope === 'GLOBAL' ? 'GLOBAL' : 'CHAT';
    const source: 'chat' | 'knowledge_base' = doc?.source === 'knowledge_base' || scope === 'GLOBAL'
      ? 'knowledge_base'
      : 'chat';
    const rawScore =
      typeof doc?.score === 'number'
        ? doc.score
        : typeof doc?.relevance_score === 'number'
          ? doc.relevance_score
          : typeof doc?.hybrid_score === 'number'
            ? doc.hybrid_score
            : typeof doc?.similarity_score === 'number'
              ? doc.similarity_score
              : undefined;
    const alias = typeof doc?.alias === 'string' ? doc.alias : undefined;

    return {
      id: String(doc?.document_id ?? doc?.id ?? `context-${index}`),
      documentId: doc?.document_id ?? doc?.id,
      title: (doc?.title ?? 'Dokument').toString().trim(),
      scope,
      source,
      contentPreview: typeof doc?.content_preview === 'string' ? doc.content_preview : undefined,
      mimeType: doc?.mime_type,
      chunkId: doc?.chunk_id,
      score: rawScore,
      alias,
    };
  });
};

export const buildUploadAcknowledgement = (
  notices: string[],
  documents: UploadedDocumentInfo[]
): string => {
  if (notices.length > 0) {
    return `Upload erfolgreich abgeschlossen:\n${notices.join('\n')}`;
  }

  if (documents.length === 0) {
    return 'Upload abgeschlossen.';
  }

  const lines = documents.map(doc =>
    `• ${doc.title} (${doc.scope === 'GLOBAL' ? 'Firmendatenbank' : 'Chat-Kontext'})`
  );

  return `Upload erfolgreich abgeschlossen:\n${lines.join('\n')}`;
};
