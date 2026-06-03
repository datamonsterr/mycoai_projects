import { sampleStrains } from '@/lib/sample-assets'

export type Role = 'user' | 'owner'

export interface Species {
  species_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  is_archived: boolean
}

export interface Media {
  media_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  is_archived: boolean
}

export interface BBox {
  x: number
  y: number
  w: number
  h: number
}

export interface Segment {
  segment_index: number
  bbox: BBox
  crop_path: string
}

export interface ImageRecord {
  image_id: string
  strain: string
  species_id: string | null
  media_id: string
  file_path: string
  segments: Segment[]
  data_update_status: 'current' | 'updated_requires_reindex' | 'archived'
  indexed_in_qdrant: boolean
  created_at: string
  updated_at: string
}

export interface RetrievalResult {
  result_id: string
  strain: string
  media_strategy: 'same_media' | 'all_media'
  rankings: Array<{
    rank: number
    species: string
    score: number
    neighbors: Array<{
      image_path: string
      species: string
      strain: string
      media: string
      similarity: number
    }>
  }>
  query_details: {
    k: number
    aggregation: 'weighted' | 'uni'
    total_neighbors_queried: number
    new_media_flagged: boolean
  }
}

export interface FeedbackItem {
  feedback_id: string
  source: 'retrieval_result'
  feedback_type: 'wrong_prediction' | 'issue' | 'contribution'
  retrieval_result_id: string
  query_strain: string
  media: string
  predicted_species: string
  suggested_species: string | null
  description: string
  submitter_id: string
  submitter_name: string
  status: 'pending' | 'accepted' | 'rejected' | 'deferred'
  created_at: string
  reviewed_at: string | null
  reviewed_by: string | null
  review_note: string | null
}

export interface UserAccount {
  user_id: string
  name: string
  email: string
  role: Role
  account_status: 'active' | 'inactive'
  created_at: string
}

export interface IndexStatus {
  current_model_version: string
  qdrant_index_status: 'current' | 'needs_reindex' | 'reindexing' | 'failed'
  changes_since_last_index: {
    items_updated: number
    items_archived: number
    feedback_accepted: number
    contributions_accepted: number
  }
  external_retraining_recommended: boolean
}

export interface CandidateModel {
  candidate_model_id: string
  version: string
  uploaded_at: string
  status: 'uploaded' | 'evaluating' | 'accepted' | 'rejected'
  current_metrics: { f1: number }
  candidate_metrics: { f1: number } | null
}

export interface AuditEntry {
  audit_id: string
  actor_id: string
  actor_name: string
  action: string
  target: string
  details: string
  created_at: string
}

export interface BatchItem {
  batch_id: string
  strain: string
  media: string
  images: Array<{ name: string; status: 'pending' | 'ready' | 'removed' }>
  status: 'draft' | 'queue' | 'processing' | 'done' | 'failed'
  created_at: string
}

export const speciesList: Species[] = [
  { species_id: 'sp-001', name: 'Penicillium commune', description: 'Common indoor mold', created_at: '2025-01-15', updated_at: '2025-06-01', is_archived: false },
  { species_id: 'sp-002', name: 'Penicillium expansum', description: 'Blue mold of fruits', created_at: '2025-01-15', updated_at: '2025-06-01', is_archived: false },
  { species_id: 'sp-003', name: 'Aspergillus niger', description: 'Black mold', created_at: '2025-01-20', updated_at: '2025-05-15', is_archived: false },
  { species_id: 'sp-004', name: 'Aspergillus flavus', description: 'Aflatoxin producer', created_at: '2025-02-01', updated_at: '2025-06-01', is_archived: false },
  { species_id: 'sp-005', name: 'Fusarium oxysporum', description: 'Wilt pathogen', created_at: '2025-02-10', updated_at: '2025-04-20', is_archived: false },
  { species_id: 'sp-006', name: 'Trichoderma harzianum', description: 'Biocontrol agent', created_at: '2025-03-01', updated_at: '2025-06-01', is_archived: false },
  { species_id: 'sp-007', name: 'Cladosporium herbarum', description: 'Common outdoor mold', created_at: '2025-03-15', updated_at: '2025-06-01', is_archived: false },
  { species_id: 'sp-008', name: 'Alternaria alternata', description: 'Leaf spot pathogen', created_at: '2025-04-01', updated_at: '2025-06-01', is_archived: false },
  { species_id: 'sp-009', name: 'thymicola', description: 'Dataset sample species', created_at: '2025-06-02', updated_at: '2025-06-02', is_archived: false },
  { species_id: 'sp-010', name: 'sclerotigenum', description: 'Dataset sample species', created_at: '2025-06-02', updated_at: '2025-06-02', is_archived: false },
]

