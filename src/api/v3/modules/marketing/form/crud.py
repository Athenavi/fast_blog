"""form 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.form import Form, FormField, FormSubmission
from src.api.v3.core.base_crud import CRUDBase


class FormCRUD(CRUDBase[Form, dict, dict]):
    model = Form
    keyword_fields = ("title", "slug", "description")
    default_order_by = "id"


class FormFieldCRUD(CRUDBase[FormField, dict, dict]):
    model = FormField
    default_order_by = "order_index"


class FormSubmissionCRUD(CRUDBase[FormSubmission, dict, dict]):
    model = FormSubmission
    default_order_by = "id"


form_crud = FormCRUD()
form_field_crud = FormFieldCRUD()
form_submission_crud = FormSubmissionCRUD()
