from pydantic import BaseModel


class CreateDecisionTableRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateDecisionTableRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AddFactorRequest(BaseModel):
    name: str


class UpdateFactorRequest(BaseModel):
    name: str | None = None
    order_index: int | None = None


class AddFactorValueRequest(BaseModel):
    value: str


class UpdateFactorValueRequest(BaseModel):
    value: str | None = None
    order_index: int | None = None