export const mediaList: Media[] = [
  { media_id: 'm-001', name: 'MEA', description: 'Malt Extract Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
  { media_id: 'm-002', name: 'CYA', description: 'Czapek Yeast Autolysate Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
  { media_id: 'm-003', name: 'YES', description: 'Yeast Extract Sucrose Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
  { media_id: 'm-004', name: 'DG18', description: 'Dichloran Glycerol Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
  { media_id: 'm-005', name: 'OA', description: 'Oatmeal Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
  { media_id: 'm-006', name: 'PDA', description: 'Potato Dextrose Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
  { media_id: 'm-007', name: 'SAB', description: 'Sabouraud Agar', created_at: '2025-01-01', updated_at: '2025-06-01', is_archived: false },
]

export const datasetImages: ImageRecord[] = [
  ...sampleStrains.flatMap((strain) =>
    strain.images.map((image, index) => ({
      image_id: `sample-${strain.slug}-${image.media}`,
      strain: strain.strain,
      species_id: strain.species === 'thymicola' ? 'sp-009' : 'sp-010',
      media_id: mediaList.find((media) => media.name === image.media)?.media_id ?? 'm-001',
      file_path: image.original,
      segments: image.segments.map((segment, segmentIndex) => ({
        segment_index: segmentIndex,
        bbox: segment.bbox,
        crop_path: segment.url,
      })),
      data_update_status: index === 0 ? 'updated_requires_reindex' as const : 'current' as const,
      indexed_in_qdrant: true,
      created_at: '2025-06-02',
      updated_at: '2025-06-02',
    })),
  ),
  ...(function generateExtraImages(): ImageRecord[] {
    const result: ImageRecord[] = []
    const speciesPool = speciesList.slice(0, 10)
    const samplePool = (sampleStrains as unknown as Array<{ images: Array<{ original: string; segments: ReadonlyArray<{ url: string; bbox: { x: number; y: number; w: number; h: number } }> }> }>).flatMap((s) => s.images)
    const mediaPool = ['MEA', 'CYA', 'YES', 'DG18', 'OA']

    for (let i = 0; i < 18; i++) {
      const strain = `REF-2024-${String(i + 10).padStart(3, '0')}`
      const species = speciesPool[i % 10]
      const imgCount = 3 + (i % 3)

      for (let j = 0; j < imgCount; j++) {
        const sample = samplePool[(i * 5 + j) % samplePool.length]
        const media = mediaPool[j % mediaPool.length]
        result.push({
          image_id: `ref-${i}-${j}`,
          strain,
          species_id: species.species_id,
          media_id: mediaList.find((m) => m.name === media)?.media_id ?? 'm-001',
          file_path: sample.original,
          segments: sample.segments.slice(0, 1 + (j % 3)).map((seg: { url: string; bbox: { x: number; y: number; w: number; h: number } }, si: number) => ({
            segment_index: si,
            bbox: seg.bbox,
            crop_path: seg.url,
          })),
          data_update_status: (i % 5 === 0 ? 'updated_requires_reindex' : i % 7 === 0 ? 'archived' : 'current') as 'current' | 'updated_requires_reindex' | 'archived',
          indexed_in_qdrant: i % 7 !== 0,
          created_at: `2025-0${4 + (i % 3)}-${String(1 + (i % 28)).padStart(2, '0')}`,
          updated_at: '2025-06-02',
        })
      }
    }
    return result
  })(),
]

export const mockRetrievalResult: RetrievalResult = {
  result_id: 'ret-001',
  strain: 'UNK-2025-001',
  media_strategy: 'same_media',
  rankings: [
    {
      rank: 1, species: 'Penicillium commune', score: 0.87,
      neighbors: [
        { image_path: '/mock/neighbor_01.jpg', species: 'Penicillium commune', strain: 'PCO-2024-001', media: 'MEA', similarity: 0.92 },
        { image_path: '/mock/neighbor_02.jpg', species: 'Penicillium commune', strain: 'PCO-2024-003', media: 'MEA', similarity: 0.88 },
        { image_path: '/mock/neighbor_03.jpg', species: 'Penicillium commune', strain: 'PCO-2024-005', media: 'MEA', similarity: 0.85 },
      ],
    },
    {
      rank: 2, species: 'Penicillium expansum', score: 0.43,
      neighbors: [
        { image_path: '/mock/neighbor_04.jpg', species: 'Penicillium expansum', strain: 'PCO-2024-002', media: 'CYA', similarity: 0.65 },
        { image_path: '/mock/neighbor_05.jpg', species: 'Penicillium expansum', strain: 'PCO-2024-007', media: 'MEA', similarity: 0.52 },
      ],
    },
    {
      rank: 3, species: 'Aspergillus niger', score: 0.21,
      neighbors: [
        { image_path: '/mock/neighbor_06.jpg', species: 'Aspergillus niger', strain: 'AN-2024-001', media: 'YES', similarity: 0.41 },
        { image_path: '/mock/neighbor_07.jpg', species: 'Aspergillus niger', strain: 'AN-2024-003', media: 'MEA', similarity: 0.28 },
      ],
    },
  ],
  query_details: { k: 5, aggregation: 'weighted', total_neighbors_queried: 7, new_media_flagged: false },
}

export const feedbackItems: FeedbackItem[] = [
  {
    feedback_id: 'fb-001', source: 'retrieval_result', feedback_type: 'wrong_prediction',
    retrieval_result_id: 'ret-001', query_strain: 'UNK-2025-001', media: 'MEA',
    predicted_species: 'Penicillium commune', suggested_species: 'Penicillium expansum',
    description: 'Colony morphology matches P. expansum better - blue-green with yellow exudate.',
    submitter_id: 'u-002', submitter_name: 'Jane Smith',
    status: 'pending', created_at: '2025-06-01T10:00:00Z', reviewed_at: null, reviewed_by: null, review_note: null,
  },
  {
    feedback_id: 'fb-002', source: 'retrieval_result', feedback_type: 'contribution',
    retrieval_result_id: 'ret-002', query_strain: 'UNK-2025-003', media: 'PDA',
    predicted_species: 'Trichoderma harzianum', suggested_species: null,
    description: 'Clear colony with good segmentation. Suggest adding this as reference data.',
    submitter_id: 'u-002', submitter_name: 'Jane Smith',
    status: 'pending', created_at: '2025-06-01T14:00:00Z', reviewed_at: null, reviewed_by: null, review_note: null,
  },
  {
    feedback_id: 'fb-003', source: 'retrieval_result', feedback_type: 'wrong_prediction',
    retrieval_result_id: 'ret-003', query_strain: 'UNK-2025-004', media: 'CYA',
    predicted_species: 'Fusarium oxysporum', suggested_species: 'Cladosporium herbarum',
    description: 'Microscopy confirmed Cladosporium.',
    submitter_id: 'u-003', submitter_name: 'Bob Wilson',
    status: 'accepted', created_at: '2025-05-28T09:00:00Z', reviewed_at: '2025-05-30T15:00:00Z', reviewed_by: 'u-001', review_note: 'Microscopy evidence confirmed. Corrected.',
  },
  {
    feedback_id: 'fb-004', source: 'retrieval_result', feedback_type: 'issue',
    retrieval_result_id: 'ret-004', query_strain: 'UNK-2025-005', media: 'DG18',
    predicted_species: 'Aspergillus flavus', suggested_species: null,
    description: 'Segmentation missed one colony in top-right corner.',
    submitter_id: 'u-003', submitter_name: 'Bob Wilson',
    status: 'rejected', created_at: '2025-05-25T11:00:00Z', reviewed_at: '2025-05-26T10:00:00Z', reviewed_by: 'u-001', review_note: 'Missed colony was debris, not a fungal colony. Bounding boxes correct.',
  },
  {
    feedback_id: 'fb-005', source: 'retrieval_result', feedback_type: 'contribution',
    retrieval_result_id: 'ret-sample-t379', query_strain: 'T379', media: 'CREA,CYA,DG18,MEA,YES',
    predicted_species: 'thymicola', suggested_species: null,
    description: 'Five-media strain run has clean segments and should be reviewed as reference contribution.',
    submitter_id: 'u-001', submitter_name: 'Dr. Alice Chen',
    status: 'pending', created_at: '2025-06-02T09:30:00Z', reviewed_at: null, reviewed_by: null, review_note: null,
  },
  {
    feedback_id: 'fb-006', source: 'retrieval_result', feedback_type: 'wrong_prediction',
    retrieval_result_id: 'ret-sample-t362', query_strain: 'T362', media: 'CREA,CYA,DG18,MEA,YES',
    predicted_species: 'sclerotigenum', suggested_species: 'thymicola',
    description: 'DG18 and YES colonies look closer to thymicola neighbors; please verify aggregation weights.',
    submitter_id: 'u-001', submitter_name: 'Dr. Alice Chen',
    status: 'deferred', created_at: '2025-06-02T11:20:00Z', reviewed_at: null, reviewed_by: null, review_note: 'Waiting for microscope confirmation.',
  },
  {
    feedback_id: 'fb-007', source: 'retrieval_result', feedback_type: 'issue',
    retrieval_result_id: 'ret-batch-042', query_strain: 'T379', media: 'MEA',
    predicted_species: 'thymicola', suggested_species: null,
    description: 'MEA plate bbox is too tight around lower colony; user adjusted before final retrieval.',
    submitter_id: 'u-002', submitter_name: 'Jane Smith',
    status: 'accepted', created_at: '2025-06-02T12:00:00Z', reviewed_at: '2025-06-02T13:00:00Z', reviewed_by: 'u-001', review_note: 'Accepted bbox correction; item marked for re-index.',
  },
]

export const users: UserAccount[] = [
  { user_id: 'u-001', name: 'Dr. Alice Chen', email: 'alice@mycoai.org', role: 'owner', account_status: 'active', created_at: '2025-01-01' },
  { user_id: 'u-002', name: 'Jane Smith', email: 'jane@university.edu', role: 'user', account_status: 'active', created_at: '2025-02-15' },
  { user_id: 'u-003', name: 'Bob Wilson', email: 'bob@lab.org', role: 'user', account_status: 'active', created_at: '2025-03-01' },
  { user_id: 'u-004', name: 'Dr. Maria Garcia', email: 'maria@mycoai.org', role: 'owner', account_status: 'active', created_at: '2025-01-15' },
  { user_id: 'u-005', name: 'Tom Harris', email: 'tom@research.net', role: 'user', account_status: 'inactive', created_at: '2025-04-01' },
]

export const indexStatus: IndexStatus = {
  current_model_version: 'efficientnet-b1-v3',
  qdrant_index_status: 'needs_reindex',
  changes_since_last_index: {
    items_updated: 12,
    items_archived: 3,
    feedback_accepted: 5,
    contributions_accepted: 4,
  },
  external_retraining_recommended: true,
}

export const candidateModels: CandidateModel[] = [
  {
    candidate_model_id: 'cm-001', version: 'efficientnet-b1-v4',
    uploaded_at: '2025-06-01T08:00:00Z', status: 'evaluating',
    current_metrics: { f1: 0.89 },
    candidate_metrics: { f1: 0.92 },
  },
  {
    candidate_model_id: 'cm-002', version: 'efficientnet-b1-v3-try2',
    uploaded_at: '2025-05-20T10:00:00Z', status: 'rejected',
    current_metrics: { f1: 0.89 },
    candidate_metrics: { f1: 0.84 },
  },
]

export const auditLogs: AuditEntry[] = [
  { audit_id: 'au-001', actor_id: 'u-001', actor_name: 'Dr. Alice Chen', action: 'reindex_qdrant', target: 'Qdrant Index', details: 'Full re-index triggered', created_at: '2025-05-30T15:00:00Z' },
  { audit_id: 'au-002', actor_id: 'u-001', actor_name: 'Dr. Alice Chen', action: 'accept_feedback', target: 'Feedback fb-003', details: 'Wrong prediction accepted, species corrected to Cladosporium herbarum', created_at: '2025-05-30T14:00:00Z' },
  { audit_id: 'au-003', actor_id: 'u-001', actor_name: 'Dr. Alice Chen', action: 'update_metadata', target: 'Image img-002', details: 'Species changed from Penicillium commune to Penicillium expansum', created_at: '2025-05-29T10:00:00Z' },
  { audit_id: 'au-004', actor_id: 'u-004', actor_name: 'Dr. Maria Garcia', action: 'archive_item', target: 'Image img-005', details: 'Archived due to poor image quality', created_at: '2025-05-28T09:00:00Z' },
  { audit_id: 'au-005', actor_id: 'u-001', actor_name: 'Dr. Alice Chen', action: 'promote_role', target: 'User u-004', details: 'Promoted Maria Garcia to Data Owner', created_at: '2025-05-15T12:00:00Z' },
  { audit_id: 'au-006', actor_id: 'u-001', actor_name: 'Dr. Alice Chen', action: 'create_species', target: 'Species Cladosporium herbarum', details: 'New species added to catalog', created_at: '2025-05-14T10:00:00Z' },
  { audit_id: 'au-007', actor_id: 'u-004', actor_name: 'Dr. Maria Garcia', action: 'reindex_qdrant', target: 'Qdrant Index', details: 'Incremental re-index after edits', created_at: '2025-05-10T16:00:00Z' },
  { audit_id: 'au-008', actor_id: 'u-001', actor_name: 'Dr. Alice Chen', action: 'upload_candidate_model', target: 'Candidate Model efficientnet-b1-v4', details: 'New candidate model uploaded for assessment', created_at: '2025-06-01T08:00:00Z' },
]

export const batchJobs: BatchItem[] = [
  {
    batch_id: 'bat-001', strain: 'UNK-2025-001', media: 'MEA',
    images: [
      { name: 'plate_01.jpg', status: 'ready' },
      { name: 'plate_02.jpg', status: 'ready' },
      { name: 'plate_03.jpg', status: 'removed' },
    ],
    status: 'done', created_at: '2025-06-01T09:00:00Z',
  },
  {
    batch_id: 'bat-002', strain: 'BATCH-2025-042', media: 'CYA',
    images: [
      { name: 'strain_a/plate_01.jpg', status: 'ready' },
      { name: 'strain_a/plate_02.jpg', status: 'pending' },
      { name: 'strain_b/plate_01.jpg', status: 'ready' },
    ],
    status: 'processing', created_at: '2025-06-02T10:00:00Z',
  },
]

export const me: UserAccount = users[0]
