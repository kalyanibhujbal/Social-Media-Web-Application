from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class AdminUserAccessUpdate(BaseModel):
    role: Optional[Literal["USER", "MODERATOR", "ADMIN"]] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def require_change(self):
        if self.role is None and self.is_active is None:
            raise ValueError("Provide a role or account status to update.")
        return self
