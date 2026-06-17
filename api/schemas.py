from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


FinalOutcome = Literal[
    "booked",
    "no_agreement",
    "no_match",
    "not_verified",
    "not_interested",
    "incomplete",
]

Sentiment = Literal["positive", "neutral", "negative"]


class LoadOut(BaseModel):
    load_id: int
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: Optional[str] = None
    weight: Optional[float] = None
    commodity_type: Optional[str] = None
    num_of_pieces: Optional[int] = None
    miles: Optional[float] = None
    dimensions: Optional[str] = None


class CallCreate(BaseModel):
    call_id: str = Field(min_length=1)
    call_started_at: datetime
    call_ended_at: datetime
    mc_number: str = Field(min_length=1)
    carrier_authorized: bool
    requested_origin: Optional[str] = None
    requested_destination: Optional[str] = None
    requested_equipment: Optional[str] = None
    requested_pickup_window: Optional[str] = None
    matched_load_id: Optional[int] = None
    agreed_rate: Optional[float] = None
    negotiation_turns: Optional[int] = None
    final_outcome: FinalOutcome
    sentiment: Sentiment

    @field_validator("agreed_rate")
    @classmethod
    def validate_agreed_rate(cls, value):
        if value is not None and value < 0:
            raise ValueError("agreed_rate must be >= 0")
        return value

    @field_validator("negotiation_turns")
    @classmethod
    def validate_negotiation_turns(cls, value):
        if value is not None and value < 0:
            raise ValueError("negotiation_turns must be >= 0")
        return value

    @field_validator("mc_number")
    @classmethod
    def validate_mc_number(cls, value):
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("mc_number must not be empty")
        return trimmed

    @field_validator("call_id")
    @classmethod
    def validate_call_id(cls, value):
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("call_id must not be empty")
        return trimmed

    @model_validator(mode="after")
    def validate_timestamps(self):
        if self.call_ended_at < self.call_started_at:
            raise ValueError("call_ended_at must be >= call_started_at")
        return self


class CallOut(BaseModel):
    call_id: str
    call_started_at: datetime
    call_ended_at: datetime
    mc_number: str
    carrier_authorized: bool
    requested_origin: Optional[str] = None
    requested_destination: Optional[str] = None
    requested_equipment: Optional[str] = None
    requested_pickup_window: Optional[str] = None
    matched_load_id: Optional[int] = None
    agreed_rate: Optional[float] = None
    negotiation_turns: Optional[int] = None
    final_outcome: FinalOutcome
    sentiment: Sentiment


class CallCreateResponse(BaseModel):
    call_id: str
    message: str


class CarrierVerifyOut(BaseModel):
    mc_number: str
    legal_name: Optional[str] = None
    dot_number: Optional[str] = None
    authorized: bool
    reason: Optional[str] = None