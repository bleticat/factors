"""Request bodies for the `tables` module's REST endpoints. Routers using
these only parse input, call the module's command/query service, and
serialize the result — no business logic lives here."""

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
