"""Request bodies for the `tables` module's REST endpoints. Per ADR 007,
routers using these only parse input, build a typed mediator request, and
serialize the result — no business logic lives here."""

from __future__ import annotations

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
