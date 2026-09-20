"""certification 模块的数据访问层（唯一 DB 访问点）

三张表：``expert_certifications``（主表）/ ``certification_documents``（材料）/ ``certification_reviews``（审核流水）。
"""

from shared.models.certification import (
    CertificationDocument,
    CertificationReview,
    ExpertCertification,
)
from src.api.v3.core.base_crud import CRUDBase


class ExpertCertificationCRUD(CRUDBase[ExpertCertification, dict, dict]):
    model = ExpertCertification
    keyword_fields = ("real_name", "organization", "intro")
    #: 待审队列按申请时间正序更有意义，但列表默认给最新申请
    default_order_by = "applied_at"


class CertificationDocumentCRUD(CRUDBase[CertificationDocument, dict, dict]):
    model = CertificationDocument
    default_order_by = "created_at"


class CertificationReviewCRUD(CRUDBase[CertificationReview, dict, dict]):
    model = CertificationReview
    default_order_by = "created_at"


expert_certification_crud = ExpertCertificationCRUD()
certification_document_crud = CertificationDocumentCRUD()
certification_review_crud = CertificationReviewCRUD()
