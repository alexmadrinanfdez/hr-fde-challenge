from fastapi import APIRouter, Depends, HTTPException

from api.auth import verify_api_key
from api.schemas import CarrierVerifyOut
from api.services.fmcsa import FMCSAError, verify_carrier


router = APIRouter(prefix="/carriers", tags=["carriers"])


@router.get(
    "/{mc_number}/verify",
    response_model=CarrierVerifyOut,
    dependencies=[Depends(verify_api_key)],
)
def verify(mc_number: str):
    mc_number = mc_number.strip()
    if not mc_number.isdigit():
        raise HTTPException(status_code=400, detail="mc_number must contain only digits")

    try:
        result = verify_carrier(mc_number)
    except FMCSAError as e:
        raise HTTPException(status_code=502, detail=f"FMCSA lookup failed: {e.reason}")

    return CarrierVerifyOut(**result)