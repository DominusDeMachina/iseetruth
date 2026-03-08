from typing import Optional

from pydantic import BaseModel


class RFC7807Error(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
